"""Weekly digest — what changed in the last 7 days."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from lib import data_loader
from lib.auth import obo_client

dash.register_page(__name__, path="/digest", name="Weekly digest")

WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")

NEW_NODES_QUERY = """
SELECT n.full_name, c.category
FROM {schema}.mainland_lineage_nodes n
LEFT JOIN {schema}.mainland_lineage_classified c ON c.node = n.full_name
WHERE n.first_seen_dir = 'incremental'
LIMIT 200
"""

NEW_PINCH_QUERY = """
SELECT c.node, c.category
FROM {schema}.mainland_lineage_classified c
JOIN {schema}.mainland_lineage_nodes n ON n.full_name = c.node
WHERE c.category IN ('CO_MINGLED_UPSTREAM', 'CO_MINGLED_DOWNSTREAM')
  AND n.first_seen_dir = 'incremental'
LIMIT 100
"""

CLEARED_QUERY = """
SELECT node, status, updated_at, updated_by
FROM {schema}.pinchpoint_status
WHERE status = 'Cleared'
  AND updated_at > current_timestamp() - INTERVAL 7 DAYS
ORDER BY updated_at DESC
"""


def layout():
    return html.Div([
        html.H2("Weekly digest", className="mt-3"),
        dbc.Row([
            dbc.Col([html.H5("New nodes (incremental)"), html.Div(id="d-new-nodes")]),
            dbc.Col([html.H5("Newly CO_MINGLED"), html.Div(id="d-new-pinch")]),
            dbc.Col([html.H5("Cleared this week"), html.Div(id="d-cleared")]),
        ]),
        html.Div(id="d-error", className="text-danger"),
        dcc.Interval(id="d-load-once", n_intervals=0, max_intervals=1, interval=100),
    ])


def _table(df, columns):
    if df.empty:
        return html.Em("none")
    return dbc.Table.from_dataframe(df[columns], striped=True, size="sm")


@callback(
    Output("d-new-nodes", "children"),
    Output("d-new-pinch", "children"),
    Output("d-cleared", "children"),
    Output("d-error", "children"),
    Input("d-load-once", "n_intervals"),
)
def _load(_n):
    if not WAREHOUSE:
        return "", "", "", "DATABRICKS_WAREHOUSE_ID not set."
    try:
        c = obo_client()
        new_nodes = data_loader._execute(c, warehouse_id=WAREHOUSE,
                                          statement=NEW_NODES_QUERY.format(schema=SCHEMA))
        new_pinch = data_loader._execute(c, warehouse_id=WAREHOUSE,
                                          statement=NEW_PINCH_QUERY.format(schema=SCHEMA))
        cleared = data_loader._execute(c, warehouse_id=WAREHOUSE,
                                        statement=CLEARED_QUERY.format(schema=SCHEMA))
    except RuntimeError as e:
        return "", "", "", f"Error: {e}"
    return (
        _table(new_nodes, ["full_name", "category"]),
        _table(new_pinch, ["node", "category"]),
        _table(cleared, ["node", "updated_at", "updated_by"]),
        "",
    )
