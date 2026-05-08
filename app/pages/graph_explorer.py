"""Graph explorer — full UC lineage spider-web with filters + focus mode."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import Input, Output, callback, dcc, html

from lib import cytoscape_builder, data_loader
from lib.auth import obo_client

cyto.load_extra_layouts()
dash.register_page(__name__, path="/graph", name="Graph")

WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")

CATEGORIES = [
    "MAINLAND_TAGGED", "MAINLAND_INTERIOR", "MAINLAND_SOURCE", "MAINLAND_SINK",
    "CO_MINGLED_UPSTREAM", "CO_MINGLED_DOWNSTREAM",
    "RETAINED_OR_INDIRECT", "UNCLASSIFIED",
]


def layout():
    return html.Div([
        html.Div("Lineage explorer", className="app-eyebrow"),
        html.H2("UC lineage spider-web"),
        html.P(
            "Walked from system.access.table_lineage. Click a node for "
            "category and degree. CO_MINGLED nodes are the engineering scope.",
            className="app-page__subtitle",
        ),
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5("Categories"),
                    dbc.Checklist(
                        id="g-cat",
                        options=[{"label": c, "value": c} for c in CATEGORIES],
                        value=["CO_MINGLED_UPSTREAM", "CO_MINGLED_DOWNSTREAM"],
                        inline=False,
                    ),
                    html.H5("View", style={"marginTop": "24px"}),
                    dbc.Switch(id="g-pinch-only", label="Pinch-points + 1-hop only", value=True),
                    dbc.Switch(id="g-hide-edges", label="Hide edges (faster)", value=False),
                    html.Div(style={"borderTop": "1px solid var(--rule)", "marginTop": "20px", "paddingTop": "20px"},
                             children=html.Div(id="g-info", className="app-kpi-card__sub")),
                ], className="app-sidebar"),
            ], width=3),
            dbc.Col([
                html.Div(
                    cyto.Cytoscape(
                        id="g-graph",
                        elements=[],
                        layout={"name": "dagre", "rankDir": "LR"},
                        stylesheet=cytoscape_builder.CYTOSCAPE_STYLESHEET,
                        style={"height": "78vh", "width": "100%"},
                    ),
                    className="app-graph-shell",
                ),
                dcc.Interval(id="g-load-once", n_intervals=0, max_intervals=1, interval=100),
            ], width=9),
        ]),
    ])


@callback(
    Output("g-graph", "elements"),
    Output("g-info", "children"),
    Input("g-cat", "value"),
    Input("g-pinch-only", "value"),
    Input("g-hide-edges", "value"),
    Input("g-load-once", "n_intervals"),
)
def _render(cats, pinch_only, hide_edges, _n):
    if not WAREHOUSE:
        return [], "DATABRICKS_WAREHOUSE_ID not set."
    try:
        c = obo_client()
        cls = data_loader.load_classified(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        edges = data_loader.load_edges(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
    except RuntimeError as e:
        return [], f"Error: {e}"
    cls = cls[cls["category"].isin(cats)]
    elements = cytoscape_builder.build_elements(
        cls, edges, pinch_neighbourhood_only=pinch_only, hide_edges=hide_edges,
    )
    n_nodes = sum(1 for e in elements if "source" not in e["data"])
    n_edges = sum(1 for e in elements if "source" in e["data"])
    return elements, f"{n_nodes} nodes / {n_edges} edges rendered"


@callback(
    Output("g-info", "children", allow_duplicate=True),
    Input("g-graph", "tapNodeData"),
    prevent_initial_call=True,
)
def _node_info(data):
    if not data:
        return dash.no_update
    return html.Div([
        html.Div(html.Strong(data["id"]), style={"wordBreak": "break-all"}),
        html.Div(data["category"], style={"marginTop": "8px", "fontWeight": "700"}),
        html.Div(
            f"upstream {data['n_upstream']} . downstream {data['n_downstream']} . "
            f"bridge {data['bridge_score']:.2f}",
            style={"marginTop": "4px"},
        ),
    ])
