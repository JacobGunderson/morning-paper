from .base import CandidateArticle, HttpClient, extract_articles


async def collect(source: dict, client: HttpClient) -> list[CandidateArticle]:
    response = await client.get(source["url"])
    return [article for article in extract_articles(response.text, source) if "/article/" in article.canonical_url or "/photo-gallery/" in article.canonical_url]
