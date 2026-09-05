#!/usr/bin/env python3
"""Refresh only the comic providers that do not require a signed-in browser."""
from __future__ import annotations

import asyncio
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

from scripts.comics import comics_kingdom, farside, xkcd
from scripts.comics.base import ComicResult, sort_key
from scripts.news.base import HttpClient
from scripts.validate import validate_comics

GENERATED = ROOT / "generated"
PROVIDERS = {"comics_kingdom": comics_kingdom, "farside": farside, "xkcd": xkcd}


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_json(path: Path, fallback: object) -> object:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def main() -> None:
    site = load_yaml(ROOT / "config" / "site.yaml")["site"]
    now = datetime.now(ZoneInfo(site["timezone"]))
    day = now.date()
    comic_sources = load_yaml(ROOT / "config" / "comics.yaml")["comics"]
    requested = [source for source in comic_sources if source["provider"] in PROVIDERS]
    staging = ROOT / "work" / f"comics-provider-refresh-{os.getpid()}"
    staging_images = staging / "comics"
    shutil.rmtree(staging, ignore_errors=True)
    staging_images.mkdir(parents=True)
    client = HttpClient()

    async def collect(source: dict) -> ComicResult:
        try:
            return await PROVIDERS[source["provider"]].collect(source, day, client, staging_images)
        except Exception as exc:
            return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))

    try:
        print(f"Refreshing {len(requested)} non-browser comics for {day.isoformat()}…", flush=True)
        results = await asyncio.gather(*(collect(source) for source in requested))
    finally:
        await client.close()

    old_comics = load_json(GENERATED / "comics.json", [])
    by_id = {comic["id"]: comic for comic in old_comics if comic["id"] not in {result.id for result in results}}
    by_id.update({result.id: result.public() for result in results})
    comics = sorted(by_id.values(), key=lambda comic: sort_key(comic["name"]))

    # Replace only files produced by the providers being refreshed. Browser-sourced
    # GoComics strips remain untouched until their signed-in refresh runs.
    target_ids = {result.id for result in results}
    live_images = GENERATED / "comics"
    live_images.mkdir(parents=True, exist_ok=True)
    for image in live_images.iterdir():
        if image.is_file() and any(image.name.startswith(f"{comic_id}-") for comic_id in target_ids):
            image.unlink()
    for image in staging_images.iterdir():
        if image.is_file() and image.name != ".gitkeep":
            image.replace(live_images / image.name)

    validate_comics(comics, GENERATED)
    write_json(GENERATED / "comics.json", comics)

    manifest = load_json(GENERATED / "manifest.json", {})
    existing_statuses = [status for status in manifest.get("source_statuses", []) if status.get("id") not in target_ids]
    existing_statuses.extend({"id": result.id, "kind": "comic", "status": result.status, "detail": result.detail[:240]} for result in results)
    manifest.update({
        "build_time": now.isoformat(),
        "edition_date": day.isoformat(),
        "comics": {
            "success": sum(comic["status"] in {"ok", "stale"} for comic in comics),
            "failed": sum(comic["status"] not in {"ok", "stale"} for comic in comics),
        },
        "source_statuses": existing_statuses,
    })
    write_json(GENERATED / "manifest.json", manifest)
    shutil.rmtree(staging, ignore_errors=True)
    print(json.dumps({"edition_date": day.isoformat(), "updated": [result.public() for result in results]}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
