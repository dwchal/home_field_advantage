#!/usr/bin/env python3
"""One-time backfill of historical season data per league.

Pulls every season from each league's earliest free-data year forward and merges
the results into ``data/raw/<league>_games.csv``. Re-running the daily pipeline
preserves the backfilled history (the daily writer now merges by ``game_id``
instead of overwriting), so a single backfill seeds the dataset permanently.

Per-league floors reflect what each free API actually exposes:

* MLB (statsapi.mlb.com) — 1901, the start of the modern AL/NL era.
* NHL (api-web.nhle.com) — 1917, the league's founding season.
* NBA (api.balldontlie.io) — 1946, the BAA founding. Requires
  ``BALLDONTLIE_API_KEY``; some free/low tiers cap historical access, in which
  case older seasons will simply return empty.
* NFL (ESPN scoreboard) — 1970, the AFL-NFL merger. ESPN's coverage of earlier
  seasons is too sparse to be useful (one or two games per season range).

Usage::

    python3 scripts/backfill_history.py                  # all leagues, full history
    python3 scripts/backfill_history.py --leagues mlb,nhl
    python3 scripts/backfill_history.py --mlb-from 2000 --to 2024
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from home_field_advantage.ingest.api_ingest import (  # noqa: E402
    _adapt_mlb_statsapi,
    _adapt_nba_balldontlie,
    _adapt_nfl_espn,
    _adapt_nhl_api_web,
    _fetch_url,
    _nba_has_next_page,
    merge_records_into_csv,
)


LEAGUE_FLOORS = {
    "mlb": 1901,
    "nhl": 1917,
    "nba": 1946,
    "nfl": 1970,
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def backfill_mlb(start: int, end: int, sleep: float) -> list[dict]:
    records: list[dict] = []
    for season in range(start, end + 1):
        url = (
            "https://statsapi.mlb.com/api/v1/schedule"
            f"?sportId=1&season={season}&gameType=R&hydrate=linescore"
        )
        try:
            season_records = _adapt_mlb_statsapi(_fetch_url(url, None))
        except Exception as exc:
            _log(f"  MLB {season}: ERROR {exc}")
            continue
        records.extend(season_records)
        _log(f"  MLB {season}: {len(season_records)} games")
        time.sleep(sleep)
    return records


def backfill_nhl(start: int, end: int, sleep: float) -> list[dict]:
    """Iterate weekly /v1/schedule/{date} windows from Sep through Aug of each season."""
    records: list[dict] = []
    seen: set[str] = set()
    for season in range(start, end + 1):
        cursor = date(season, 9, 1)
        stop = date(season + 1, 8, 1)
        season_count = 0
        while cursor < stop:
            url = f"https://api-web.nhle.com/v1/schedule/{cursor.isoformat()}"
            try:
                week = _adapt_nhl_api_web(_fetch_url(url, None))
            except Exception:
                week = []
            for r in week:
                gid = str(r["game_id"])
                if gid not in seen:
                    seen.add(gid)
                    records.append(r)
                    season_count += 1
            cursor += timedelta(days=7)
            time.sleep(sleep)
        _log(f"  NHL {season}: {season_count} games")
    return records


def backfill_nba(start: int, end: int, token_env: str, sleep: float) -> list[dict]:
    records: list[dict] = []
    for season in range(start, end + 1):
        page = 1
        season_count = 0
        while True:
            url = (
                "https://api.balldontlie.io/v1/games"
                f"?seasons[]={season}&per_page=100&page={page}"
            )
            try:
                raw = _fetch_url(url, token_env)
            except Exception as exc:
                _log(f"  NBA {season} page {page}: ERROR {exc}")
                break
            page_records = _adapt_nba_balldontlie(raw)
            records.extend(page_records)
            season_count += len(page_records)
            if not _nba_has_next_page(raw):
                break
            page += 1
            time.sleep(sleep)
        _log(f"  NBA {season}: {season_count} games")
        time.sleep(sleep)
    return records


def backfill_nfl(start: int, end: int, sleep: float) -> list[dict]:
    """Pull each NFL season via the ESPN ``dates=YYYY0801-YYYY+10301`` window."""
    records: list[dict] = []
    seen: set[str] = set()
    for season in range(start, end + 1):
        url = (
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
            f"?dates={season}0801-{season + 1}0301&limit=1000"
        )
        try:
            season_records = _adapt_nfl_espn(_fetch_url(url, None))
        except Exception as exc:
            _log(f"  NFL {season}: ERROR {exc}")
            continue
        added = 0
        for r in season_records:
            gid = str(r["game_id"])
            if gid not in seen:
                seen.add(gid)
                records.append(r)
                added += 1
        _log(f"  NFL {season}: {added} games")
        time.sleep(sleep)
    return records


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--leagues",
        default="mlb,nhl,nba,nfl",
        help="Comma-separated leagues to backfill (default: all).",
    )
    parser.add_argument("--mlb-from", type=int, default=LEAGUE_FLOORS["mlb"])
    parser.add_argument("--nhl-from", type=int, default=LEAGUE_FLOORS["nhl"])
    parser.add_argument("--nba-from", type=int, default=LEAGUE_FLOORS["nba"])
    parser.add_argument("--nfl-from", type=int, default=LEAGUE_FLOORS["nfl"])
    parser.add_argument(
        "--to",
        type=int,
        default=date.today().year,
        help="Inclusive last season year (default: current year).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.3,
        help="Seconds to sleep between API requests (rate-limit cushion).",
    )
    parser.add_argument(
        "--nba-token-env",
        default="BALLDONTLIE_API_KEY",
        help="Env var holding the BallDontLie API key.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    leagues = [l.strip().lower() for l in args.leagues.split(",") if l.strip()]
    raw_dir = ROOT / "data" / "raw"

    if "mlb" in leagues:
        _log(f"Backfilling MLB {args.mlb_from}-{args.to}")
        recs = backfill_mlb(args.mlb_from, args.to, args.sleep)
        merge_records_into_csv(recs, raw_dir / "mlb_games.csv")
        _log(f"  MLB total fetched this run: {len(recs)}")

    if "nhl" in leagues:
        _log(f"Backfilling NHL {args.nhl_from}-{args.to}")
        recs = backfill_nhl(args.nhl_from, args.to, args.sleep)
        merge_records_into_csv(recs, raw_dir / "nhl_games.csv")
        _log(f"  NHL total fetched this run: {len(recs)}")

    if "nba" in leagues:
        _log(f"Backfilling NBA {args.nba_from}-{args.to}")
        recs = backfill_nba(args.nba_from, args.to, args.nba_token_env, args.sleep)
        merge_records_into_csv(recs, raw_dir / "nba_games.csv")
        _log(f"  NBA total fetched this run: {len(recs)}")

    if "nfl" in leagues:
        _log(f"Backfilling NFL {args.nfl_from}-{args.to}")
        recs = backfill_nfl(args.nfl_from, args.to, args.sleep)
        merge_records_into_csv(recs, raw_dir / "nfl_games.csv")
        _log(f"  NFL total fetched this run: {len(recs)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
