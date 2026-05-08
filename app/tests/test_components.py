"""Pure structure tests for app components. No HTTP, no rendering."""
from __future__ import annotations

from dash import html

from components.header import branded_header


def _walk(node):
    """Yield every component in the tree (depth-first)."""
    yield node
    children = getattr(node, "children", None)
    if children is None:
        return
    if not isinstance(children, list):
        children = [children]
    for c in children:
        if hasattr(c, "children") or hasattr(c, "_prop_names"):
            yield from _walk(c)


def _classes(node):
    return (getattr(node, "className", "") or "").split()


def test_branded_header_returns_div_with_app_header_class():
    h = branded_header()
    assert "app-header" in _classes(h)


def test_branded_header_includes_fonterra_logo_image():
    h = branded_header()
    imgs = [n for n in _walk(h) if isinstance(n, html.Img)]
    assert len(imgs) == 1
    assert "fonterra-logo" in imgs[0].src


def test_branded_header_links_to_all_six_pages():
    expected_paths = {"/", "/pinchpoints", "/graph", "/search", "/workspaces", "/digest"}
    h = branded_header()
    links = [n for n in _walk(h) if isinstance(n, html.A)]
    hrefs = {l.href for l in links}
    assert expected_paths.issubset(hrefs), f"missing: {expected_paths - hrefs}"


def test_branded_header_marks_active_page():
    h = branded_header(active_path="/pinchpoints")
    links = [n for n in _walk(h) if isinstance(n, html.A)]
    active = [l for l in links if "is-active" in _classes(l)]
    assert len(active) == 1
    assert active[0].href == "/pinchpoints"


def test_branded_header_brand_includes_courgette_subtitle():
    h = branded_header()
    subs = [n for n in _walk(h) if "app-header__brand-sub" in _classes(n)]
    assert len(subs) == 1


from components.kpi_card import kpi_card


def test_kpi_card_renders_label_value_and_sub():
    c = kpi_card("Pinch-points", "12 / 49", "cleared")
    text_nodes = [str(n.children) for n in _walk(c) if hasattr(n, "children") and isinstance(n.children, str)]
    joined = " | ".join(text_nodes)
    assert "Pinch-points" in joined
    assert "12 / 49" in joined
    assert "cleared" in joined


def test_kpi_card_omits_sub_when_none():
    c = kpi_card("TSA exit", "2028-04-01")
    subs = [n for n in _walk(c) if "app-kpi-card__sub" in _classes(n)]
    assert subs == []


def test_kpi_card_uses_app_kpi_card_class():
    c = kpi_card("X", "Y")
    assert "app-kpi-card" in _classes(c)


import pytest
from components.status_pill import status_pill, STATUS_TO_CLASS


@pytest.mark.parametrize("status,suffix", list(STATUS_TO_CLASS.items()))
def test_status_pill_class_for(status, suffix):
    s = status_pill(status)
    assert "app-pill" in _classes(s)
    assert suffix in _classes(s)


def test_status_pill_renders_status_text():
    s = status_pill("UC Tagged")
    text_nodes = [str(n.children) for n in _walk(s) if hasattr(n, "children") and isinstance(n.children, str)]
    assert "UC Tagged" in " | ".join(text_nodes)


def test_status_pill_unknown_status_falls_back_to_pending():
    s = status_pill("Whatever")
    assert "app-pill--pending" in _classes(s)
