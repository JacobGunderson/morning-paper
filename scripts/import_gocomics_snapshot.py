#!/usr/bin/env python3
"""Create a one-time local comic edition from a saved GoComics follows page."""
from __future__ import annotations

import base64
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "generated"


def comic_id(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return "gocomics_" + re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")


def save_data_image(value: str, comic_id_value: str) -> str:
    header, encoded = value.split(",", 1)
    kind = re.search(r"data:image/([^;]+)", header).group(1)
    extension = {"jpeg": "jpg", "svg+xml": "svg"}.get(kind, kind)
    filename = f"{comic_id_value}-2026-09-05.{extension}"
    destination = GENERATED / "comics" / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(base64.b64decode(encoded))
    return f"comics/{filename}"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: import_gocomics_snapshot.py /path/to/saved-page.html")
    soup = BeautifulSoup(Path(sys.argv[1]).read_text(encoding="utf-8"), "lxml")
    comics: list[dict] = []
    for card in soup.select('div[class*="ViewMyComics"][class*="container"]'):
        metadata = card.select_one('script[type="application/ld+json"]')
        image = card.select_one('img[class*="Comic-module"]')
        link = card.select_one('a[href*="gocomics.com/"]')
        if not metadata or not image or not link or not image.get("src", "").startswith("data:image/"):
            continue
        payload = json.loads(metadata.string)
        name = payload["name"].rsplit(" - ", 1)[0]
        raw_author = payload.get("author")
        author = raw_author.get("name") if isinstance(raw_author, dict) else raw_author
        published = datetime.strptime(payload["datePublished"], "%B %d, %Y").date().isoformat()
        source_url = link["href"]
        item_id = comic_id(source_url)
        comics.append({
            "id": item_id,
            "name": name,
            "provider": "gocomics_snapshot",
            "published_date": published,
            "source_url": source_url,
            "images": [save_data_image(image["src"], item_id)],
            "status": "mock",
            "author": author,
        })

    not_issued = soup.select_one('div[class*="FeaturesNotIssued"]')
    for link in not_issued.select('a[href*="gocomics.com/"]') if not_issued else []:
        source_url = link["href"]
        name = link.get_text(" ", strip=True).split(" By ", 1)[0]
        comics.append({
            "id": comic_id(source_url),
            "name": name,
            "provider": "gocomics_snapshot",
            "published_date": None,
            "source_url": source_url,
            "images": [],
            "status": "unavailable",
            "author": None,
        })

    existing = json.loads((GENERATED / "comics.json").read_text(encoding="utf-8"))
    replaced_ids = {comic["id"] for comic in existing if comic["provider"] in {"gocomics", "gocomics_snapshot"}}
    combined = [comic for comic in existing if comic["provider"] not in {"gocomics", "gocomics_snapshot"}] + comics
    combined.sort(key=lambda comic: comic["name"].removeprefix("The ").casefold())
    (GENERATED / "comics.json").write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    used_images = {image for comic in combined for image in comic["images"]}
    for image in (GENERATED / "comics").iterdir():
        if image.is_file() and image.name != ".gitkeep" and f"comics/{image.name}" not in used_images:
            image.unlink()

    manifest_path = GENERATED / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["edition_date"] = "2026-09-05"
    manifest["source_statuses"] = [status for status in manifest["source_statuses"] if status["id"] not in replaced_ids]
    manifest["source_statuses"].extend({"id": comic["id"], "kind": "comic", "status": comic["status"], "detail": "Saved GoComics page"} for comic in comics)
    manifest["comics"] = {
        "success": sum(comic["status"] in {"ok", "stale", "mock"} for comic in combined),
        "failed": sum(comic["status"] not in {"ok", "stale", "mock"} for comic in combined),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing_count = len(not_issued.select("a[href]")) if not_issued else 0
    print(f"Imported {len(comics) - missing_count} issued strips and {missing_count} not-issued titles.")


if __name__ == "__main__":
    main()
