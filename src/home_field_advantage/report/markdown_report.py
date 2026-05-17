from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from home_field_advantage.analyze.metrics import MetricSummary
from home_field_advantage.analyze.spotlight import (
    SPOTLIGHT_CITIES,
    TeamSplit,
    compute_team_splits,
    find_spotlight_teams,
)
from home_field_advantage.analyze.trends import (
    cumulative_league_trend,
    cumulative_team_home_trend,
)
from home_field_advantage.report.charts import (
    LineSeries,
    bar_chart_svg,
    date_to_ordinal,
    line_chart_svg,
)
from home_field_advantage.transform.normalize import GameRecord


@dataclass
class Report:
    markdown: str
    charts: dict[str, str] = field(default_factory=dict)


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _league_trend_chart(games: list[GameRecord]) -> str | None:
    trends = cumulative_league_trend(games)
    series: list[LineSeries] = []
    for league in sorted(trends):
        pts = trends[league]
        if len(pts) < 2:
            continue
        series.append(
            LineSeries(
                label=league,
                points=tuple((date_to_ordinal(p.date), p.cumulative_home_win_pct) for p in pts),
            )
        )
    if not series:
        return None
    return line_chart_svg(
        series,
        title="Season-to-date Home Win % by League",
        y_min=0.4,
        y_max=0.7,
    )


def _spotlight_bar_chart(splits: list[TeamSplit]) -> str | None:
    items = [
        (f"{s.team} ({s.league})", s.hfa_lift)
        for s in sorted(splits, key=lambda s: s.hfa_lift, reverse=True)
        if s.home_games and s.away_games
    ]
    if not items:
        return None
    return bar_chart_svg(
        items,
        title="Home Win % minus Away Win % (Spotlight Teams)",
        value_format="{:+.1%}",
        zero_centered=True,
    )


def _spotlight_trend_chart(games: list[GameRecord], teams: list[str]) -> str | None:
    trends = cumulative_team_home_trend(games, teams)
    series: list[LineSeries] = []
    for team in sorted(trends):
        pts = trends[team]
        if len(pts) < 2:
            continue
        series.append(
            LineSeries(
                label=team,
                points=tuple((date_to_ordinal(p.date), p.cumulative_home_win_pct) for p in pts),
            )
        )
    if not series:
        return None
    return line_chart_svg(
        series,
        title="Season-to-date Home Win % (Spotlight Teams)",
        y_min=0.0,
        y_max=1.0,
    )


def _render_league_table(league_metrics: dict[str, MetricSummary]) -> list[str]:
    lines = [
        "## League Summary",
        "",
        "| League | Games | Home Win % | Avg Home Margin |",
        "|---|---:|---:|---:|",
    ]
    for league in sorted(league_metrics):
        m = league_metrics[league]
        lines.append(
            f"| {league} | {m.games} | {_fmt_pct(m.home_win_pct)} | {m.avg_home_margin:+.2f} |"
        )
    return lines


def _render_top_teams_table(team_metrics: dict[str, MetricSummary]) -> list[str]:
    lines = [
        "## Team Summary (Top 15 by Home Win %)",
        "",
        "| Team | Home Games | Home Win % | Avg Home Margin |",
        "|---|---:|---:|---:|",
    ]
    ranked = sorted(
        team_metrics.items(),
        key=lambda item: (item[1].home_win_pct, item[1].games),
        reverse=True,
    )
    for team, m in ranked[:15]:
        lines.append(
            f"| {team} | {m.games} | {_fmt_pct(m.home_win_pct)} | {m.avg_home_margin:+.2f} |"
        )
    return lines


def _render_spotlight_section(splits: list[TeamSplit]) -> list[str]:
    cities = " & ".join(SPOTLIGHT_CITIES)
    lines = [
        f"## Spotlight: {cities}",
        "",
        "| Team | League | Home | Home Win % | Away | Away Win % | HFA Lift | Streak | Last 10 (Home) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for s in splits:
        lines.append(
            f"| {s.team} | {s.league} | "
            f"{s.home_wins}-{s.home_games - s.home_wins} | {_fmt_pct(s.home_win_pct)} | "
            f"{s.away_wins}-{s.away_games - s.away_wins} | {_fmt_pct(s.away_win_pct)} | "
            f"{s.hfa_lift:+.1%} | {s.longest_home_win_streak}W max | "
            f"`{s.recent_home_form or '—'}` |"
        )
    lines.append("")
    lines.append("### Biggest home wins")
    lines.append("")
    has_any = False
    for s in splits:
        if s.biggest_home_win:
            margin, opponent, day = s.biggest_home_win
            lines.append(f"- **{s.team}** beat {opponent} by {margin} on {day}")
            has_any = True
    if not has_any:
        lines.append("- _No home wins recorded yet._")
    return lines


def build_report(
    league_metrics: dict[str, MetricSummary],
    team_metrics: dict[str, MetricSummary],
    games: list[GameRecord],
    run_date: date,
) -> Report:
    lines: list[str] = [f"# Home Field Advantage Report ({run_date.isoformat()})", ""]

    if not league_metrics:
        lines.append("No non-neutral game data available today.")
        return Report(markdown="\n".join(lines) + "\n")

    charts: dict[str, str] = {}
    chart_dir_rel = f"charts/{run_date.isoformat()}"

    lines.extend(_render_league_table(league_metrics))
    lines.append("")

    league_chart = _league_trend_chart(games)
    if league_chart is not None:
        charts["league_trend.svg"] = league_chart
        lines.append(f"![League home win % trend]({chart_dir_rel}/league_trend.svg)")
        lines.append("")

    lines.extend(_render_top_teams_table(team_metrics))
    lines.append("")

    spotlight_teams = find_spotlight_teams(games)
    splits = compute_team_splits(games, spotlight_teams)
    if splits:
        lines.extend(_render_spotlight_section(splits))
        lines.append("")

        bar = _spotlight_bar_chart(splits)
        if bar is not None:
            charts["spotlight_hfa_lift.svg"] = bar
            lines.append(f"![Spotlight HFA lift]({chart_dir_rel}/spotlight_hfa_lift.svg)")
            lines.append("")

        trend = _spotlight_trend_chart(games, spotlight_teams)
        if trend is not None:
            charts["spotlight_trend.svg"] = trend
            lines.append(f"![Spotlight trend]({chart_dir_rel}/spotlight_trend.svg)")
            lines.append("")

    return Report(markdown="\n".join(lines) + "\n", charts=charts)


def write_report(report: Report | str, reports_dir: Path, run_date: date) -> Path:
    if isinstance(report, str):
        report = Report(markdown=report)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{run_date.isoformat()}.md"
    report_path.write_text(report.markdown, encoding="utf-8")

    if report.charts:
        chart_dir = reports_dir / "charts" / run_date.isoformat()
        chart_dir.mkdir(parents=True, exist_ok=True)
        for filename, svg in report.charts.items():
            (chart_dir / filename).write_text(svg, encoding="utf-8")

    return report_path


def build_markdown_report(
    league_metrics: dict[str, MetricSummary],
    team_metrics: dict[str, MetricSummary],
    run_date: date,
) -> str:
    """Markdown-only builder used by callers that don't pass game records."""
    return build_report(league_metrics, team_metrics, [], run_date).markdown
