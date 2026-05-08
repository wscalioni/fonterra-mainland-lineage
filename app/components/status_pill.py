"""Coloured pill for pinch-point separation status."""
from __future__ import annotations

from dash import html

STATUS_TO_CLASS = {
    "Pending":              "app-pill--pending",
    "UC Tagged":            "app-pill--uc-tagged",
    "Row Filter Applied":   "app-pill--row-filtered",
    "Attested":             "app-pill--attested",
    "Cleared":              "app-pill--cleared",
}


def status_pill(status: str) -> html.Span:
    suffix = STATUS_TO_CLASS.get(status, STATUS_TO_CLASS["Pending"])
    return html.Span(status, className=f"app-pill {suffix}")
