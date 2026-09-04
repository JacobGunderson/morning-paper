from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

TRACKING = {"cmpid", "fbclid", "gclid", "output", "ref", "source"}


@dataclass
class CandidateArticle:
    publisher: str
    headline: str
    url: str
    canonical_url: str
    published_at: str | None
    source_page: str
    source_id: str = ""
    section: str = ""
    subsection: str = ""
    subsection_title: str = ""
    specificity: int = 0

    def public(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if key not in {"source_id", "section", "subsection", "subsection_title", "specificity"}}


def canonicalize_url(url: str, base_url: str = "") -> str:
    absolute = urljoin(base_url, url)
    parts = urlsplit(absolute)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if not key.lower().startswith("utm_") and key.lower() not in TRACKING]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def normalize_headline(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).lower()
    text = re.sub(r"\s*[|\-–—]\s*(ap news|politico)\s*$", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def same_story(a: CandidateArticle, b: CandidateArticle) -> bool:
    if a.canonical_url == b.canonical_url:
        return True
    if a.publisher != b.publisher:
        return False
    left, right = normalize_headline(a.headline), normalize_headline(b.headline)
    if left == right:
        return True
    return len(left) > 35 and len(right) > 35 and SequenceMatcher(None, left, right).ratio() >= 0.94


class HttpClient:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "MorningPaper/1.0 (+personal GitHub Pages feed reader)"})

    async def get(self, url: str) -> httpx.Response:
        error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                error = exc
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
        raise RuntimeError(f"request failed after 3 attempts: {url}: {error}")

    async def close(self) -> None:
        await self.client.aclose()


def _jsonld_articles(soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            raw = json.loads(tag.string or "null")
        except json.JSONDecodeError:
            continue
        stack = raw if isinstance(raw, list) else [raw]
        while stack:
            item = stack.pop()
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("@graph"), list):
                stack.extend(item["@graph"])
            kind = item.get("@type", "")
            kinds = kind if isinstance(kind, list) else [kind]
            if any(value in {"NewsArticle", "Article", "ReportageNewsArticle"} for value in kinds):
                url = item.get("url") or item.get("mainEntityOfPage")
                if isinstance(url, dict):
                    url = url.get("@id")
                headline = item.get("headline") or item.get("name")
                if isinstance(url, str) and isinstance(headline, str):
                    output.append({"headline": headline, "url": urljoin(base_url, url), "published_at": item.get("datePublished")})
    return output


def extract_articles(html: str, source: dict[str, Any]) -> list[CandidateArticle]:
    soup = BeautifulSoup(html, "lxml")
    base_url = source["url"]
    raw = _jsonld_articles(soup, base_url)
    if len(raw) < 10:
        seen = {canonicalize_url(item["url"]) for item in raw}
        for heading in soup.select("article h1, article h2, article h3, main h2, main h3"):
            link = heading.find("a", href=True) or heading.find_parent("a", href=True)
            if not link:
                continue
            url = urljoin(base_url, link["href"])
            title = heading.get_text(" ", strip=True)
            canonical = canonicalize_url(url)
            if title and canonical not in seen:
                seen.add(canonical); raw.append({"headline": title, "url": url, "published_at": None})
    articles: list[CandidateArticle] = []
    for item in raw[:30]:
        url = canonicalize_url(str(item["url"]), base_url)
        if not url.startswith("https://") or len(str(item["headline"]).strip()) < 8:
            continue
        articles.append(CandidateArticle(
            publisher=source["publisher"], headline=str(item["headline"]).strip(), url=url, canonical_url=url,
            published_at=item.get("published_at"), source_page=base_url, source_id=source["id"], section=source["section"],
            subsection=source["subsection"], subsection_title=source["title"], specificity=int(source.get("specificity", 0))))
    return articles


def assign_unique(candidates_by_source: dict[str, list[CandidateArticle]], sources: list[dict[str, Any]]) -> dict[str, list[CandidateArticle]]:
    assigned: dict[str, list[CandidateArticle]] = {source["id"]: [] for source in sources}
    claimed: list[CandidateArticle] = []
    # Specific sections claim stories first; each source scans its full candidate pool to refill after duplicates.
    for source in sorted(sources, key=lambda value: int(value.get("specificity", 0)), reverse=True):
        for candidate in candidates_by_source.get(source["id"], []):
            if any(same_story(candidate, existing) for existing in claimed):
                continue
            assigned[source["id"]].append(candidate); claimed.append(candidate)
            if len(assigned[source["id"]]) >= int(source.get("limit", 10)):
                break
    return assigned
