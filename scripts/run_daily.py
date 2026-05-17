#!/usr/bin/env python3
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from home_field_advantage.analyze.metrics import compute_league_metrics, compute_team_metrics
from home_field_advantage.ingest.csv_ingest import discover_raw_files
from home_field_advantage.report.markdown_report import build_markdown_report, write_report
from home_field_advantage.transform.normalize import normalize_games, write_processed_games


DEFAULT_LEAGUES = ["nfl", "nba", "mlb", "nhl"]


def run() -> None:
    raw_dir = ROOT / "data" / "raw"
    processed_games_file = ROOT / "data" / "processed" / "games.csv"
    reports_dir = ROOT / "reports"

    raw_files = discover_raw_files(raw_dir, DEFAULT_LEAGUES)
    games = normalize_games(raw_files)
    write_processed_games(games, processed_games_file)

    league_metrics = compute_league_metrics(games)
    team_metrics = compute_team_metrics(games)

    today = date.today()
    markdown = build_markdown_report(league_metrics, team_metrics, today)
    report_path = write_report(markdown, reports_dir, today)

    print(f"Raw files discovered: {len(raw_files)}")
    print(f"Games processed: {len(games)}")
    print(f"Report written: {report_path}")


if __name__ == "__main__":
    run()
