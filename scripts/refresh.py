#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.comics.base import ComicResult, sort_key
from scripts.comics import comics_kingdom, farside, gocomics, xkcd
from scripts.games import circle9, latimes, nyt
from scripts.news import ap, politico
from scripts.news.base import HttpClient, assign_unique
from scripts.validate import validate_comics, validate_games, validate_news

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

    # Start every comic edition clean. Individual failures remain visible as source links.
    comics_dir = GENERATED / "comics"
    comics_dir.mkdir(parents=True, exist_ok=True)
    for existing in comics_dir.iterdir():
        if existing.is_file() and existing.name != ".gitkeep":
            existing.unlink()
    comic_sources = load_yaml("comics.yaml")["comics"]
    if len({source["id"] for source in comic_sources}) != len(comic_sources):
        raise ValueError("Duplicate comic ids in config/comics.yaml")

    async def comic_source(source: dict) -> ComicResult:
        try:
            adapter = {"gocomics": gocomics, "comics_kingdom": comics_kingdom, "farside": farside, "xkcd": xkcd}[source["provider"]]
            result = await limited(adapter.collect(source, day, client, comics_dir))
        except Exception as exc:
            result = ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))
        statuses.append({"id": source["id"], "kind": "comic", "status": result.status, "detail": result.detail[:240]})
        return result

    async def comic_provider(provider: str) -> list[ComicResult]:
        provider_sources = [source for source in comic_sources if source["provider"] == provider]
        if provider == "gocomics":
            results = await gocomics.collect_all(provider_sources, day, comics_dir)
            statuses.extend({"id": result.id, "kind": "comic", "status": result.status, "detail": result.detail[:240]} for result in results)
            return results
        first = await comic_source(provider_sources[0])
        if first.status == "error" and len(provider_sources) > 1:
            # A transport-level failure on the representative page indicates a provider outage/block.
            # Record every configured title without spending minutes retrying identical connections.
            remainder = [ComicResult(source["id"], source["title"], provider, None, source["base_url"], [], "error", "Provider unavailable during representative request") for source in provider_sources[1:]]
            statuses.extend({"id": result.id, "kind": "comic", "status": result.status, "detail": result.detail} for result in remainder)
            return [first, *remainder]
        return [first, *await asyncio.gather(*(comic_source(source) for source in provider_sources[1:]))]

    provider_results = await asyncio.gather(*(comic_provider(provider) for provider in ("gocomics", "comics_kingdom", "farside", "xkcd")))
    comics = sorted([comic for group in provider_results for comic in group], key=lambda comic: sort_key(comic.name))
    comics_data = [comic.public() for comic in comics]

    games_config = load_yaml("games.yaml")
    async def external_game(source: dict) -> dict:
        adapter = circle9 if source["provider"] == "circle9" else latimes
        result = await limited(adapter.collect(source, client))
        statuses.append({"id": source["id"], "kind": "game", "status": result["status"], "detail": result.get("detail", "")[:240]})
        return result

    external = await asyncio.gather(*(external_game(source) for source in games_config["external"]))
    wordle, connections, strands = await asyncio.gather(*(limited(nyt.collect(game, day, client)) for game in ("wordle", "connections", "strands")))
    for game, result in (("wordle", wordle), ("connections", connections), ("strands", strands)):
        statuses.append({"id": game, "kind": "game", "status": result["status"], "detail": result.get("detail", "")[:240]})
    games_index = {"date": day.isoformat(), "external": [{key: value for key, value in game.items() if key != "detail"} for game in external]}

    validate_news(news_data)
    validate_comics(comics_data, GENERATED)
    validate_games(wordle, connections, strands)
    manifest = {
        "build_time": now.isoformat(), "edition_date": day.isoformat(),
        "news": {"success": sum(s["kind"] == "news" and s["status"] == "ok" for s in statuses), "failed": sum(s["kind"] == "news" and s["status"] != "ok" for s in statuses)},
        "comics": {"success": sum(s["kind"] == "comic" and s["status"] in {"ok", "stale"} for s in statuses), "failed": sum(s["kind"] == "comic" and s["status"] not in {"ok", "stale"} for s in statuses)},
        "games": {"success": sum(s["kind"] == "game" and s["status"] == "ok" for s in statuses), "failed": sum(s["kind"] == "game" and s["status"] != "ok" for s in statuses)},
        "source_statuses": statuses,
    }
    write_json(GENERATED / "site.json", site_config)
    write_json(GENERATED / "news.json", news_data)
    write_json(GENERATED / "comics.json", comics_data)
    write_json(GENERATED / "games" / "index.json", games_index)
    write_json(GENERATED / "games" / "wordle.json", {key: value for key, value in wordle.items() if key != "detail"})
    write_json(GENERATED / "games" / "connections.json", {key: value for key, value in connections.items() if key != "detail"})
    write_json(GENERATED / "games" / "strands.json", {key: value for key, value in strands.items() if key != "detail"})
    write_json(GENERATED / "manifest.json", manifest)
    await client.close()
    print(json.dumps({key: manifest[key] for key in ("edition_date", "news", "comics", "games")}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
