import asyncio
import json
import os
from datetime import date, timedelta
from pathlib import Path

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
    assert process.stdin and process.stdout and process.stderr
    process.stdin.write(json.dumps(sources).encode())
    await process.stdin.drain()
    process.stdin.close()

    async def relay_progress() -> str:
        lines: list[str] = []
        while line := await process.stderr.readline():
            text = line.decode(errors="replace")
            lines.append(text)
            print(text, end="", flush=True)
        return "".join(lines)

    progress_task = asyncio.create_task(relay_progress())
    stdout = await process.stdout.read()
    await process.wait()
    stderr = (await progress_task).encode()
    if process.returncode != 0:
        detail = stderr.decode(errors="replace").strip()[-240:] or "Rendered collector failed"
        if os.environ.get("MORNING_PAPER_CDP_URL"):
            raise RuntimeError(detail)
        return [ComicResult(source["id"], source["title"], source["provider"], None, source["base_url"], [], "error", detail) for source in sources]
    try:
        values = json.loads(stdout)
        if os.environ.get("MORNING_PAPER_CDP_URL") and not any(
            value.get("status") in {"ok", "stale"} for value in values
        ):
            details = next((value.get("detail") for value in values if value.get("detail")), "No strip diagnostic was returned")
            raise RuntimeError(f"The dedicated Chrome session collected zero GoComics strips. {details}")
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
