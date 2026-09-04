from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
from scripts.news.base import HttpClient
from .base import ComicResult, download_images


async def collect(source: dict, day: date, client: HttpClient, output_dir: Path) -> ComicResult:
    # Comics Kingdom's current dated page exposes the exact strip as og:image and
    # inside the dated comic-reader item. Avoid generic navigation/gallery art.
    from datetime import timedelta
    for offset in range(8):
        candidate_date = day - timedelta(days=offset)
        page_url = f'https://comicskingdom.com/{source["slug"]}/{candidate_date:%Y-%m-%d}'
        try:
            response = await client.get(page_url)
        except Exception as exc:
            return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))
        soup = BeautifulSoup(response.text, "lxml")
        urls: list[str] = []
        reader = soup.select_one(f'.comic-reader-item[data-published-date="{candidate_date.isoformat()}"]')
        for image in reader.select('.ck-panel img[src]') if reader else []:
            raw = urljoin(page_url, image["src"])
            if urlsplit(raw).path == "/_next/image":
                raw = unquote(parse_qs(urlsplit(raw).query).get("url", [raw])[0])
            if raw not in urls:
                urls.append(raw)
        if not urls:
            meta = soup.select_one('meta[property="og:image"][content]')
            if meta:
                urls.append(urljoin(page_url, meta["content"]))
        images = await download_images(client, urls, source["id"], output_dir)
        if images:
            return ComicResult(source["id"], source["title"], source["provider"], candidate_date.isoformat(), page_url, images, "ok" if offset == 0 else "stale")
    return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "unavailable", "No valid strip found in the 8-day window")
