"""Dash entry point for the Mainland Lineage app.

The Databricks Apps runtime calls ``python app.py``. Locally, set
DATABRICKS_CONFIG_PROFILE and DATABRICKS_WAREHOUSE_ID in the env then
run ``python app/app.py`` from the repo root.
"""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
from dash import html

from components.header import branded_header

GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Assistant:wght@400;700"
    "&family=Courgette&display=swap"
)

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP, GOOGLE_FONTS],
    suppress_callback_exceptions=True,
    title="Mainland Lineage — Fonterra",
    update_title=None,
)

app.layout = html.Div([
    branded_header(),
    html.Div(dash.page_container, className="app-page"),
])

if __name__ == "__main__":
    port = int(os.environ.get("DATABRICKS_APP_PORT", "8050"))
    app.run(host="0.0.0.0", port=port, debug=False)
