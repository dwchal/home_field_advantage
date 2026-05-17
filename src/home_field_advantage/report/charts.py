from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


PALETTE = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#17becf",
)


@dataclass(frozen=True)
class LineSeries:
    label: str
    points: tuple[tuple[float, float], ...]


def date_to_ordinal(d: str) -> int:
    return datetime.strptime(d, "%Y-%m-%d").date().toordinal()


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def line_chart_svg(
    series_list: list[LineSeries],
    title: str,
    *,
    y_format: str = "{:.0%}",
    y_min: float | None = None,
    y_max: float | None = None,
    width: int = 760,
    height: int = 360,
) -> str:
    margin_left = 60
    margin_right = 200
    margin_top = 40
    margin_bottom = 50
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    flat_x = [x for s in series_list for x, _ in s.points]
    flat_y = [y for s in series_list for _, y in s.points]
    if not flat_x:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}"></svg>'
        )

    x_min, x_max = min(flat_x), max(flat_x)
    y_low = y_min if y_min is not None else min(flat_y)
    y_high = y_max if y_max is not None else max(flat_y)
    if y_high == y_low:
        y_high = y_low + 1
    if x_max == x_min:
        x_max = x_min + 1

    def sx(x: float) -> float:
        return margin_left + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y: float) -> float:
        return margin_top + plot_h - (y - y_low) / (y_high - y_low) * plot_h

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="system-ui, -apple-system, sans-serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{width / 2:.1f}" y="22" text-anchor="middle" '
        f'font-size="16" font-weight="600">{_escape(title)}</text>',
    ]

    for i in range(5):
        y_val = y_low + (y_high - y_low) * i / 4
        y_px = sy(y_val)
        parts.append(
            f'<line x1="{margin_left}" y1="{y_px:.1f}" '
            f'x2="{margin_left + plot_w}" y2="{y_px:.1f}" stroke="#eee"/>'
        )
        parts.append(
            f'<text x="{margin_left - 6}" y="{y_px + 4:.1f}" '
            f'text-anchor="end" fill="#666">{y_format.format(y_val)}</text>'
        )

    n_ticks = 5
    for i in range(n_ticks):
        x_val = x_min + (x_max - x_min) * i / (n_ticks - 1)
        x_px = sx(x_val)
        d = date.fromordinal(int(round(x_val))).isoformat()
        parts.append(
            f'<line x1="{x_px:.1f}" y1="{margin_top + plot_h}" '
            f'x2="{x_px:.1f}" y2="{margin_top + plot_h + 4}" stroke="#999"/>'
        )
        parts.append(
            f'<text x="{x_px:.1f}" y="{margin_top + plot_h + 18}" '
            f'text-anchor="middle" fill="#666">{d}</text>'
        )

    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top}" '
        f'x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#444"/>'
    )
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" '
        f'x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#444"/>'
    )

    if y_low <= 0.5 <= y_high:
        ref = sy(0.5)
        parts.append(
            f'<line x1="{margin_left}" y1="{ref:.1f}" '
            f'x2="{margin_left + plot_w}" y2="{ref:.1f}" '
            f'stroke="#bbb" stroke-dasharray="4,4"/>'
        )

    for i, s in enumerate(series_list):
        color = PALETTE[i % len(PALETTE)]
        pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in s.points)
        parts.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{pts}"/>'
        )

    legend_x = margin_left + plot_w + 16
    for i, s in enumerate(series_list):
        color = PALETTE[i % len(PALETTE)]
        y_pos = margin_top + i * 20
        parts.append(
            f'<rect x="{legend_x}" y="{y_pos - 9}" width="12" height="12" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{legend_x + 18}" y="{y_pos + 1}" fill="#333">{_escape(s.label)}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def bar_chart_svg(
    items: list[tuple[str, float]],
    title: str,
    *,
    value_format: str = "{:+.1%}",
    width: int = 760,
    height: int = 360,
    zero_centered: bool = False,
) -> str:
    margin_left = 200
    margin_right = 60
    margin_top = 40
    margin_bottom = 30
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    if not items:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}"></svg>'
        )

    values = [v for _, v in items]
    if zero_centered:
        bound = max(abs(min(values)), abs(max(values)), 0.01)
        v_min, v_max = -bound, bound
    else:
        v_min, v_max = min(0.0, min(values)), max(0.0, max(values))
        if v_max == v_min:
            v_max = v_min + 1

    def sx(v: float) -> float:
        return margin_left + (v - v_min) / (v_max - v_min) * plot_w

    zero_x = sx(0.0)
    spacing = plot_h / len(items)
    bar_h = spacing * 0.7

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="system-ui, -apple-system, sans-serif" font-size="12">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{width / 2:.1f}" y="22" text-anchor="middle" '
        f'font-size="16" font-weight="600">{_escape(title)}</text>',
    ]

    for i, (label, value) in enumerate(items):
        y = margin_top + i * spacing + (spacing - bar_h) / 2
        end_x = sx(value)
        bar_x = min(zero_x, end_x)
        bar_w = abs(end_x - zero_x)
        color = PALETTE[i % len(PALETTE)] if not zero_centered else (
            "#2ca02c" if value >= 0 else "#d62728"
        )
        parts.append(
            f'<rect x="{bar_x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{bar_h:.1f}" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{margin_left - 8}" y="{y + bar_h / 2 + 4:.1f}" '
            f'text-anchor="end" fill="#333">{_escape(label)}</text>'
        )
        text_x = end_x + (4 if value >= 0 else -4)
        anchor = "start" if value >= 0 else "end"
        parts.append(
            f'<text x="{text_x:.1f}" y="{y + bar_h / 2 + 4:.1f}" '
            f'text-anchor="{anchor}" fill="#333">{value_format.format(value)}</text>'
        )

    parts.append(
        f'<line x1="{zero_x:.1f}" y1="{margin_top}" '
        f'x2="{zero_x:.1f}" y2="{margin_top + plot_h}" stroke="#444"/>'
    )

    parts.append("</svg>")
    return "\n".join(parts)
