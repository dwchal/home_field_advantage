from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from home_field_advantage.transform.normalize import GameRecord


@dataclass
class TrendPoint:
    date: str
    cumulative_games: int
    cumulative_home_wins: int

    @property
    def cumulative_home_win_pct(self) -> float:
        return self.cumulative_home_wins / self.cumulative_games if self.cumulative_games else 0.0


def _accumulate(games: list[GameRecord]) -> list[TrendPoint]:
    games = sorted(games, key=lambda g: g.date)
    points: list[TrendPoint] = []
    wins = 0
    played = 0
    for g in games:
        played += 1
        if g.home_score > g.away_score:
            wins += 1
        if points and points[-1].date == g.date:
            points[-1] = TrendPoint(g.date, played, wins)
        else:
            points.append(TrendPoint(g.date, played, wins))
    return points


def cumulative_league_trend(games: list[GameRecord]) -> dict[str, list[TrendPoint]]:
    by_league: dict[str, list[GameRecord]] = defaultdict(list)
    for game in games:
        if game.neutral_site:
            continue
        by_league[game.league].append(game)
    return {league: _accumulate(group) for league, group in by_league.items()}


def cumulative_team_home_trend(
    games: list[GameRecord], teams: list[str]
) -> dict[str, list[TrendPoint]]:
    team_set = set(teams)
    by_team: dict[str, list[GameRecord]] = defaultdict(list)
    for game in games:
        if game.neutral_site:
            continue
        if game.home_team in team_set:
            by_team[game.home_team].append(game)
    return {team: _accumulate(group) for team, group in by_team.items()}
