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
        html.Div("Engineering backlog", className="app-eyebrow"),
        html.H2("Pinch-point tracker"),
        html.P(
            "49 CO_MINGLED nodes that bridge Mainland and retained data. "
            "Edit the Status column to record progress.",
            className="app-page__subtitle",
        ),
        html.Div(id="pp-progress"),
        html.Div(id="pp-error"),
        html.Div([
            dash_table.DataTable(
                id="pp-table",
                columns=[
                    {"name": "Node", "id": "node"},
                    {"name": "Category", "id": "category"},
                    {"name": "Schema", "id": "schema"},
                    {"name": "Up / Dn", "id": "ud"},
                    {"name": "Status", "id": "status", "presentation": "dropdown", "editable": True},
                    {"name": "Notes", "id": "notes", "editable": True},
                ],
                dropdown={"status": {"options": [{"label": s, "value": s} for s in STATUS_OPTIONS]}},
                data=[],
                style_cell={
                    "fontFamily": "Assistant, system-ui, sans-serif",
                    "fontSize": "13px",
                    "padding": "10px 8px",
                    "border": "0",
                    "borderBottom": "1px solid var(--rule)",
                    "textAlign": "left",
                },
                style_header={
                    "fontWeight": "700",
                    "textTransform": "uppercase",
                    "letterSpacing": "0.06em",
                    "fontSize": "11px",
                    "color": "var(--ink)",
                    "borderBottom": "2px solid var(--ink)",
                    "background": "var(--canvas)",
                },
                style_data_conditional=[
                    {"if": {"filter_query": "{status} = 'Cleared'"}, "backgroundColor": "#F0FDF4"},
                    {"if": {"filter_query": "{category} = 'CO_MINGLED_DOWNSTREAM'", "column_id": "category"},
                     "color": "var(--danger)", "fontWeight": "700"},
                    {"if": {"filter_query": "{category} = 'CO_MINGLED_UPSTREAM'", "column_id": "category"},
                     "color": "var(--warning)", "fontWeight": "700"},
                ],
                style_as_list_view=True,
                page_size=50,
            ),
        ]),
        dcc.Store(id="pp-user", data={"email": "unknown@databricks.com"}),
        dcc.Interval(id="pp-load-once", n_intervals=0, max_intervals=1, interval=100),
    ])


def _build_rows(classified, status):
    pp = classified[classified["category"].str.startswith("CO_MINGLED")].copy()
    pp = (
        pp.merge(status[["node", "status", "notes"]], on="node", how="left")
        if not status.empty
        else pp.assign(status=None, notes=None)
    )
    pp["status"] = pp["status"].fillna("Pending")
    pp["notes"] = pp["notes"].fillna("")
    pp["ud"] = pp["n_upstream"].astype(str) + " / " + pp["n_downstream"].astype(str)
    return pp[["node", "category", "schema", "ud", "status", "notes"]].to_dict("records")


def _progress_banner(cleared: int, total: int) -> html.Div:
    pct = round(100 * cleared / max(1, total))
    return html.Div(
        [
            html.Div(
                [
                    html.Div("Progress", className="app-kpi-card__label"),
                    html.Div(f"{cleared} / {total}", className="app-kpi-card__value"),
                    html.Div(f"{pct}% cleared", className="app-kpi-card__sub"),
                ],
                style={
                    "background": "var(--surface)",
                    "border": "1px solid var(--rule)",
                    "padding": "20px 22px",
                    "minWidth": "200px",
                },
            ),
            html.Div(
                style={
                    "flex": "1",
                    "background": "var(--rule)",
                    "height": "8px",
                    "alignSelf": "center",
                    "marginLeft": "24px",
                    "position": "relative",
                    "overflow": "hidden",
                },
                children=html.Div(
                    style={
                        "background": "var(--fonterra-green)",
                        "width": f"{pct}%",
                        "height": "100%",
                    }
                ),
            ),
        ],
        style={"display": "flex", "alignItems": "stretch", "marginBottom": "32px"},
    )


@callback(
    Output("pp-table", "data"),
    Output("pp-progress", "children"),
    Output("pp-error", "children"),
    Input("pp-load-once", "n_intervals"),
)
def _initial(_n):
    if not WAREHOUSE:
        return [], "", html.Div("DATABRICKS_WAREHOUSE_ID not set.", className="app-error")
    try:
        c = obo_client()
        cls = data_loader.load_classified(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        st = data_loader.load_pinchpoint_status(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
    except RuntimeError as e:
        return [], "", html.Div(str(e), className="app-error")
    rows = _build_rows(cls, st)
    cleared = sum(1 for r in rows if r["status"] == "Cleared")
    return rows, _progress_banner(cleared, len(rows)), ""


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
        return html.Div(f"Save failed: {e}", className="app-error")
    return ""
