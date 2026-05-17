from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from home_field_advantage.transform.normalize import GameRecord


SPOTLIGHT_CITIES: tuple[str, ...] = ("Minnesota", "Pittsburgh")


def find_spotlight_teams(games: list[GameRecord]) -> list[str]:
    teams: set[str] = set()
    for game in games:
        for name in (game.home_team, game.away_team):
            for city in SPOTLIGHT_CITIES:
                if name.startswith(city + " "):
                    teams.add(name)
    return sorted(teams)


@dataclass
class TeamSplit:
    team: str
    league: str
    home_games: int = 0
    home_wins: int = 0
    away_games: int = 0
    away_wins: int = 0
    home_pf: int = 0
    home_pa: int = 0
    away_pf: int = 0
    away_pa: int = 0
    longest_home_win_streak: int = 0
    recent_home_form: str = ""
    biggest_home_win: tuple[int, str, str] | None = None

    @property
    def home_win_pct(self) -> float:
        return self.home_wins / self.home_games if self.home_games else 0.0

    @property
    def away_win_pct(self) -> float:
        return self.away_wins / self.away_games if self.away_games else 0.0

    @property
    def hfa_lift(self) -> float:
        return self.home_win_pct - self.away_win_pct

    @property
    def avg_home_margin(self) -> float:
        return (self.home_pf - self.home_pa) / self.home_games if self.home_games else 0.0

    @property
    def avg_away_margin(self) -> float:
        return (self.away_pf - self.away_pa) / self.away_games if self.away_games else 0.0


def compute_team_splits(games: list[GameRecord], teams: list[str]) -> list[TeamSplit]:
    by_team: dict[str, TeamSplit] = {}
    home_results: dict[str, list[tuple[str, str]]] = defaultdict(list)
    team_set = set(teams)

    for game in games:
        if game.neutral_site:
            continue
        if game.home_team in team_set:
            split = by_team.setdefault(
                game.home_team, TeamSplit(team=game.home_team, league=game.league)
            )
            split.home_games += 1
            split.home_pf += game.home_score
            split.home_pa += game.away_score
            margin = game.home_score - game.away_score
            if game.home_score > game.away_score:
                split.home_wins += 1
                result = "W"
                if split.biggest_home_win is None or margin > split.biggest_home_win[0]:
                    split.biggest_home_win = (margin, game.away_team, game.date)
            elif game.home_score < game.away_score:
                result = "L"
            else:
                result = "T"
            home_results[game.home_team].append((game.date, result))
        if game.away_team in team_set:
            split = by_team.setdefault(
                game.away_team, TeamSplit(team=game.away_team, league=game.league)
            )
            split.away_games += 1
            split.away_pf += game.away_score
            split.away_pa += game.home_score
            if game.away_score > game.home_score:
                split.away_wins += 1

    for team, split in by_team.items():
        results = sorted(home_results.get(team, []), key=lambda r: r[0])
        longest = 0
        current = 0
        for _, r in results:
            if r == "W":
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        split.longest_home_win_streak = longest
        split.recent_home_form = "".join(r for _, r in results[-10:])

    return [by_team[t] for t in sorted(by_team)]
