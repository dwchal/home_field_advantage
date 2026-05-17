from __future__ import annotations

from pathlib import Path
from typing import Iterable


RAW_REQUIRED_COLUMNS = {
    "game_id",
    "date",
    "season",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "neutral_site",
}


def discover_raw_files(raw_dir: Path, leagues: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for league in leagues:
        candidate = raw_dir / f"{league.lower()}_games.csv"
        if candidate.exists():
            files.append(candidate)
    return files
