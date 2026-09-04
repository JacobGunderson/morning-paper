from scripts.games.nyt import assign_paths, find_paths, normalize_connections, normalize_wordle
from datetime import date


def test_wordle_normalization():
    assert normalize_wordle({"solution": "crane"}, date(2026, 9, 4))["status"] == "ok"


def test_connections_normalization():
    payload = {"categories": [{"title": str(index), "cards": [{"content": f"{index}-{word}"} for word in range(4)]} for index in range(4)]}
    assert normalize_connections(payload, date(2026, 9, 4))["status"] == "ok"


def test_path_generation_and_global_non_overlap():
    grid = ["ABCDEF", "GHIJKL", "MNOPQR", "STUVWX", "YZABCD", "EFGHIJ", "KLMNOP", "QRSTUV"]
    assert [(0, 0), (0, 1), (0, 2)] in find_paths(grid, "ABC")
    paths = assign_paths(grid, ["ABC", "DEF"])
    assert paths and not set(paths["ABC"]) & set(paths["DEF"])
