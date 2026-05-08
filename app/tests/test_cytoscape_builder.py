import pandas as pd
from lib import cytoscape_builder as cb


def _classified():
    return pd.DataFrame([
        {"node": "a.s.t1", "category": "MAINLAND_TAGGED", "catalog": "a",
         "schema": "s", "table_name": "t1", "n_upstream": 1, "n_downstream": 2,
         "bridge_score": 0.5},
        {"node": "a.s.t2", "category": "CO_MINGLED_DOWNSTREAM", "catalog": "a",
         "schema": "s", "table_name": "t2", "n_upstream": 0, "n_downstream": 5,
         "bridge_score": 0.9},
    ])


def _edges():
    return pd.DataFrame([
        {"src_full_name": "a.s.t1", "tgt_full_name": "a.s.t2", "edge_count": 7},
    ])


def test_build_elements_emits_one_node_per_row():
    elems = cb.build_elements(_classified(), _edges())
    nodes = [e for e in elems if "source" not in e["data"]]
    assert len(nodes) == 2
    assert {n["data"]["id"] for n in nodes} == {"a.s.t1", "a.s.t2"}


def test_build_elements_emits_edges_with_weights():
    elems = cb.build_elements(_classified(), _edges())
    edges = [e for e in elems if "source" in e["data"]]
    assert len(edges) == 1
    assert edges[0]["data"]["source"] == "a.s.t1"
    assert edges[0]["data"]["target"] == "a.s.t2"
    assert edges[0]["data"]["weight"] == 7


def test_node_size_uses_capped_formula():
    df = _classified()
    df.loc[0, "n_upstream"] = 100
    df.loc[0, "n_downstream"] = 100
    elems = cb.build_elements(df, _edges())
    sized = next(e for e in elems if e["data"]["id"] == "a.s.t1")
    assert sized["data"]["size"] <= 40
    assert sized["data"]["size"] >= 8


def test_co_mingled_nodes_get_pinch_class():
    elems = cb.build_elements(_classified(), _edges())
    pinch = next(e for e in elems if e["data"]["id"] == "a.s.t2")
    assert "pinch" in pinch.get("classes", "")


def test_filter_to_pinch_neighbourhood_includes_one_hop():
    df = _classified()
    edges = _edges()
    elems = cb.build_elements(df, edges, pinch_neighbourhood_only=True)
    ids = {e["data"]["id"] for e in elems if "source" not in e["data"]}
    assert "a.s.t2" in ids
    assert "a.s.t1" in ids
