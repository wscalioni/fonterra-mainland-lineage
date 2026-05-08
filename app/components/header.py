"""Fonterra-branded header for the Mainland Lineage app."""
from __future__ import annotations

from dash import html

NAV_PAGES = [
    ("/",            "Dashboard"),
    ("/pinchpoints", "Pinch-points"),
    ("/graph",       "Graph"),
    ("/search",      "Search"),
    ("/workspaces",  "Workspaces"),
    ("/digest",      "Weekly digest"),
]


def branded_header(active_path: str = "/") -> html.Div:
    """Return the page-spanning Fonterra header.

    ``active_path`` matches a NAV_PAGES href; the matching link gets the
    ``is-active`` class. Defaults to "/" so the dashboard is highlighted
    at app boot before client-side routing kicks in.
    """
    nav_links = [
        html.A(
            label,
            href=path,
            className="is-active" if path == active_path else "",
        )
        for path, label in NAV_PAGES
    ]
    return html.Div(
        [
            html.Img(
                src="/assets/fonterra-logo.png",
                alt="Fonterra",
                className="app-header__logo",
            ),
            html.Div(
                [
                    html.Div("Mainland Lineage", className="app-header__brand-line"),
                    html.Div(
                        "data separation programme",
                        className="app-header__brand-sub",
                    ),
                ],
                className="app-header__brand",
            ),
            html.Nav(nav_links, className="app-header__nav"),
        ],
        className="app-header",
    )
