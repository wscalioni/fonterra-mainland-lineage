"""Phase 5 — Visualization.

Reads outputs/classified_nodes.csv and outputs/edges.csv, builds a networkx
DiGraph, and emits:

  outputs/lineage_full.html              pyvis interactive (whole graph)
  outputs/lineage_pinchpoints.dot        Graphviz subgraph (49 pinch-points + 1-hop)
  outputs/lineage_pinchpoints.png        rendered via `dot -Tpng`
  outputs/lineage_pinchpoints.svg        rendered via `dot -Tsvg`
  outputs/lineage_layer_flow.dot         high-level FDP-layer flow summary
  outputs/lineage_layer_flow.png

Run with the venv:  .venv/bin/python -m lib.visualize
"""
from __future__ import annotations

import csv
import pathlib
import subprocess

import networkx as nx
from pyvis.network import Network


REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "outputs"


# ---------------------------------------------------------------------------
# Colour scheme — keep stable so Confluence/PNG/HTML look identical.
CATEGORY_COLOUR = {
    "MAINLAND_TAGGED":         "#4CAF50",  # green
    "MAINLAND_INTERIOR":       "#2E7D32",  # dark green
    "MAINLAND_SOURCE":         "#1976D2",  # blue
    "MAINLAND_SINK":           "#0288D1",  # cyan-blue
    "CO_MINGLED_UPSTREAM":     "#E65100",  # deep orange
    "CO_MINGLED_DOWNSTREAM":   "#D32F2F",  # red
    "RETAINED_OR_INDIRECT":    "#9E9E9E",  # grey
    "UNCLASSIFIED":            "#BDBDBD",  # light grey
}


def fdp_layer(catalog: str, schema: str) -> str:
    """Map a (catalog, schema) to its medallion layer."""
    if "_std_" in catalog:
        return "std"
    if "_itg_" in catalog:
        return "itg"
    if "_srv_" in catalog:
        return "srv"
    if catalog.startswith("fc_"):
        return "foreign"
    if catalog.startswith("aw_"):
        return "adpcoe"
    return "other"


# ---------------------------------------------------------------------------
def load_graph() -> tuple[nx.DiGraph, dict]:
    """Build a DiGraph from outputs/. Returns (graph, node_metadata)."""
    g = nx.DiGraph()
    nmeta: dict[str, dict] = {}

    with (OUT / "classified_nodes.csv").open() as f:
        for row in csv.DictReader(f):
            name = row["node"]
            cat = row.get("category", "UNCLASSIFIED")
            seps = ",".join(s for s in (
                "biz" if row.get("sep_business_entity") == "1" else "",
                "loc" if row.get("sep_location") == "1" else "",
                "emp" if row.get("sep_employee") == "1" else "",
                "cust" if row.get("sep_customer") == "1" else "",
                "mat" if row.get("sep_material") == "1" else "",
                "so" if row.get("sep_sales_org") == "1" else "",
            ) if s)
            nmeta[name] = {
                "category": cat,
                "is_seed": row.get("is_seed") in ("true", "TRUE", "1"),
                "catalog": row.get("catalog", ""),
                "schema":  row.get("schema", ""),
                "table":   row.get("table_name", ""),
                "n_up":    int(row.get("n_upstream") or 0),
                "n_dn":    int(row.get("n_downstream") or 0),
                "seps":    seps,
                "layer":   fdp_layer(row.get("catalog", ""), row.get("schema", "")),
            }
            g.add_node(name)

    with (OUT / "edges.csv").open() as f:
        for row in csv.DictReader(f):
            src, tgt = row["src_full_name"], row["tgt_full_name"]
            g.add_edge(src, tgt, edge_count=int(row["edge_count"]))

    return g, nmeta


# ---------------------------------------------------------------------------
def short_label(name: str) -> str:
    """`fdp_prd_itg_internal.itg_internal_finance.dim_supplier`
    → `itg_internal_finance.dim_supplier`."""
    parts = name.split(".")
    if len(parts) == 3:
        return f"{parts[1]}.{parts[2]}"
    return name


def write_pinchpoint_dot(g: nx.DiGraph, nmeta: dict, *, top_n: int | None = None,
                          neighbours: str = "all",
                          out_name: str = "lineage_pinchpoints") -> pathlib.Path:
    """Subgraph: every (or top-N) CO_MINGLED node + its 1-hop neighbours.

    neighbours:
      'all'           — include every 1-hop neighbour (huge for top_n=None)
      'mainland_only' — only include neighbours that are MAINLAND_TAGGED
      'none'          — only the pinch-points themselves
    """
    pinch = [n for n, m in nmeta.items()
             if m["category"] in ("CO_MINGLED_UPSTREAM", "CO_MINGLED_DOWNSTREAM")]
    if top_n is not None:
        pinch.sort(key=lambda n: nmeta[n]["n_up"] + nmeta[n]["n_dn"], reverse=True)
        pinch = pinch[:top_n]

    selected: set[str] = set(pinch)
    if neighbours != "none":
        for n in pinch:
            for nb in (*g.predecessors(n), *g.successors(n)):
                if neighbours == "all":
                    selected.add(nb)
                elif neighbours == "mainland_only" and nmeta[nb]["category"] == "MAINLAND_TAGGED":
                    selected.add(nb)

    # Group by FDP layer for a clean left-to-right cascade.
    layers: dict[str, list[str]] = {"std": [], "itg": [], "srv": [], "foreign": [], "adpcoe": [], "other": []}
    for n in selected:
        layers[nmeta[n]["layer"]].append(n)

    lines: list[str] = []
    lines.append('digraph G {')
    lines.append('  rankdir=LR;')
    lines.append('  graph [bgcolor="white", fontname="Helvetica", pad=0.5, splines=true, overlap=false];')
    lines.append('  node  [fontname="Helvetica", fontsize=9, shape=box, style="rounded,filled", penwidth=1.0];')
    lines.append('  edge  [fontname="Helvetica", fontsize=8, color="#90A4AE"];')
    lines.append('  // Layer columns (rank=same)')

    # Emit nodes per layer cluster.
    for layer in ("foreign", "std", "itg", "srv", "adpcoe", "other"):
        nodes = layers[layer]
        if not nodes:
            continue
        lines.append(f'  subgraph cluster_{layer} {{')
        lines.append(f'    label="{layer.upper()}"; style=rounded; color="#CFD8DC"; fontsize=11;')
        for n in sorted(nodes):
            m = nmeta[n]
            colour = CATEGORY_COLOUR.get(m["category"], "#BDBDBD")
            text_colour = "#FFFFFF" if m["category"] in (
                "CO_MINGLED_DOWNSTREAM","CO_MINGLED_UPSTREAM",
                "MAINLAND_INTERIOR","MAINLAND_SOURCE","MAINLAND_SINK") else "#212121"
            label = short_label(n).replace('"', '\\"')
            lines.append(
                f'    "{n}" [label="{label}", '
                f'fillcolor="{colour}", fontcolor="{text_colour}", '
                f'tooltip="{m["category"]} | up={m["n_up"]} dn={m["n_dn"]} seps={m["seps"]}"];'
            )
        lines.append('  }')

    # Emit edges among selected nodes.
    for u, v, d in g.edges(data=True):
        if u in selected and v in selected:
            lines.append(f'  "{u}" -> "{v}" [penwidth={min(3.0, 0.5 + d["edge_count"]/200):.2f}];')
    lines.append('}')

    out_dot = OUT / f"{out_name}.dot"
    out_dot.write_text("\n".join(lines))
    return out_dot


def write_layer_flow_dot(g: nx.DiGraph, nmeta: dict) -> pathlib.Path:
    """High-level cross-catalog flow (catalog × layer) as a small DAG."""
    flow_counts: dict[tuple[str, str], int] = {}
    flow_events: dict[tuple[str, str], int] = {}
    for u, v, d in g.edges(data=True):
        a = (nmeta[u]["catalog"], nmeta[u]["layer"])
        b = (nmeta[v]["catalog"], nmeta[v]["layer"])
        key = (f'{a[0]} ({a[1]})', f'{b[0]} ({b[1]})')
        flow_counts[key] = flow_counts.get(key, 0) + 1
        flow_events[key] = flow_events.get(key, 0) + d["edge_count"]

    # Group by layer for a clean left-to-right.
    nodes_by_layer: dict[str, set[str]] = {}
    for (src, tgt) in flow_counts:
        for n in (src, tgt):
            layer = n.split("(")[-1].rstrip(")")
            nodes_by_layer.setdefault(layer, set()).add(n)

    lines: list[str] = []
    lines.append('digraph G {')
    lines.append('  rankdir=LR;')
    lines.append('  graph [bgcolor="white", fontname="Helvetica", pad=0.5, splines=true, overlap=false, nodesep=0.4, ranksep=0.8];')
    lines.append('  node  [fontname="Helvetica", fontsize=10, shape=box, style="rounded,filled", fillcolor="#ECEFF1", penwidth=1.0];')
    lines.append('  edge  [fontname="Helvetica", fontsize=8, color="#607D8B"];')
    for layer in ("foreign", "std", "itg", "srv", "adpcoe", "other"):
        if layer not in nodes_by_layer: continue
        lines.append(f'  subgraph cluster_{layer} {{')
        lines.append(f'    label="{layer.upper()}"; style=rounded; color="#CFD8DC"; fontsize=12;')
        for n in sorted(nodes_by_layer[layer]):
            label = n.replace('"', '\\"')
            lines.append(f'    "{n}" [label="{label}"];')
        lines.append('  }')
    for (src, tgt), n_edges in sorted(flow_counts.items(), key=lambda kv: -kv[1]):
        events = flow_events[(src, tgt)]
        lines.append(
            f'  "{src}" -> "{tgt}" [label="{n_edges} edges\\n{events:,} ev", '
            f'penwidth={min(4.0, 0.5 + n_edges/300):.2f}];'
        )
    lines.append('}')
    out_dot = OUT / "lineage_layer_flow.dot"
    out_dot.write_text("\n".join(lines))
    return out_dot


def render(dot_file: pathlib.Path) -> None:
    """Render DOT to PNG and SVG using the system `dot` binary."""
    for fmt in ("png", "svg"):
        out = dot_file.with_suffix(f".{fmt}")
        subprocess.run(["dot", f"-T{fmt}", str(dot_file), "-o", str(out)], check=True)


def write_pyvis_full(g: nx.DiGraph, nmeta: dict) -> pathlib.Path:
    """Interactive pyvis HTML for the full graph with category colour."""
    net = Network(height="900px", width="100%", directed=True, notebook=False, bgcolor="#FAFAFA", font_color="#212121")
    net.barnes_hut(gravity=-12000, spring_length=120, central_gravity=0.2, damping=0.4)

    for n, m in nmeta.items():
        title = (
            f"<b>{n}</b><br>"
            f"category: {m['category']}<br>"
            f"layer: {m['layer']}<br>"
            f"upstream: {m['n_up']}, downstream: {m['n_dn']}<br>"
            f"separators: {m['seps'] or 'none'}"
        )
        size = max(8, min(40, 8 + 2 * (m["n_up"] + m["n_dn"]) ** 0.6))
        net.add_node(
            n, label=short_label(n),
            color=CATEGORY_COLOUR.get(m["category"], "#BDBDBD"),
            title=title, size=size,
        )
    for u, v, d in g.edges(data=True):
        net.add_edge(u, v, value=min(8, d["edge_count"] // 10), title=f'{d["edge_count"]} events')

    out = OUT / "lineage_full.html"
    net.write_html(str(out), notebook=False, open_browser=False)
    return out


# ---------------------------------------------------------------------------
def main() -> None:
    g, nmeta = load_graph()
    print(f"Loaded {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")

    # 1a. All 49 pinch-points + Mainland-tagged neighbours (Confluence embed)
    dot = write_pinchpoint_dot(
        g, nmeta, neighbours="mainland_only", out_name="lineage_pinchpoints_focus",
    )
    render(dot)
    print(f"  pinch-points (Mainland neighbours): {dot.with_suffix('.png')}")

    # 1b. All 49 pinch-points only, no neighbours (compact summary)
    dot = write_pinchpoint_dot(
        g, nmeta, neighbours="none", out_name="lineage_pinchpoints_only",
    )
    render(dot)
    print(f"  pinch-points (no neighbours): {dot.with_suffix('.png')}")

    # 1c. Full pinch-points + all neighbours (repo-only reference)
    dot = write_pinchpoint_dot(
        g, nmeta, neighbours="all", out_name="lineage_pinchpoints_full",
    )
    render(dot)
    print(f"  full pinch-points: {dot.with_suffix('.png')}")

    # 2. Layer-level flow
    dot = write_layer_flow_dot(g, nmeta)
    render(dot)
    print(f"  layer-flow DOT: {dot}")

    # 3. Full pyvis
    html = write_pyvis_full(g, nmeta)
    print(f"  pyvis HTML: {html}")


if __name__ == "__main__":
    main()
