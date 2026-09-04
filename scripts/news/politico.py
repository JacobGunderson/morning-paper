from .base import CandidateArticle, HttpClient, extract_articles


async def collect(source: dict, client: HttpClient) -> list[CandidateArticle]:
    response = await client.get(source["url"])
    articles = extract_articles(response.text, source)
    return [article for article in articles if "/news/" in article.canonical_url or "/story/" in article.canonical_url]
