from datetime import date
from pathlib import Path

from scripts.news.base import HttpClient
from .base import ComicResult, download_images


async def collect(source: dict, day: date, client: HttpClient, output_dir: Path) -> ComicResult:
    try:
        response = await client.get("https://xkcd.com/info.0.json")
        payload = response.json()
        published = date(int(payload["year"]), int(payload["month"]), int(payload["day"]))
        images = await download_images(client, [payload["img"]], source["id"], output_dir)
        if images:
            return ComicResult(source["id"], source["title"], source["provider"], published.isoformat(), f'https://xkcd.com/{payload["num"]}/', images, "ok" if published == day else "stale", author=source.get("author"))
    except Exception as exc:
        return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))
    return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "unavailable")
