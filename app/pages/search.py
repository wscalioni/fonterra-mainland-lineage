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
        html.Div("Lineage lookup", className="app-eyebrow"),
        html.H2("What touches this table?"),
        html.P(
            "Paste any catalog.schema.table to see its 2-hop neighbourhood "
            "and whether it's classified as a pinch-point.",
            className="app-page__subtitle",
        ),
        html.Div(
            dbc.InputGroup([
                dbc.Input(
                    id="s-node",
                    placeholder="fdp_prd_std_internal.std_internal_sapentbw.company_code_s4__zs4compco",
                ),
                dbc.Button("Search", id="s-go", color="primary"),
            ], className="app-search-bar"),
            style={"marginBottom": "32px"},
        ),
        html.Div(id="s-summary", style={"marginBottom": "16px"}),
        html.Div(
            cyto.Cytoscape(
                id="s-graph",
                elements=[],
                layout={"name": "dagre", "rankDir": "LR"},
                stylesheet=cytoscape_builder.CYTOSCAPE_STYLESHEET,
                style={"height": "62vh", "width": "100%"},
            ),
            className="app-graph-shell",
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
        return [], html.Div("Enter a fully-qualified node name.", className="app-error")
    try:
        c = obo_client()
        nbrs = data_loader.load_neighbourhood(
            c, warehouse_id=WAREHOUSE, working_schema=SCHEMA, node=node, hops=2,
        )
        if nbrs.empty:
            return [], html.Div(f"No edges found for {node} in the last 90 days.",
                                className="app-error")
        node_ids = set(nbrs["src_full_name"]) | set(nbrs["tgt_full_name"]) | {node}
        cls = data_loader.load_classified(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        cls = cls[cls["node"].isin(node_ids)]
    except RuntimeError as e:
        return [], html.Div(f"Error: {e}", className="app-error")
    elements = cytoscape_builder.build_elements(cls, nbrs)
    centre = cls[cls["node"] == node]
    if centre.empty:
        summary = html.Div(f"{node} not in classified set — showing neighbours only.")
    else:
        r = centre.iloc[0]
        summary = html.Div([
            html.Span(node, style={"fontWeight": "700"}),
            html.Span(" . ", style={"color": "var(--muted)", "margin": "0 6px"}),
            html.Span(r["category"]),
            html.Span(" . ", style={"color": "var(--muted)", "margin": "0 6px"}),
            html.Span(f"upstream {int(r['n_upstream'])} . downstream {int(r['n_downstream'])} . "
                      f"bridge {float(r.get('bridge_score') or 0):.2f}"),
        ])
    return elements, summary
