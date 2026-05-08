"""Pinch-point tracker — 49 CO_MINGLED nodes with status write-back."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dash_table, dcc, html

from lib import data_loader, status_writer
from lib.auth import obo_client, user_email

dash.register_page(__name__, path="/pinchpoints", name="Pinch-points")

WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")
STATUS_OPTIONS = ["Pending", "UC Tagged", "Row Filter Applied", "Attested", "Cleared"]


def layout():
    return html.Div([
        html.H2("Pinch-point tracker", className="mt-3"),
        html.P("49 CO_MINGLED nodes — set separation status to track progress."),
        html.Div(id="pp-progress", className="mb-3"),
        html.Div(id="pp-error", className="text-danger"),
        dash_table.DataTable(
            id="pp-table",
            columns=[
                {"name": "Node", "id": "node"},
                {"name": "Category", "id": "category"},
                {"name": "Schema", "id": "schema"},
                {"name": "Up/Dn", "id": "ud"},
                {"name": "Status", "id": "status", "presentation": "dropdown", "editable": True},
                {"name": "Notes", "id": "notes", "editable": True},
            ],
            dropdown={"status": {"options": [{"label": s, "value": s} for s in STATUS_OPTIONS]}},
            data=[],
            style_cell={"fontSize": "0.85em", "fontFamily": "system-ui"},
            style_data_conditional=[
                {"if": {"filter_query": "{status} = 'Cleared'"}, "backgroundColor": "#E8F5E9"},
                {"if": {"filter_query": "{category} = 'CO_MINGLED_DOWNSTREAM'"},
                 "borderLeft": "4px solid #D32F2F"},
                {"if": {"filter_query": "{category} = 'CO_MINGLED_UPSTREAM'"},
                 "borderLeft": "4px solid #E65100"},
            ],
        ),
        dcc.Store(id="pp-user", data={"email": "unknown@databricks.com"}),
        dcc.Interval(id="pp-load-once", n_intervals=0, max_intervals=1, interval=100),
    ])


def _build_rows(classified, status):
    pp = classified[classified["category"].str.startswith("CO_MINGLED")].copy()
    pp = pp.merge(status[["node", "status", "notes"]], on="node", how="left") if not status.empty else pp.assign(status=None, notes=None)
    pp["status"] = pp["status"].fillna("Pending")
    pp["notes"] = pp["notes"].fillna("")
    pp["ud"] = pp["n_upstream"].astype(str) + " / " + pp["n_downstream"].astype(str)
    return pp[["node", "category", "schema", "ud", "status", "notes"]].to_dict("records")


@callback(
    Output("pp-table", "data"),
    Output("pp-progress", "children"),
    Output("pp-error", "children"),
    Input("pp-load-once", "n_intervals"),
)
def _initial(_n):
    if not WAREHOUSE:
        return [], "", "DATABRICKS_WAREHOUSE_ID not set."
    try:
        c = obo_client()
        cls = data_loader.load_classified(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        st = data_loader.load_pinchpoint_status(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
    except RuntimeError as e:
        return [], "", str(e)
    rows = _build_rows(cls, st)
    cleared = sum(1 for r in rows if r["status"] == "Cleared")
    bar = dbc.Progress(value=100 * cleared / max(1, len(rows)),
                       label=f"{cleared} / {len(rows)} cleared",
                       style={"height": "24px"})
    return rows, bar, ""


@callback(
    Output("pp-error", "children", allow_duplicate=True),
    Input("pp-table", "data_timestamp"),
    State("pp-table", "data"),
    State("pp-table", "data_previous"),
    State("pp-user", "data"),
    prevent_initial_call=True,
)
def _persist(_ts, data, prev, user):
    if not data or not prev:
        return ""
    by_id = {r["node"]: r for r in prev}
    diffs = [r for r in data if by_id.get(r["node"]) != r]
    if not diffs:
        return ""
    try:
        c = obo_client()
        for r in diffs:
            status_writer.set_pinchpoint_status(
                c, warehouse_id=WAREHOUSE, working_schema=SCHEMA,
                node=r["node"], status=r["status"], notes=r["notes"] or "",
                updated_by=user_email(),
            )
    except (RuntimeError, ValueError) as e:
        return f"Save failed: {e}"
    return ""
