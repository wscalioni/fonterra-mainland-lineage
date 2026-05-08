"""Programme dashboard — homepage. KPI cards + schema heat map."""
from __future__ import annotations

import os
from datetime import date

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, html

from lib import data_loader
from lib.auth import obo_client

dash.register_page(__name__, path="/", name="Dashboard")

TSA_EXIT = date(2028, 4, 1)
WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")


def _kpi_card(title, value, sub=""):
    return dbc.Card(
        dbc.CardBody([
            html.Div(title, className="text-muted small"),
            html.Div(value, className="display-6"),
            html.Div(sub, className="small"),
        ]),
        className="mb-2",
    )


def layout():
    return html.Div([
        html.H2("Mainland divestment — programme dashboard", className="mt-3"),
        html.Div(id="dashboard-error", className="text-danger"),
        dbc.Row(id="kpi-row", className="g-2 mt-2"),
        html.H4("Schemas by entanglement risk", className="mt-4"),
        dcc.Loading(html.Div(id="schema-heat")),
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
        return [], [], "DATABRICKS_WAREHOUSE_ID not set."
    try:
        client = obo_client()
        classified = data_loader.load_classified(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        status = data_loader.load_pinchpoint_status(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        refresh = data_loader.load_refresh_control(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
    except RuntimeError as e:
        return [], [], f"Permission or query error: {e}"

    pinchpoints = classified[classified["category"].str.startswith("CO_MINGLED")]
    cleared = status[status["status"] == "Cleared"] if not status.empty else pd.DataFrame()
    schemas_with_pinch = pinchpoints["schema"].nunique()
    days_to_exit = (TSA_EXIT - date.today()).days
    last_refresh = refresh["run_completed"].iloc[0] if not refresh.empty else "never"

    cards = [
        dbc.Col(_kpi_card("Mainland-touching objects", f"{len(classified):,}", "")),
        dbc.Col(_kpi_card("Pinch-points", f"{len(cleared)} / {len(pinchpoints)}", "cleared")),
        dbc.Col(_kpi_card("Active schemas", f"{schemas_with_pinch}", "with CO_MINGLED nodes")),
        dbc.Col(_kpi_card("TSA exit", "2028-04-01", f"{days_to_exit} days remaining")),
        dbc.Col(_kpi_card("Last refresh", str(last_refresh), "")),
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

    def _colour(row):
        if row["n_pinch"] > 0:
            return "#D32F2F"
        if row["n_source"] + row["n_sink"] > 0:
            return "#FFA000"
        return "#4CAF50"

    tiles = [
        html.Div(
            f"{r['schema']} ({r['n']})",
            title=f"{r['n_pinch']} pinch / {r['n_source']} source / {r['n_sink']} sink",
            style={
                "background": _colour(r),
                "color": "white",
                "padding": "6px 8px",
                "borderRadius": "4px",
                "fontSize": "0.85em",
                "display": "inline-block",
                "margin": "2px",
            },
        )
        for _, r in schema_summary.iterrows()
    ]
    return cards, html.Div(tiles), ""
