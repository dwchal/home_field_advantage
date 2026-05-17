from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from home_field_advantage.transform.normalize import GameRecord


@dataclass
class MetricSummary:
    games: int = 0
    home_wins: int = 0
    home_points: int = 0
    away_points: int = 0

    @property
    def home_win_pct(self) -> float:
        return (self.home_wins / self.games) if self.games else 0.0

    @property
    def avg_home_margin(self) -> float:
        return ((self.home_points - self.away_points) / self.games) if self.games else 0.0


def compute_league_metrics(games: list[GameRecord]) -> dict[str, MetricSummary]:
    metrics: dict[str, MetricSummary] = defaultdict(MetricSummary)
    for game in games:
        if game.neutral_site:
            continue
        m = metrics[game.league]
        m.games += 1
        m.home_points += game.home_score
        m.away_points += game.away_score
        if game.home_score > game.away_score:
            m.home_wins += 1
    return dict(metrics)


def compute_team_metrics(games: list[GameRecord]) -> dict[str, MetricSummary]:
    metrics: dict[str, MetricSummary] = defaultdict(MetricSummary)
    for game in games:
        if game.neutral_site:
            continue
        m = metrics[game.home_team]
        m.games += 1
        m.home_points += game.home_score
        m.away_points += game.away_score
        if game.home_score > game.away_score:
            m.home_wins += 1
    return dict(metrics)
