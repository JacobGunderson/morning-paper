from datetime import date
from pathlib import Path

from scripts.news.base import HttpClient
from .base import ComicResult, download_images, image_candidates


async def collect(source: dict, day: date, client: HttpClient, output_dir: Path) -> ComicResult:
    try:
        response = await client.get(source["base_url"])
        images = await download_images(client, image_candidates(response.text, source["base_url"])[:2], source["id"], output_dir)
        if images:
            return ComicResult(source["id"], source["title"], source["provider"], day.isoformat(), source["base_url"], images, "ok")
    except Exception as exc:
        return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))
    return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "unavailable")
