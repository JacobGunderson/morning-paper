from datetime import date
from pathlib import Path
from datetime import timedelta

from bs4 import BeautifulSoup
from scripts.news.base import HttpClient
from .base import ComicResult, dated_url, download_images


async def collect(source: dict, day: date, client: HttpClient, output_dir: Path) -> ComicResult:
    # The dated page's Open Graph image is the public canonical strip asset.
    # Do not scrape archive-gate internals or unrelated image cards.
    for offset in range(8):
        candidate_date = day - timedelta(days=offset)
        page_url = dated_url("gocomics", source["slug"], candidate_date)
        try:
            response = await client.get(page_url)
        except Exception as exc:
            return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))
        soup = BeautifulSoup(response.text, "lxml")
        meta = soup.select_one('meta[property="og:image"][content]')
        images = await download_images(client, [meta["content"]] if meta else [], source["id"], output_dir)
        if images:
            return ComicResult(source["id"], source["title"], source["provider"], candidate_date.isoformat(), page_url, images, "ok" if offset == 0 else "stale")
    return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "unavailable", "No valid public strip found in the 8-day window")
