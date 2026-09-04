from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from scripts.news.base import HttpClient

BASE = "https://www.nytimes.com/svc"
OFFICIAL = {
    "wordle": "https://www.nytimes.com/games/wordle/index.html",
    "connections": "https://www.nytimes.com/games/connections",
    "strands": "https://www.nytimes.com/games/strands",
}


def _unavailable(game: str, day: date, detail: str) -> dict[str, Any]:
    return {"date": day.isoformat(), "status": "unavailable", "source_url": OFFICIAL[game], "detail": detail}


def normalize_wordle(payload: dict[str, Any], day: date) -> dict[str, Any]:
    solution = str(payload.get("solution", "")).strip().lower()
    if len(solution) != 5 or not solution.isalpha():
        return _unavailable("wordle", day, "Payload did not contain a five-letter solution")
    return {"date": str(payload.get("print_date") or day.isoformat()), "solution": solution, "status": "ok", "source_url": OFFICIAL["wordle"]}


def normalize_connections(payload: dict[str, Any], day: date) -> dict[str, Any]:
    raw_groups = payload.get("categories") or payload.get("groups") or []
    groups = []
    for index, raw in enumerate(raw_groups):
        members = raw.get("cards") or raw.get("members") or []
        words = [str(card.get("content") if isinstance(card, dict) else card).upper() for card in members]
        if len(words) == 4:
            groups.append({"level": int(raw.get("difficulty", raw.get("level", index))), "category": str(raw.get("title") or raw.get("category") or "GROUP"), "members": words})
    if len(groups) != 4 or len({word for group in groups for word in group["members"]}) != 16:
        return _unavailable("connections", day, "Payload did not contain four groups of four unique words")
    return {"date": str(payload.get("print_date") or day.isoformat()), "groups": groups, "status": "ok", "source_url": OFFICIAL["connections"]}


def find_paths(grid: list[str], word: str) -> list[list[tuple[int, int]]]:
    rows, columns = len(grid), len(grid[0])
    output: list[list[tuple[int, int]]] = []
    target = word.upper().replace(" ", "").replace("-", "")

    def dfs(row: int, column: int, index: int, path: list[tuple[int, int]], used: set[tuple[int, int]]) -> None:
        if grid[row][column].upper() != target[index]:
            return
        next_path = [*path, (row, column)]
        if index == len(target) - 1:
            output.append(next_path)
            return
        used = {*used, (row, column)}
        for next_row in range(max(0, row - 1), min(rows, row + 2)):
            for next_column in range(max(0, column - 1), min(columns, column + 2)):
                if (next_row, next_column) not in used:
                    dfs(next_row, next_column, index + 1, next_path, used)

    for row in range(rows):
        for column in range(columns):
            dfs(row, column, 0, [], set())
    return output


def assign_paths(grid: list[str], words: Iterable[str]) -> dict[str, list[tuple[int, int]]] | None:
    candidates = {word: find_paths(grid, word) for word in words}
    ordered = sorted(candidates, key=lambda word: len(candidates[word]))
    selected: dict[str, list[tuple[int, int]]] = {}

    def solve(index: int, occupied: set[tuple[int, int]]) -> bool:
        if index == len(ordered):
            return True
        word = ordered[index]
        for path in candidates[word]:
            cells = set(path)
            if not cells & occupied:
                selected[word] = path
                if solve(index + 1, occupied | cells):
                    return True
        selected.pop(word, None)
        return False

    return selected if solve(0, set()) else None


def _grid_from_payload(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("startingBoard") or payload.get("grid") or payload.get("board") or []
    if isinstance(raw, str):
        raw = list(raw)
    if isinstance(raw, list) and len(raw) == 48 and all(isinstance(value, str) and len(value) == 1 for value in raw):
        return ["".join(raw[index:index + 6]) for index in range(0, 48, 6)]
    if isinstance(raw, list) and raw and all(isinstance(row, list) for row in raw):
        return ["".join(map(str, row)) for row in raw]
    return [str(row) for row in raw] if isinstance(raw, list) else []


def normalize_strands(payload: dict[str, Any], day: date) -> dict[str, Any]:
    grid = _grid_from_payload(payload)
    theme = str(payload.get("clue") or payload.get("themeClue") or payload.get("theme") or "")
    words = [str(word).upper() for word in (payload.get("themeWords") or payload.get("theme_words") or [])]
    spangram = str(payload.get("spangram") or "").upper()
    if spangram and spangram not in words:
        words.append(spangram)
    if len(grid) != 8 or any(len(row) != 6 for row in grid) or not words or not spangram:
        return _unavailable("strands", day, "Payload did not contain an 8-row by 6-column board and answers")
    supplied = payload.get("themeCoords") or {}
    paths = {word: [tuple(cell) for cell in supplied.get(word, [])] for word in words if word != spangram and supplied.get(word)}
    if payload.get("spangramCoords"):
        paths[spangram] = [tuple(cell) for cell in payload["spangramCoords"]]
    if set(paths) != set(words) or any(path not in find_paths(grid, word) for word, path in paths.items()):
        paths = assign_paths(grid, words)
    if not paths:
        return _unavailable("strands", day, "Could not derive a non-overlapping answer path assignment")
    answers = [{"word": word, "cells": paths[word], "spangram": word == spangram} for word in words]
    valid_words = sorted({str(word).upper() for word in payload.get("solutions", []) if len(str(word)) >= 4} - set(words))
    return {"date": str(payload.get("printDate") or payload.get("print_date") or day.isoformat()), "theme": theme, "grid": grid, "answers": answers, "valid_words": valid_words, "status": "ok", "source_url": OFFICIAL["strands"]}


async def collect(game: str, day: date, client: HttpClient) -> dict[str, Any]:
    url = f"{BASE}/{game}/v2/{day.isoformat()}.json"
    try:
        response = await client.get(url)
        payload = response.json()
        return {"wordle": normalize_wordle, "connections": normalize_connections, "strands": normalize_strands}[game](payload, day)
    except Exception as exc:
        return _unavailable(game, day, str(exc))
