from scripts.news.base import CandidateArticle, assign_unique, canonicalize_url, extract_articles, normalize_headline


def article(url: str, headline: str, source_id: str, specificity: int) -> CandidateArticle:
    return CandidateArticle("AP", headline, url, canonicalize_url(url), None, "https://apnews.com", source_id, "international", source_id, source_id.title(), specificity)


def test_canonical_url_removes_tracking_fragment_and_slash():
    assert canonicalize_url("https://APNEWS.com/story/example/?utm_source=x&foo=1#part") == "https://apnews.com/story/example?foo=1"


def test_headline_normalization():
    assert normalize_headline("  A Story — AP News ") == "a story"


def test_specific_section_wins_and_general_refills_to_limit():
    sources = [
        {"id": "world", "limit": 2, "specificity": 0},
        {"id": "china", "limit": 1, "specificity": 100},
    ]
    duplicate = article("https://apnews.com/a", "Shared story", "china", 100)
    assigned = assign_unique({
        "world": [article("https://apnews.com/a?utm_source=x", "Shared story", "world", 0), article("https://apnews.com/b", "Second", "world", 0), article("https://apnews.com/c", "Third", "world", 0)],
        "china": [duplicate],
    }, sources)
    assert [item.canonical_url for item in assigned["china"]] == ["https://apnews.com/a"]
    assert [item.canonical_url for item in assigned["world"]] == ["https://apnews.com/b", "https://apnews.com/c"]


def test_ap_semantic_fixture_parser():
    html = '<main><article><h2><a href="/article/one">A sufficiently descriptive AP headline</a></h2></article></main>'
    source = {"publisher": "AP", "url": "https://apnews.com/world-news", "id": "ap_world", "section": "international", "subsection": "world", "title": "World", "specificity": 0}
    result = extract_articles(html, source)
    assert result[0].canonical_url == "https://apnews.com/article/one"


def test_politico_jsonld_fixture_parser():
    html = '<script type="application/ld+json">{"@type":"NewsArticle","headline":"A sufficiently descriptive Politico headline","url":"https://www.politico.com/news/2026/09/04/example","datePublished":"2026-09-04"}</script>'
    source = {"publisher": "POLITICO", "url": "https://www.politico.com/congress-news-updates-analysis", "id": "politico", "section": "usa", "subsection": "congress", "title": "Congress", "specificity": 100}
    result = extract_articles(html, source)
    assert result[0].published_at == "2026-09-04"
