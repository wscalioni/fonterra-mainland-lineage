"""Transforms classified-nodes + edges DataFrames into cytoscape elements."""
from __future__ import annotations

import pandas as pd

from lib.colours import CATEGORY_COLOUR

PINCH_CATEGORIES = {"CO_MINGLED_UPSTREAM", "CO_MINGLED_DOWNSTREAM"}


def _node_size(n_up: int, n_dn: int) -> float:
    return max(8.0, min(40.0, 8.0 + 2.0 * (n_up + n_dn) ** 0.6))


def build_elements(classified, edges, *, pinch_neighbourhood_only=False, hide_edges=False):
    nodes_df = classified.copy()
    edges_df = edges.copy()

    if pinch_neighbourhood_only:
        pinches = set(nodes_df.loc[nodes_df["category"].isin(PINCH_CATEGORIES), "node"])
        keep_edges = edges_df[
            edges_df["src_full_name"].isin(pinches)
            | edges_df["tgt_full_name"].isin(pinches)
        ]
        keep_nodes = pinches | set(keep_edges["src_full_name"]) | set(keep_edges["tgt_full_name"])
        nodes_df = nodes_df[nodes_df["node"].isin(keep_nodes)]
        edges_df = keep_edges

    elements = []
    for _, r in nodes_df.iterrows():
        cat = r["category"]
        elements.append({
            "data": {
                "id": r["node"],
                "label": r["table_name"],
                "category": cat,
                "schema": r["schema"],
                "catalog": r["catalog"],
                "n_upstream": int(r["n_upstream"]),
                "n_downstream": int(r["n_downstream"]),
                "bridge_score": float(r.get("bridge_score") or 0.0),
                "colour": CATEGORY_COLOUR.get(cat, "#BDBDBD"),
                "size": _node_size(int(r["n_upstream"]), int(r["n_downstream"])),
            },
            "classes": "pinch" if cat in PINCH_CATEGORIES else "",
        })

    if not hide_edges:
        for _, e in edges_df.iterrows():
            elements.append({
                "data": {
                    "source": e["src_full_name"],
                    "target": e["tgt_full_name"],
                    "weight": int(e["edge_count"]),
                },
            })
    return elements


CYTOSCAPE_STYLESHEET = [
    {"selector": "node", "style": {
        "background-color": "data(colour)",
        "label": "data(label)",
        "width": "data(size)",
        "height": "data(size)",
        "font-size": "8px",
        "color": "#222",
        "text-valign": "bottom",
        "text-halign": "center",
    }},
    {"selector": "edge", "style": {
        "width": "mapData(weight, 1, 1000, 1, 6)",
        "line-color": "#bbb",
        "target-arrow-color": "#bbb",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        "opacity": 0.6,
    }},
    {"selector": ".pinch", "style": {
        "border-width": 3,
        "border-color": "#000",
        "border-style": "solid",
    }},
]
