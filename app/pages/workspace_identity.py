"""Workspace identity panel — annotate the 10 workspace IDs from Phase 0."""
from __future__ import annotations

import os

import dash
from dash import Input, Output, State, callback, dash_table, dcc, html
from databricks.sdk import WorkspaceClient

from lib import data_loader, status_writer

dash.register_page(__name__, path="/workspaces", name="Workspaces")

WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")

EVENTS_QUERY = """
SELECT workspace_id, count(*) AS event_count
FROM system.access.table_lineage
WHERE event_time > current_timestamp() - INTERVAL 30 DAYS
GROUP BY workspace_id
ORDER BY event_count DESC
"""


def layout():
    return html.Div([
        html.H2("Workspace identities", className="mt-3"),
        html.P("Annotate workspace IDs that appear in lineage events."),
        html.Div(id="ws-error", className="text-danger"),
        dash_table.DataTable(
            id="ws-table",
            columns=[
                {"name": "Workspace ID", "id": "workspace_id"},
                {"name": "Events (30d)", "id": "event_count"},
                {"name": "Display name", "id": "display_name", "editable": True},
                {"name": "Notes", "id": "notes", "editable": True},
            ],
            data=[],
            style_cell={"fontSize": "0.85em", "fontFamily": "system-ui"},
        ),
        dcc.Store(id="ws-user", data={"email": "unknown@databricks.com"}),
        dcc.Interval(id="ws-load-once", n_intervals=0, max_intervals=1, interval=100),
    ])


@callback(
    Output("ws-table", "data"),
    Output("ws-error", "children"),
    Input("ws-load-once", "n_intervals"),
)
def _initial(_n):
    if not WAREHOUSE:
        return [], "DATABRICKS_WAREHOUSE_ID not set."
    try:
        c = WorkspaceClient()
        events = data_loader._execute(c, warehouse_id=WAREHOUSE, statement=EVENTS_QUERY)
        identities = data_loader.load_workspace_identities(
            c, warehouse_id=WAREHOUSE, working_schema=SCHEMA,
        )
    except RuntimeError as e:
        return [], str(e)
    if identities.empty:
        events["display_name"] = ""
        events["notes"] = ""
        return events[["workspace_id", "event_count", "display_name", "notes"]].to_dict("records"), ""
    merged = events.merge(identities, on="workspace_id", how="left")
    merged["display_name"] = merged["display_name"].fillna("")
    merged["notes"] = merged["notes"].fillna("")
    return merged[["workspace_id", "event_count", "display_name", "notes"]].to_dict("records"), ""


@callback(
    Output("ws-error", "children", allow_duplicate=True),
    Input("ws-table", "data_timestamp"),
    State("ws-table", "data"),
    State("ws-table", "data_previous"),
    State("ws-user", "data"),
    prevent_initial_call=True,
)
def _persist(_ts, data, prev, user):
    if not data or not prev:
        return ""
    by_id = {r["workspace_id"]: r for r in prev}
    diffs = [r for r in data if by_id.get(r["workspace_id"]) != r]
    if not diffs:
        return ""
    try:
        c = WorkspaceClient()
        for r in diffs:
            status_writer.set_workspace_identity(
                c, warehouse_id=WAREHOUSE, working_schema=SCHEMA,
                workspace_id=r["workspace_id"],
                display_name=r["display_name"] or "",
                notes=r["notes"] or "",
                updated_by=user.get("email", "unknown"),
            )
    except RuntimeError as e:
        return f"Save failed: {e}"
    return ""
