"""Search — what touches this table? Submit a node, get a 2-hop subgraph."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import Input, Output, State, callback, html

from lib import cytoscape_builder, data_loader
from lib.auth import obo_client

cyto.load_extra_layouts()
dash.register_page(__name__, path="/search", name="Search")

WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")


def layout():
    return html.Div([
        html.H2("What touches this table?", className="mt-3"),
        dbc.InputGroup([
            dbc.Input(id="s-node", placeholder="catalog.schema.table"),
            dbc.Button("Search", id="s-go", color="primary"),
        ], className="mb-3"),
        html.Div(id="s-summary"),
        cyto.Cytoscape(
            id="s-graph",
            elements=[],
            layout={"name": "dagre", "rankDir": "LR"},
            stylesheet=cytoscape_builder.CYTOSCAPE_STYLESHEET,
            style={"height": "70vh", "width": "100%"},
        ),
    ])


@callback(
    Output("s-graph", "elements"),
    Output("s-summary", "children"),
    Input("s-go", "n_clicks"),
    State("s-node", "value"),
    prevent_initial_call=True,
)
def _search(_n, node):
    if not node:
        return [], "Enter a fully-qualified node name."
    try:
        c = obo_client()
        nbrs = data_loader.load_neighbourhood(
            c, warehouse_id=WAREHOUSE, working_schema=SCHEMA, node=node, hops=2,
        )
        if nbrs.empty:
            return [], f"No edges found for {node} in the last 90 days."
        node_ids = set(nbrs["src_full_name"]) | set(nbrs["tgt_full_name"]) | {node}
        cls = data_loader.load_classified(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        cls = cls[cls["node"].isin(node_ids)]
    except RuntimeError as e:
        return [], f"Error: {e}"
    elements = cytoscape_builder.build_elements(cls, nbrs)
    centre = cls[cls["node"] == node]
    if centre.empty:
        summary = f"{node} not in classified set — showing neighbours only."
    else:
        r = centre.iloc[0]
        summary = (
            f"{node}: {r['category']}, "
            f"upstream={int(r['n_upstream'])}, downstream={int(r['n_downstream'])}, "
            f"bridge_score={float(r.get('bridge_score') or 0):.2f}"
        )
    return elements, summary
