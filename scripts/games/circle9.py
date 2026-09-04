from scripts.news.base import HttpClient


async def collect(source: dict, client: HttpClient) -> dict:
    try:
        response = await client.get(source.get("embed_url", source["url"]))
        frame_options = response.headers.get("x-frame-options", "").lower()
        frame_ancestors = response.headers.get("content-security-policy", "").lower()
        blocked = frame_options in {"deny", "sameorigin"} or ("frame-ancestors" in frame_ancestors and "*" not in frame_ancestors)
        return {**source, "embed_url": None if blocked else str(response.url), "status": "unavailable" if blocked else "ok"}
    except Exception as exc:
        return {**source, "embed_url": None, "status": "error", "detail": str(exc)}
