from __future__ import annotations

from datetime import date
from pathlib import Path

from home_field_advantage.analyze.metrics import MetricSummary


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def build_markdown_report(
    league_metrics: dict[str, MetricSummary],
    team_metrics: dict[str, MetricSummary],
    run_date: date,
) -> str:
    lines: list[str] = []
    lines.append(f"# Home Field Advantage Report ({run_date.isoformat()})")
    lines.append("")

    if not league_metrics:
        lines.append("No non-neutral game data available today.")
        return "\n".join(lines) + "\n"

    lines.append("## League Summary")
    lines.append("")
    lines.append("| League | Games | Home Win % | Avg Home Margin |")
    lines.append("|---|---:|---:|---:|")
    for league in sorted(league_metrics):
        metric = league_metrics[league]
        lines.append(
            f"| {league} | {metric.games} | {_fmt_pct(metric.home_win_pct)} | {metric.avg_home_margin:.2f} |"
        )

    lines.append("")
    lines.append("## Team Summary (Top 15 by Home Win %)")
    lines.append("")
    lines.append("| Team | Home Games | Home Win % | Avg Home Margin |")
    lines.append("|---|---:|---:|---:|")

    ranked = sorted(team_metrics.items(), key=lambda item: (item[1].home_win_pct, item[1].games), reverse=True)
    for team, metric in ranked[:15]:
        lines.append(
            f"| {team} | {metric.games} | {_fmt_pct(metric.home_win_pct)} | {metric.avg_home_margin:.2f} |"
        )

    return "\n".join(lines) + "\n"


def write_report(markdown: str, reports_dir: Path, run_date: date) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{run_date.isoformat()}.md"
    report_path.write_text(markdown, encoding="utf-8")
    return report_path
