from datetime import date
import yaml

from scripts.comics.base import ComicResult, dated_url, sort_key


def test_gocomics_date_url():
    assert dated_url("gocomics", "calvinandhobbes", date(2026, 9, 4)).endswith("/2026/09/04")


def test_comics_kingdom_date_url():
    assert dated_url("comics_kingdom", "bizarro", date(2026, 9, 4)).endswith("/2026-09-04")


def test_sort_ignores_the():
    titles = ["Wizard of Id", "The Far Side", "Goomer"]
    assert sorted(titles, key=sort_key) == ["The Far Side", "Goomer", "Wizard of Id"]


def test_stale_date_and_multiple_images_model():
    result = ComicResult("fox", "FoxTrot", "gocomics", "2026-08-30", "https://example.com", ["one.png", "two.png"], "stale")
    assert result.status == "stale" and len(result.images) == 2


def test_edison_lee_configured_once():
    with open("config/comics.yaml", encoding="utf-8") as handle:
        comics = yaml.safe_load(handle)["comics"]
    assert sum(comic["id"] == "edison_lee" for comic in comics) == 1
    assert len(comics) == 39
