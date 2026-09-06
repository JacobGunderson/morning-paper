#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import atexit
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.comics.base import ComicResult, sort_key
from scripts.comics import comics_kingdom, farside, xkcd
from scripts.games import circle9
from scripts.news import ap, politico
from scripts.news.base import HttpClient, assign_unique
from scripts.validate import validate_comics, validate_news

GENERATED = ROOT / "generated"


def load_yaml(name: str) -> dict:
    with (ROOT / "config" / name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def main() -> None:
    site_config = load_yaml("site.yaml")
    timezone = ZoneInfo(site_config["site"]["timezone"])
    now = datetime.now(timezone)
    day = now.date()
    client = HttpClient()
    statuses: list[dict] = []
    limiter = asyncio.Semaphore(5)
    print(f"Refreshing the {day.isoformat()} edition…", flush=True)

    async def limited(coro):
        async with limiter:
            return await coro

    # News sources are normalized, then specific subsections claim duplicates before catch-alls.
    news_config = load_yaml("news.yaml")
    sources: list[dict] = []
    for section in news_config["sections"]:
        for configured in section["sources"]:
            sources.append({**configured, "section": section["id"], "section_title": section["title"]})

    async def news_source(source: dict):
        try:
            adapter = {"ap": ap, "politico": politico}[source["adapter"]]
            items = await limited(adapter.collect(source, client))
            statuses.append({"id": source["id"], "kind": "news", "status": "ok" if items else "unavailable", "count": len(items)})
            return source["id"], items
        except Exception as exc:
            statuses.append({"id": source["id"], "kind": "news", "status": "error", "detail": str(exc)[:240]})
            return source["id"], []

    print(f"Collecting {len(sources)} news sources…", flush=True)
    news_pairs = await asyncio.gather(*(news_source(source) for source in sources))
    assigned = assign_unique(dict(news_pairs), sources)
    source_by_id = {source["id"]: source for source in sources}
    status_by_id = {status["id"]: status["status"] for status in statuses if status["kind"] == "news"}
    news_data = {"generated_at": now.isoformat(), "sections": []}
    for section in news_config["sections"]:
        subsections = []
        for source in (candidate for candidate in sources if candidate["section"] == section["id"] and not candidate.get("fallback_for")):
            active_source = source
            items = assigned[source["id"]]
            status = status_by_id.get(source["id"], "error")
            fallback_id = source.get("fallback")
            if not items and fallback_id:
                fallback_source = source_by_id[fallback_id]
                fallback_items = assigned[fallback_id]
                if fallback_items:
                    active_source = fallback_source
                    items = fallback_items
                    status = "fallback"
            subsections.append({
                "id": source["subsection"],
                "title": source["title"],
                "items": [item.public() for item in items],
                "status": status,
                "source": {"publisher": source["publisher"], "url": source["url"]},
                "active_source": {"publisher": active_source["publisher"], "url": active_source["url"]},
            })
        news_data["sections"].append({
            "id": section["id"], "title": section["title"],
            "subsections": subsections,
        })

    # Build images away from the current edition. An interrupted or invalid refresh
    # must never erase the last working comic sheet.
    staging_root = ROOT / "work" / f"edition-next-{os.getpid()}"
    comics_dir = staging_root / "comics"
    shutil.rmtree(staging_root, ignore_errors=True)
    comics_dir.mkdir(parents=True, exist_ok=True)
    (comics_dir / ".gitkeep").touch()
    atexit.register(shutil.rmtree, staging_root, ignore_errors=True)
    previous_comics = json.loads((GENERATED / "comics.json").read_text(encoding="utf-8")) if (GENERATED / "comics.json").exists() else []
    saved_gocomics = [comic for comic in previous_comics if comic["provider"] == "gocomics_snapshot"]
    for comic in saved_gocomics:
        for image in comic["images"]:
            source = GENERATED / image
            destination = staging_root / image
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        statuses.append({"id": comic["id"], "kind": "comic", "status": comic["status"], "detail": "Saved GoComics page"})
    comic_sources = load_yaml("comics.yaml")["comics"]
    if len({source["id"] for source in comic_sources}) != len(comic_sources):
        raise ValueError("Duplicate comic ids in config/comics.yaml")

    async def comic_source(source: dict) -> ComicResult:
        try:
            adapter = {"comics_kingdom": comics_kingdom, "farside": farside, "xkcd": xkcd}[source["provider"]]
            result = await limited(adapter.collect(source, day, client, comics_dir))
        except Exception as exc:
            result = ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))
        statuses.append({"id": source["id"], "kind": "comic", "status": result.status, "detail": result.detail[:240]})
        return result

    async def comic_provider(provider: str) -> list[ComicResult]:
        provider_sources = [source for source in comic_sources if source["provider"] == provider]
        first = await comic_source(provider_sources[0])
        if first.status == "error" and len(provider_sources) > 1:
            # A transport-level failure on the representative page indicates a provider outage/block.
            # Record every configured title without spending minutes retrying identical connections.
            remainder = [ComicResult(source["id"], source["title"], provider, None, source["base_url"], [], "error", "Provider unavailable during representative request") for source in provider_sources[1:]]
            statuses.extend({"id": result.id, "kind": "comic", "status": result.status, "detail": result.detail} for result in remainder)
            return [first, *remainder]
        return [first, *await asyncio.gather(*(comic_source(source) for source in provider_sources[1:]))]

    print(f"Collecting {len(comic_sources)} comics…", flush=True)
    providers = tuple(dict.fromkeys(source["provider"] for source in comic_sources))
    provider_results = await asyncio.gather(*(comic_provider(provider) for provider in providers))
    comics_data = sorted([*saved_gocomics, *(comic.public() for group in provider_results for comic in group)], key=lambda comic: sort_key(comic["name"]))

    games_config = load_yaml("games.yaml")
    async def external_game(source: dict) -> dict:
        if source["provider"] == "circle9":
            result = await limited(circle9.collect(source, client))
        else:
            result = {**source, "status": "ok"}
        statuses.append({"id": source["id"], "kind": "game", "status": result["status"], "detail": result.get("detail", "")[:240]})
        return result

    print("Collecting games…", flush=True)
    external = await asyncio.gather(*(external_game(source) for source in games_config["external"]))
    games_index = {"date": day.isoformat(), "external": [{key: value for key, value in game.items() if key != "detail"} for game in external]}

    validate_news(news_data)
    validate_comics(comics_data, staging_root)
    manifest = {
        "build_time": now.isoformat(), "edition_date": day.isoformat(),
        "news": {"success": sum(s["kind"] == "news" and s["status"] == "ok" for s in statuses), "failed": sum(s["kind"] == "news" and s["status"] != "ok" for s in statuses)},
        "comics": {"success": sum(s["kind"] == "comic" and s["status"] in {"ok", "stale", "mock"} for s in statuses), "failed": sum(s["kind"] == "comic" and s["status"] not in {"ok", "stale", "mock"} for s in statuses)},
        "games": {"success": sum(s["kind"] == "game" and s["status"] == "ok" for s in statuses), "failed": sum(s["kind"] == "game" and s["status"] != "ok" for s in statuses)},
        "source_statuses": statuses,
    }
    print("Writing the static edition…", flush=True)
    live_comics_dir = GENERATED / "comics"
    previous_comics_dir = GENERATED / ".comics-previous"
    shutil.rmtree(previous_comics_dir, ignore_errors=True)
    if live_comics_dir.exists():
        live_comics_dir.replace(previous_comics_dir)
    try:
        comics_dir.replace(live_comics_dir)
    except BaseException:
        if previous_comics_dir.exists() and not live_comics_dir.exists():
            previous_comics_dir.replace(live_comics_dir)
        raise
    shutil.rmtree(previous_comics_dir, ignore_errors=True)
    write_json(GENERATED / "site.json", site_config)
    write_json(GENERATED / "news.json", news_data)
    write_json(GENERATED / "comics.json", comics_data)
    write_json(GENERATED / "games" / "index.json", games_index)
    write_json(GENERATED / "manifest.json", manifest)
    await client.close()
    print(json.dumps({key: manifest[key] for key in ("edition_date", "news", "comics", "games")}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
