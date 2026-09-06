from bs4 import BeautifulSoup

from .base import CandidateArticle, HttpClient, canonicalize_url, extract_articles


async def collect(source: dict, client: HttpClient) -> list[CandidateArticle]:
    feed_url = source.get("feed_url")
    response = await client.get(feed_url or source["url"])
    if feed_url:
        soup = BeautifulSoup(response.text, "xml")
        articles: list[CandidateArticle] = []
        for item in soup.select("item"):
            title = item.find("title")
            link = item.find("link")
            url = link.get("href") if link else None
            url = url or (link.get_text(strip=True) if link else "")
            if not title or not url.startswith("https://"):
                continue
            canonical_url = canonicalize_url(url)
            articles.append(CandidateArticle(
                publisher=source["publisher"], headline=title.get_text(" ", strip=True), url=canonical_url,
                canonical_url=canonical_url, published_at=(item.find("pubDate").get_text(strip=True) if item.find("pubDate") else None),
                source_page=source["url"], source_id=source["id"], section=source["section"],
                subsection=source["subsection"], subsection_title=source["title"], specificity=int(source.get("specificity", 0)),
            ))
        return articles
    articles = extract_articles(response.text, source)
    return [article for article in articles if "/news/" in article.canonical_url or "/story/" in article.canonical_url]
