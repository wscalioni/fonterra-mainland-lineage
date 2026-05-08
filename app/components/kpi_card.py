"""Editorial KPI card — eyebrow label, large value, optional sub."""
from __future__ import annotations

from dash import html


def kpi_card(label: str, value: str, sub: str | None = None) -> html.Div:
    """Single KPI tile.

    ``label`` renders as a tiny uppercase eyebrow; ``value`` is the large
    headline; ``sub`` is the muted detail line and is omitted entirely if
    None or empty.
    """
    children = [
        html.Div(label, className="app-kpi-card__label"),
        html.Div(value, className="app-kpi-card__value"),
    ]
    if sub:
        children.append(html.Div(sub, className="app-kpi-card__sub"))
    return html.Div(children, className="app-kpi-card")
