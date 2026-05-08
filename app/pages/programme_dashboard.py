"""Programme dashboard — homepage. KPI cards + schema heat map."""
from __future__ import annotations

import os
from datetime import date

import pandas as pd
from dash import Input, Output, callback, dcc, html
import dash

from lib import data_loader
from lib.auth import obo_client
from components.kpi_card import kpi_card

dash.register_page(__name__, path="/", name="Dashboard")

TSA_EXIT = date(2028, 4, 1)
WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")


def layout():
    return html.Div([
        html.Div("Programme overview", className="app-eyebrow"),
        html.H2("Mainland divestment data separation"),
        html.P(
            "Track the engineering scope of the Mainland carve-out across "
            "FDP — pinch-points, schemas at risk, and weekly progress.",
            className="app-page__subtitle",
        ),
        html.Div(id="dashboard-error"),
        html.Div(id="kpi-row", className="app-kpi-row"),

        html.Div([
            html.Div([html.H4("Schemas by entanglement risk")], className="app-section-h"),
            dcc.Loading(html.Div(id="schema-heat", className="app-heat")),
        ]),

        dcc.Interval(id="dash-load-once", n_intervals=0, max_intervals=1, interval=100),
    ])


@callback(
    Output("kpi-row", "children"),
    Output("schema-heat", "children"),
    Output("dashboard-error", "children"),
    Input("dash-load-once", "n_intervals"),
)
def _load(_n):
    if not WAREHOUSE:
        return [], [], html.Div("DATABRICKS_WAREHOUSE_ID not set.", className="app-error")
    try:
        client = obo_client()
        classified = data_loader.load_classified(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        status = data_loader.load_pinchpoint_status(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        refresh = data_loader.load_refresh_control(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
    except RuntimeError as e:
        return [], [], html.Div(f"Permission or query error: {e}", className="app-error")

    pinchpoints = classified[classified["category"].str.startswith("CO_MINGLED")]
    cleared = status[status["status"] == "Cleared"] if not status.empty else pd.DataFrame()
    schemas_with_pinch = pinchpoints["schema"].nunique()
    days_to_exit = (TSA_EXIT - date.today()).days
    last_refresh = refresh["run_completed"].iloc[0] if not refresh.empty else "never"

    cards = [
        kpi_card("Mainland-touching", f"{len(classified):,}", "objects in fdp_prd"),
        kpi_card("Pinch-points", f"{len(cleared)} / {len(pinchpoints)}", "cleared"),
        kpi_card("Active schemas", f"{schemas_with_pinch}", "with CO_MINGLED nodes"),
        kpi_card("TSA exit", "1 Apr 2028", f"{days_to_exit} days remaining"),
        kpi_card("Last refresh", str(last_refresh)[:16], "incremental"),
    ]

    schema_summary = (
        classified.groupby("schema")
        .agg(
            n=("node", "count"),
            n_pinch=("category", lambda s: s.isin(["CO_MINGLED_UPSTREAM", "CO_MINGLED_DOWNSTREAM"]).sum()),
            n_source=("category", lambda s: (s == "MAINLAND_SOURCE").sum()),
            n_sink=("category", lambda s: (s == "MAINLAND_SINK").sum()),
        )
        .reset_index()
        .sort_values(["n_pinch", "n"], ascending=[False, False])
    )

    def _tile_class(row):
        if row["n_pinch"] > 0:
            return "app-heat__tile app-heat__tile--danger"
        if row["n_source"] + row["n_sink"] > 0:
            return "app-heat__tile app-heat__tile--warning"
        return "app-heat__tile app-heat__tile--ok"

    tiles = [
        html.Div(
            f"{r['schema']} ({r['n']})",
            title=f"{r['n_pinch']} pinch / {r['n_source']} source / {r['n_sink']} sink",
            className=_tile_class(r),
        )
        for _, r in schema_summary.iterrows()
    ]
    return cards, tiles, ""
