import asyncio
import json
from datetime import date
from pathlib import Path
from datetime import timedelta

from bs4 import BeautifulSoup
from scripts.news.base import HttpClient
from .base import ComicResult, dated_url, download_images


async def collect_all(sources: list[dict], day: date, output_dir: Path) -> list[ComicResult]:
    """Collect GoComics through its ordinary rendered dated pages in one browser session."""
    script = Path(__file__).with_name("gocomics_browser.mjs")
    process = await asyncio.create_subprocess_exec(
        "node", str(script), day.isoformat(), str(output_dir),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate(json.dumps(sources).encode())
    if process.returncode != 0:
        detail = stderr.decode(errors="replace").strip()[-240:] or "Rendered collector failed"
        return [ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", detail) for source in sources]
    try:
        values = json.loads(stdout)
        return [ComicResult(**value) for value in values]
    except (json.JSONDecodeError, TypeError) as exc:
        detail = f"Invalid rendered collector result: {exc}"
        return [ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", detail) for source in sources]


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
