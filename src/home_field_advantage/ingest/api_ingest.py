from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import os


@dataclass
class APISource:
    league: str
    url: str
    format: str = "csv"
    token_env: str | None = None
    query: dict[str, str] | None = None
    adapter: str | None = None
    paginated: bool = False


def _with_query(url: str, query: dict[str, str] | None) -> str:
    if not query:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(query)}"


def _headers(token_env: str | None) -> dict[str, str]:
    headers: dict[str, str] = {"User-Agent": "home-field-advantage/1.0"}
    if token_env:
        token = os.getenv(token_env)
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_url(url: str, token_env: str | None) -> bytes:
    request = Request(url=url, headers=_headers(token_env))
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc


# --- Adapters: transform each API's JSON response → canonical list[dict] ---

def _adapt_mlb_statsapi(raw_bytes: bytes) -> list[dict[str, Any]]:
    """MLB Stats API: statsapi.mlb.com/api/v1/schedule"""
    payload = json.loads(raw_bytes.decode("utf-8"))
    records: list[dict[str, Any]] = []
    for date_entry in payload.get("dates", []):
        for game in date_entry.get("games", []):
            home = game.get("teams", {}).get("home", {})
            away = game.get("teams", {}).get("away", {})
            if home.get("score") is None or away.get("score") is None:
                continue  # game not yet played
            records.append({
                "game_id": str(game["gamePk"]),
                "date": game.get("officialDate", game["gameDate"][:10]),
                "season": str(game.get("season", "")),
                "home_team": home.get("team", {}).get("name", ""),
                "away_team": away.get("team", {}).get("name", ""),
                "home_score": int(home["score"]),
                "away_score": int(away["score"]),
                "neutral_site": "false",
            })
    return records


def _adapt_nhl_statsapi(raw_bytes: bytes) -> list[dict[str, Any]]:
    """NHL Stats API: statsapi.web.nhl.com/api/v1/schedule"""
    payload = json.loads(raw_bytes.decode("utf-8"))
    records: list[dict[str, Any]] = []
    for date_entry in payload.get("dates", []):
        for game in date_entry.get("games", []):
            home = game.get("teams", {}).get("home", {})
            away = game.get("teams", {}).get("away", {})
            if home.get("score") is None or away.get("score") is None:
                continue  # game not yet played
            records.append({
                "game_id": str(game["gamePk"]),
                "date": game["gameDate"][:10],
                "season": str(game.get("season", "")),
                "home_team": home.get("team", {}).get("name", ""),
                "away_team": away.get("team", {}).get("name", ""),
                "home_score": int(home["score"]),
                "away_score": int(away["score"]),
                "neutral_site": "false",
            })
    return records


def _adapt_nba_balldontlie(raw_bytes: bytes) -> list[dict[str, Any]]:
    """BallDontLie NBA API: api.balldontlie.io/v1/games"""
    payload = json.loads(raw_bytes.decode("utf-8"))
    records: list[dict[str, Any]] = []
    for game in payload.get("data", []):
        home_score = game.get("home_team_score")
        away_score = game.get("visitor_team_score")
        if home_score is None or away_score is None:
            continue  # game not yet played
        records.append({
            "game_id": str(game["id"]),
            "date": game["date"][:10],
            "season": str(game.get("season", "")),
            "home_team": game.get("home_team", {}).get("full_name", ""),
            "away_team": game.get("visitor_team", {}).get("full_name", ""),
            "home_score": int(home_score),
            "away_score": int(away_score),
            "neutral_site": "false",
        })
    return records


def _nba_has_next_page(raw_bytes: bytes) -> bool:
    payload = json.loads(raw_bytes.decode("utf-8"))
    return bool(payload.get("meta", {}).get("next_page"))


def _adapt_nfl_espn(raw_bytes: bytes) -> list[dict[str, Any]]:
    """ESPN NFL scoreboard API: site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"""
    payload = json.loads(raw_bytes.decode("utf-8"))
    records: list[dict[str, Any]] = []
    for event in payload.get("events", []):
        season_year = str(event.get("season", {}).get("year", ""))
        for comp in event.get("competitions", []):
            neutral = comp.get("neutralSite", False)
            competitors = comp.get("competitors", [])
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            if not home.get("score") or not away.get("score"):
                continue  # game not yet played
            records.append({
                "game_id": str(event["id"]),
                "date": comp["date"][:10],
                "season": season_year,
                "home_team": home.get("team", {}).get("displayName", ""),
                "away_team": away.get("team", {}).get("displayName", ""),
                "home_score": int(home["score"]),
                "away_score": int(away["score"]),
                "neutral_site": "true" if neutral else "false",
            })
    return records


_ADAPTERS: dict[str, Callable[[bytes], list[dict[str, Any]]]] = {
    "mlb_statsapi": _adapt_mlb_statsapi,
    "nhl_statsapi": _adapt_nhl_statsapi,
    "nba_balldontlie": _adapt_nba_balldontlie,
    "nfl_espn": _adapt_nfl_espn,
}


def _write_records_to_csv(records: list[dict[str, Any]], output_file: Path) -> None:
    if not records:
        return
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0].keys())
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def _write_csv_bytes(raw_bytes: bytes, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(raw_bytes)


def _write_json_rows(raw_bytes: bytes, output_file: Path) -> None:
    payload = json.loads(raw_bytes.decode("utf-8"))
    rows: list[dict[str, Any]]
    if isinstance(payload, dict) and "games" in payload and isinstance(payload["games"], list):
        rows = payload["games"]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("JSON API payload must be a list or object with 'games' list")

    if not rows:
        return

    fieldnames = sorted({key for row in rows for key in row.keys()})
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fetch_paginated(
    source: APISource,
    adapter_fn: Callable[[bytes], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Fetch all pages from a BallDontLie-style paginated API."""
    all_records: list[dict[str, Any]] = []
    page = 1
    while True:
        query = dict(source.query or {})
        query["page"] = str(page)
        url = _with_query(source.url, query)
        raw_bytes = _fetch_url(url, source.token_env)
        records = adapter_fn(raw_bytes)
        all_records.extend(records)
        if not _nba_has_next_page(raw_bytes):
            break
        page += 1
    return all_records


def fetch_api_source(source: APISource, raw_dir: Path) -> Path:
    output_file = raw_dir / f"{source.league.lower()}_games.csv"

    if source.adapter and source.format.lower() == "json":
        adapter_fn = _ADAPTERS.get(source.adapter)
        if adapter_fn is None:
            raise ValueError(f"Unknown adapter: {source.adapter!r}")

        if source.paginated:
            records = _fetch_paginated(source, adapter_fn)
        else:
            url = _with_query(source.url, source.query)
            raw_bytes = _fetch_url(url, source.token_env)
            records = adapter_fn(raw_bytes)

        _write_records_to_csv(records, output_file)
        return output_file

    # Legacy path: no adapter — raw pass-through
    url = _with_query(source.url, source.query)
    raw_bytes = _fetch_url(url, source.token_env)

    if source.format.lower() == "json":
        _write_json_rows(raw_bytes, output_file)
    else:
        _write_csv_bytes(raw_bytes, output_file)
    return output_file


def sync_api_sources(sources: list[APISource], raw_dir: Path) -> list[Path]:
    output_files: list[Path] = []
    for source in sources:
        output_files.append(fetch_api_source(source, raw_dir))
    return output_files
