from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class GameRecord:
    game_id: str
    date: str
    league: str
    season: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    neutral_site: bool


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def normalize_games(raw_files: list[Path]) -> list[GameRecord]:
    games: list[GameRecord] = []
    for path in raw_files:
        league = path.stem.replace("_games", "").upper()
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                games.append(
                    GameRecord(
                        game_id=row["game_id"],
                        date=row["date"],
                        league=league,
                        season=row["season"],
                        home_team=row["home_team"].strip(),
                        away_team=row["away_team"].strip(),
                        home_score=int(row["home_score"]),
                        away_score=int(row["away_score"]),
                        neutral_site=parse_bool(row["neutral_site"]),
                    )
                )
    games.sort(key=lambda g: (g.date, g.league, g.game_id))
    return games


def write_processed_games(games: list[GameRecord], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(GameRecord.__annotations__.keys())
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for game in games:
            writer.writerow(asdict(game))
