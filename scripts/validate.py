from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlsplit



def validate_news(data: dict) -> None:
    seen_urls: set[str] = set()
    seen_publisher_headlines: set[tuple[str, str]] = set()
    for section in data["sections"]:
        assert section["id"]
        for subsection in section["subsections"]:
            assert subsection["id"] and len(subsection["items"]) <= 10
            for item in subsection["items"]:
                assert item["headline"].strip()
                assert urlsplit(item["url"]).scheme == "https"
                assert item["canonical_url"] not in seen_urls
                seen_urls.add(item["canonical_url"])
                key = (item["publisher"], item["headline"].casefold())
                assert key not in seen_publisher_headlines
                seen_publisher_headlines.add(key)


def validate_comics(data: list[dict], generated: Path) -> None:
    for comic in data:
        assert comic["name"] and comic["source_url"]
        assert comic["images"] or comic["status"] in {"unavailable", "error"}
        if comic["published_date"]:
            date.fromisoformat(comic["published_date"])
        for image in comic["images"]:
            path = generated / image
            assert path.exists() and path.stat().st_size > 4_000
