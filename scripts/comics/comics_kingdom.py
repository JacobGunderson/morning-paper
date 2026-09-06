from datetime import date, timedelta
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
from scripts.news.base import HttpClient
from .base import ComicResult, download_images


def published_date(soup: BeautifulSoup) -> date | None:
    """Read the date Comics Kingdom puts in the strip's page title.

    A dated URL can sometimes serve the most recently available strip instead
    of the requested edition, so the route alone is not trustworthy.
    """
    title = soup.select_one('meta[property="og:title"][content]')
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", title["content"] if title else "")
    return date.fromisoformat(match.group(1)) if match else None


async def collect(source: dict, day: date, client: HttpClient, output_dir: Path) -> ComicResult:
    # Comics Kingdom's current dated page exposes the exact strip as og:image and
    # inside the dated comic-reader item. Avoid generic navigation/gallery art.
    for offset in range(8):
        candidate_date = day - timedelta(days=offset)
        page_url = f'https://comicskingdom.com/{source["slug"]}/{candidate_date:%Y-%m-%d}'
        try:
            response = await client.get(page_url)
        except Exception as exc:
            return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", str(exc))
        soup = BeautifulSoup(response.text, "lxml")
        actual_date = published_date(soup)
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
            strip_date = actual_date or candidate_date
            return ComicResult(
                source["id"], source["title"], source["provider"], strip_date.isoformat(), page_url,
                images, "ok" if strip_date == day else "stale", author=source.get("author")
            )
    return ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "unavailable", "No valid strip found in the 8-day window")
