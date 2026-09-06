from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from scripts.games.nyt import find_paths


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


def validate_games(wordle: dict, connections: dict, strands: dict) -> None:
    if wordle["status"] == "ok":
        assert len(wordle["solution"]) == 5 and wordle["solution"].isalpha()
    if connections["status"] == "ok":
        assert len(connections["groups"]) == 4
        assert len({word for group in connections["groups"] for word in group["members"]}) == 16
    if strands["status"] == "ok":
        assert len(strands["grid"]) == 8 and all(len(row) == 6 for row in strands["grid"])
        for answer in strands["answers"]:
            assert answer["cells"] in find_paths(strands["grid"], answer["word"])
