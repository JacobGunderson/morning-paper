from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from scripts.news.base import HttpClient


@dataclass
class ComicResult:
    id: str
    name: str
    provider: str
    published_date: str | None
    source_url: str
    images: list[str]
    status: str
    detail: str = ""
    author: str | None = None

    def public(self) -> dict:
        value = asdict(self)
        value.pop("detail", None)
        return value


def sort_key(title: str) -> str:
    normalized = title.casefold().strip()
    return normalized[4:] if normalized.startswith("the ") else normalized


def dated_url(provider: str, slug: str, day: date) -> str:
    if provider == "comics_kingdom":
        return f"https://comicskingdom.com/{slug}/{day:%Y-%m-%d}"
    raise ValueError(f"No dated route for {provider}")


def image_candidates(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    found: list[str] = []
    selectors = [
        '[data-image] img[src]', '.comic img[src]', '[class*="comic"] img[src]',
        'main img[src]', 'meta[property="og:image"][content]',
    ]
    for selector in selectors:
        for node in soup.select(selector):
            raw = node.get("src") or node.get("content")
            if not raw or raw.startswith("data:"):
                continue
            url = urljoin(page_url, raw)
            lowered = url.lower()
            if any(marker in lowered for marker in ("logo", "avatar", "icon", "sprite", "favicon")):
                continue
            if url not in found:
                found.append(url)
    return found[:6]


async def download_images(client: HttpClient, urls: list[str], comic_id: str, output_dir: Path) -> list[str]:
    paths: list[str] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, url in enumerate(urls):
        try:
            response = await client.get(url)
            mime = response.headers.get("content-type", "").split(";")[0]
            signature = response.content[:16]
            if signature.startswith(b"\xff\xd8\xff"):
                kind = "jpeg"
            elif signature.startswith(b"\x89PNG\r\n\x1a\n"):
                kind = "png"
            elif signature.startswith((b"GIF87a", b"GIF89a")):
                kind = "gif"
            elif signature.startswith(b"RIFF") and response.content[8:12] == b"WEBP":
                kind = "webp"
            else:
                kind = None
            if not mime.startswith("image/") or not kind or len(response.content) < 4_000:
                continue
            suffix = {"jpeg": ".jpg", "png": ".png", "gif": ".gif", "webp": ".webp"}.get(kind, Path(urlsplit(url).path).suffix or ".img")
            digest = hashlib.sha256(response.content).hexdigest()[:10]
            filename = f"{comic_id}-{index + 1}-{digest}{suffix}"
            path = output_dir / filename
            path.write_bytes(response.content)
            paths.append(f"comics/{filename}")
        except Exception as exc:
            return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))
    return paths


async def collect_dated(source: dict, day: date, client: HttpClient, output_dir: Path) -> ComicResult:
    for offset in range(8):
        candidate_date = day - timedelta(days=offset)
        page_url = dated_url(source["provider"], source["slug"], candidate_date)
        try:
            response = await client.get(page_url)
            images = await download_images(client, image_candidates(response.text, page_url), source["id"], output_dir)
            if images:
                return ComicResult(source["id"], source["title"], source["provider"], candidate_date.isoformat(), page_url, images, "ok" if offset == 0 else "stale")
        except Exception:
            continue
    return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "unavailable", "No valid strip found in the 8-day window")
