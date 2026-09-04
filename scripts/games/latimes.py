from __future__ import annotations

import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.news.base import HttpClient


def resolve_embed(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for iframe in soup.select("iframe[src]"):
        src = urljoin(page_url, iframe["src"])
        if any(marker in src.lower() for marker in ("amuselabs", "puzzleme", "crossword")):
            return src
    for script in soup.select("script"):
        text = script.string or ""
        if "amuselabs" not in text.lower() and "puzzleme" not in text.lower():
            continue
        for token in text.replace("\\/", "/").split('"'):
            if token.startswith("http") and any(marker in token.lower() for marker in ("amuselabs", "puzzleme")):
                return token
    return None


async def collect(source: dict, client: HttpClient) -> dict:
    try:
        response = await client.get(source["url"])
        embed = resolve_embed(response.text, source["url"])
        return {**source, "embed_url": embed, "status": "ok" if embed else "unavailable"}
    except Exception as exc:
        return {**source, "status": "error", "detail": str(exc)}
