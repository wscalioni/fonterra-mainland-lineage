# Fonterra Branding & UX Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default Bootstrap chrome of the Mainland Lineage app with a Fonterra-branded UI — logo top-left, Fonterra blue/green palette, Assistant typography, editorial layout — so it feels native to a Fonterra programme manager.

**Architecture:** Add a global CSS asset (Dash auto-loads everything in `app/assets/`) that defines the brand palette as CSS custom properties and applies editorial typography + restrained chrome. Replace the inline `dbc.NavbarSimple` with a small custom `branded_header()` component that renders the logo, page nav, and a thin divider. Three reusable components — `header`, `kpi_card`, `status_pill` — replace inlined HTML in pages. Data layer (`data_loader`, `status_writer`, `cytoscape_builder`, `nightly_refresh`) is **not touched** — this is purely chrome.

**Tech Stack:** Plotly Dash 2.18, dash-bootstrap-components (kept for table + form primitives only), CSS custom properties, Google Fonts (Assistant 400/700, Courgette accent).

**Aesthetic direction:** *Editorial cooperative* — annual-report typography meets enterprise dashboard. Strong black headlines, Fonterra blue as a deliberate accent (header bar, primary actions), green only for cleared/positive states, sharp 1px dividers (no shadows), tabular numerics, generous whitespace. Opposite of AI-slop purple gradients on white.

---

## Brand reference (canonical values used throughout)

```
--fonterra-blue:        #00539B  /* primary, header bar */
--fonterra-light-blue:  #00AEEF  /* hover, active, links */
--fonterra-green:       #72BF44  /* cleared, success */
--ink:                  #111827  /* headlines */
--text:                 #374151  /* body */
--muted:                #6B7280  /* labels, sub-text */
--rule:                 #E5E7EB  /* 1px dividers */
--surface:              #FFFFFF
--canvas:               #FAFAF8  /* warm off-white app background */
--danger:               #D32F2F  /* CO_MINGLED_DOWNSTREAM, also pinchpoints */
--warning:              #E65100  /* CO_MINGLED_UPSTREAM */
```

Fonts: **Assistant** (400/700) for everything; **Courgette** reserved for one accent moment (subtitle line under app name). Both via Google Fonts.

Page categories' colours (`CATEGORY_COLOUR` in `app/lib/colours.py`) are **data semantics, not chrome** — leave them alone.

---

## File Structure

```
app/
  assets/                                    NEW (Dash auto-serves /assets/*)
    style.css                                NEW — global brand CSS
    fonterra-logo.svg                        NEW — masterbrand SVG
  components/                                NEW
    __init__.py                              NEW
    header.py                                NEW — branded_header(active_path)
    kpi_card.py                              NEW — kpi_card(title, value, sub)
    status_pill.py                           NEW — status_pill(status)
  tests/
    test_components.py                       NEW — structure tests
  app.py                                     MOD — add Google Fonts external_stylesheets, replace NavbarSimple
  pages/
    programme_dashboard.py                   MOD — use kpi_card, polish heat map
    pinchpoint_tracker.py                    MOD — status pills in table cells
    graph_explorer.py                        MOD — sidebar polish
    search.py                                MOD — bigger search input, empty state
    workspace_identity.py                    MOD — table polish
    weekly_digest.py                         MOD — column polish
```

Untouched: every file under `app/lib/` (data_loader, status_writer, cytoscape_builder, colours, auth), `jobs/`, `lib/` (repo-root pipeline), `sql/`, `databricks.yml`.

---

## Conventions

- **CSS uses class names with `app-` prefix** to avoid colliding with bootstrap classes. Example: `app-header`, `app-kpi-card`, `app-status-pill`.
- **Tabular numerics:** `font-feature-settings: "tnum"` on any element rendering numbers. Built into the global CSS.
- **No new dependencies.** Google Fonts via stylesheet `<link>` is delivered via Dash's `external_stylesheets` argument — no requirements.txt changes.
- **Tests for components are pure structure assertions** — they import the component function and inspect the returned Dash component tree. No HTTP, no rendering, no Selenium.
- **Imports stay in `from lib.X` style** (matches the runtime convention from the previous plan).

---

## Task 1: CSS foundation + Google Fonts

**Files:**
- Create: `app/assets/style.css`
- Modify: `app/app.py` (add Google Fonts to external_stylesheets)

This is chrome-only — no tests required. Visual verification via local smoke test.

- [ ] **Step 1: Write `app/assets/style.css`**

```css
/* Mainland Lineage — Fonterra brand layer.
   Loaded automatically by Dash via app/assets/. */

:root {
  --fonterra-blue:        #00539B;
  --fonterra-light-blue:  #00AEEF;
  --fonterra-green:       #72BF44;
  --ink:                  #111827;
  --text:                 #374151;
  --muted:                #6B7280;
  --rule:                 #E5E7EB;
  --surface:              #FFFFFF;
  --canvas:               #FAFAF8;
  --danger:               #D32F2F;
  --warning:              #E65100;
}

html, body {
  margin: 0;
  padding: 0;
  background: var(--canvas);
  color: var(--text);
  font-family: "Assistant", system-ui, -apple-system, sans-serif;
  font-feature-settings: "tnum";
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}

h1, h2, h3, h4, h5, h6 {
  color: var(--ink);
  font-weight: 700;
  letter-spacing: -0.01em;
  margin-top: 0;
}

a { color: var(--fonterra-blue); text-decoration: none; }
a:hover { color: var(--fonterra-light-blue); text-decoration: underline; }

/* Eyebrow / section label */
.app-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}

/* Header */
.app-header {
  display: flex;
  align-items: center;
  background: var(--fonterra-blue);
  color: #fff;
  padding: 14px 32px;
  border-bottom: 4px solid var(--fonterra-light-blue);
}

.app-header__logo {
  height: 28px;
  width: auto;
  margin-right: 24px;
  filter: brightness(0) invert(1);  /* logo SVG renders in white on the blue bar */
}

.app-header__brand {
  display: flex;
  flex-direction: column;
  margin-right: 48px;
}

.app-header__brand-line {
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 0.04em;
  line-height: 1;
}

.app-header__brand-sub {
  font-family: "Courgette", "Assistant", cursive;
  font-size: 13px;
  margin-top: 2px;
  opacity: 0.85;
  line-height: 1;
}

.app-header__nav {
  display: flex;
  gap: 28px;
  flex: 1;
}

.app-header__nav a {
  color: #fff;
  font-size: 14px;
  font-weight: 400;
  opacity: 0.78;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
}

.app-header__nav a.is-active {
  opacity: 1;
  font-weight: 700;
  border-bottom-color: var(--fonterra-light-blue);
}

.app-header__nav a:hover {
  opacity: 1;
  text-decoration: none;
}

/* Page container */
.app-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 48px 32px;
}

.app-page h2 {
  font-size: 32px;
  letter-spacing: -0.02em;
  margin-bottom: 4px;
}

.app-page__subtitle {
  color: var(--muted);
  font-size: 16px;
  margin-top: 0;
  margin-bottom: 40px;
}

/* KPI card grid */
.app-kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 24px;
  margin: 24px 0 56px;
}

@media (max-width: 1100px) { .app-kpi-row { grid-template-columns: repeat(2, 1fr); } }

.app-kpi-card {
  background: var(--surface);
  border: 1px solid var(--rule);
  padding: 20px 22px 22px;
}

.app-kpi-card__label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 700;
  margin-bottom: 12px;
}

.app-kpi-card__value {
  color: var(--ink);
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}

.app-kpi-card__sub {
  margin-top: 8px;
  font-size: 13px;
  color: var(--muted);
}

/* Heat map */
.app-heat {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 16px;
}

.app-heat__tile {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
  padding: 6px 10px;
  color: #fff;
  border-radius: 0;
  cursor: default;
}

.app-heat__tile--danger  { background: var(--danger); }
.app-heat__tile--warning { background: var(--warning); }
.app-heat__tile--ok      { background: var(--fonterra-green); color: #0d3a0a; }

/* Status pill */
.app-pill {
  display: inline-block;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  border-radius: 999px;
  border: 1px solid transparent;
  white-space: nowrap;
}
.app-pill--pending          { background: #F3F4F6; color: #4B5563; border-color: #D1D5DB; }
.app-pill--uc-tagged        { background: #DBEAFE; color: #1E40AF; border-color: #BFDBFE; }
.app-pill--row-filtered     { background: #E0F2FE; color: #075985; border-color: #BAE6FD; }
.app-pill--attested         { background: #FEF3C7; color: #92400E; border-color: #FDE68A; }
.app-pill--cleared          { background: #DCFCE7; color: #14532D; border-color: #86EFAC; }

/* Tables */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner {
  font-family: "Assistant", system-ui, sans-serif !important;
  font-size: 13px !important;
}

.dash-table-container .dash-header {
  background: var(--canvas) !important;
  color: var(--ink) !important;
  font-weight: 700 !important;
  border-bottom: 2px solid var(--ink) !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 11px !important;
}

.dash-table-container .dash-cell {
  border-bottom: 1px solid var(--rule) !important;
}

/* Buttons */
.btn-primary, button.btn-primary {
  background-color: var(--fonterra-blue) !important;
  border-color: var(--fonterra-blue) !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em !important;
}
.btn-primary:hover { background-color: var(--fonterra-light-blue) !important; border-color: var(--fonterra-light-blue) !important; }

/* Sidebar (graph explorer + search) */
.app-sidebar {
  border-right: 1px solid var(--rule);
  padding-right: 24px;
}

.app-sidebar h5 {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 700;
}

/* Search input */
.app-search-bar input {
  font-size: 18px !important;
  padding: 14px 18px !important;
  border: 1px solid var(--rule) !important;
  border-right: 0 !important;
}
.app-search-bar input:focus {
  outline: none;
  border-color: var(--fonterra-blue) !important;
  box-shadow: 0 0 0 3px rgba(0,83,155,0.12);
}
.app-search-bar .btn-primary {
  border-radius: 0 !important;
  padding: 14px 24px !important;
}

/* Section headings on dashboard */
.app-section-h {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: 40px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--ink);
}
.app-section-h h4 {
  font-size: 18px;
  margin: 0;
}
.app-section-h__count {
  font-size: 12px;
  color: var(--muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

/* Cytoscape container — let it own the white space */
.app-graph-shell {
  background: var(--surface);
  border: 1px solid var(--rule);
}

/* Error banner */
.app-error {
  background: #FEF2F2;
  border: 1px solid #FCA5A5;
  color: #991B1B;
  padding: 12px 16px;
  margin-bottom: 24px;
  font-size: 13px;
}
```

- [ ] **Step 2: Modify `app/app.py` to wire Google Fonts and the canvas background**

Replace the entire content of `app/app.py` with:

```python
"""Dash entry point for the Mainland Lineage app.

The Databricks Apps runtime calls ``python app.py``. Locally, set
DATABRICKS_CONFIG_PROFILE and DATABRICKS_WAREHOUSE_ID in the env then
run ``python app/app.py`` from the repo root.
"""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
from dash import html

from components.header import branded_header

GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Assistant:wght@400;700"
    "&family=Courgette&display=swap"
)

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP, GOOGLE_FONTS],
    suppress_callback_exceptions=True,
    title="Mainland Lineage — Fonterra",
    update_title=None,
)

app.layout = html.Div([
    branded_header(),
    html.Div(dash.page_container, className="app-page"),
])

if __name__ == "__main__":
    port = int(os.environ.get("DATABRICKS_APP_PORT", "8050"))
    app.run(host="0.0.0.0", port=port, debug=False)
```

This depends on `components.header.branded_header` which is built in Task 3. Until then `python app.py` will ImportError — that's expected. Don't run the smoke test until Task 4.

- [ ] **Step 3: Commit**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
git add app/assets/style.css app/app.py
git commit -m "feat(ui): add Fonterra brand CSS + Google Fonts wiring

App will not start until components/header.py lands in Task 3."
```

---

## Task 2: Fonterra logo asset

**Files:**
- Create: `app/assets/fonterra-logo.svg`

- [ ] **Step 1: Download the Fonterra masterbrand logo**

Try Fonterra's site first (it's a public asset on a public site):

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
mkdir -p app/assets

# Try the standard masterbrand path
curl -fsSL --retry 2 \
  "https://www.fonterra.com/content/dam/fonterra-public-website/global/masterbrand/Fonterra%20masterbrand-logo.svg" \
  -o app/assets/fonterra-logo.svg \
  && file app/assets/fonterra-logo.svg | grep -i svg \
  || rm -f app/assets/fonterra-logo.svg
```

If that 404s or returns non-SVG, try the PNG variant and call it good:

```bash
[ ! -f app/assets/fonterra-logo.svg ] && \
curl -fsSL \
  "https://www.fonterra.com/content/dam/fonterra-public-website/global/masterbrand/Fonterra%20masterbrand-logo.png" \
  -o app/assets/fonterra-logo.png \
  && echo "Got PNG fallback" \
  && ls -la app/assets/fonterra-logo.*
```

If both fail, fall back to a clean SVG word-mark you write by hand. Only use this fallback if the live URLs don't work — it's a substitute, not the real mark:

```bash
cat > app/assets/fonterra-logo.svg <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 40" role="img" aria-label="Fonterra">
  <text x="0" y="30" font-family="Assistant, system-ui, sans-serif"
        font-size="30" font-weight="700" letter-spacing="-0.5"
        fill="currentColor">Fonterra</text>
</svg>
SVG
```

(`fill="currentColor"` lets the header CSS recolour it to white via `filter: brightness(0) invert(1)`. That filter works for both the SVG word-mark fallback and the real masterbrand SVG, which is normally green.)

If the PNG path was the only one that worked, the header CSS rule needs a small tweak — change the `app/assets/style.css` selector `.app-header__logo` to drop `filter: brightness(0) invert(1)` (Fonterra's PNG is already white-on-transparent for dark headers in their site CDN). Test visually in Task 4 and adjust if the logo disappears or shows weirdly.

- [ ] **Step 2: Confirm the file exists**

```bash
ls -la app/assets/fonterra-logo.* | head
```

Expected: at least one of `fonterra-logo.svg` or `fonterra-logo.png`.

- [ ] **Step 3: Commit**

```bash
git add app/assets/
git commit -m "chore(ui): add Fonterra masterbrand logo asset"
```

---

## Task 3: Branded header component (TDD)

**Files:**
- Create: `app/components/__init__.py`
- Create: `app/components/header.py`
- Create: `app/tests/test_components.py`

- [ ] **Step 1: Create the package marker**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
touch app/components/__init__.py
```

- [ ] **Step 2: Write the failing test**

Create `app/tests/test_components.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
.venv/bin/pytest app/tests/test_components.py -v
```

Expected: ImportError or 5 failures — `header` module doesn't exist yet.

- [ ] **Step 4: Implement `app/components/header.py`**

```python
"""Fonterra-branded header for the Mainland Lineage app."""
from __future__ import annotations

from dash import html

NAV_PAGES = [
    ("/",            "Dashboard"),
    ("/pinchpoints", "Pinch-points"),
    ("/graph",       "Graph"),
    ("/search",      "Search"),
    ("/workspaces",  "Workspaces"),
    ("/digest",      "Weekly digest"),
]


def branded_header(active_path: str = "/") -> html.Div:
    """Return the page-spanning Fonterra header.

    ``active_path`` matches a NAV_PAGES href; the matching link gets the
    ``is-active`` class. Defaults to "/" so the dashboard is highlighted
    at app boot before client-side routing kicks in.
    """
    nav_links = [
        html.A(
            label,
            href=path,
            className="is-active" if path == active_path else "",
        )
        for path, label in NAV_PAGES
    ]
    return html.Div(
        [
            html.Img(
                src="/assets/fonterra-logo.svg",
                alt="Fonterra",
                className="app-header__logo",
            ),
            html.Div(
                [
                    html.Div("Mainland Lineage", className="app-header__brand-line"),
                    html.Div(
                        "data separation programme",
                        className="app-header__brand-sub",
                    ),
                ],
                className="app-header__brand",
            ),
            html.Nav(nav_links, className="app-header__nav"),
        ],
        className="app-header",
    )
```

If your logo asset only resolved to `fonterra-logo.png` (Task 2 fallback), change `src="/assets/fonterra-logo.svg"` to `src="/assets/fonterra-logo.png"`.

- [ ] **Step 5: Run tests — expect 5 PASS**

```bash
.venv/bin/pytest app/tests/test_components.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add app/components/__init__.py app/components/header.py app/tests/test_components.py
git commit -m "feat(ui): branded_header component with Fonterra logo + nav (5 TDD tests)"
```

---

## Task 4: Local smoke test the new shell

**Files:** none (verification step only)

- [ ] **Step 1: Run the app locally**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage/app
lsof -ti :8050 | xargs -r kill 2>/dev/null
DATABRICKS_CONFIG_PROFILE=FONTERRA \
DATABRICKS_WAREHOUSE_ID=406253829ca12fd5 \
WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis \
nohup ../.venv/bin/python app.py > /tmp/dashapp.log 2>&1 &
APP_PID=$!
sleep 5
curl -s -o /dev/null -w "Home: %{http_code}\n" http://localhost:8050/
curl -s http://localhost:8050/ | grep -E '(app-header|fonterra-logo|Assistant)' | head -5
kill $APP_PID 2>/dev/null
lsof -ti :8050 | xargs -r kill 2>/dev/null
```

Expected: HTTP 200, AND grep matches at least one of `app-header`, `fonterra-logo`, `Assistant`. If grep finds nothing, the new chrome isn't actually being served — investigate before proceeding.

If it's broken, dump the log:

```bash
tail -30 /tmp/dashapp.log
```

- [ ] **Step 2: No commit needed** — this task is verification only.

---

## Task 5: KPI card component (TDD)

**Files:**
- Create: `app/components/kpi_card.py`
- Modify: `app/tests/test_components.py` (append new tests)

- [ ] **Step 1: Append the failing tests**

Add to the END of `app/tests/test_components.py`:

```python
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
```

- [ ] **Step 2: Run tests, expect ImportError**

```bash
.venv/bin/pytest app/tests/test_components.py -v
```

Expected: import fails on `from components.kpi_card import kpi_card`.

- [ ] **Step 3: Implement `app/components/kpi_card.py`**

```python
"""Editorial KPI card — eyebrow label, large value, optional sub."""
from __future__ import annotations

from dash import html


def kpi_card(label: str, value: str, sub: str | None = None) -> html.Div:
    """Single KPI tile.

    ``label`` renders as a tiny uppercase eyebrow; ``value`` is the large
    headline; ``sub`` is the muted detail line and is omitted entirely if
    None or empty.
    """
    children = [
        html.Div(label, className="app-kpi-card__label"),
        html.Div(value, className="app-kpi-card__value"),
    ]
    if sub:
        children.append(html.Div(sub, className="app-kpi-card__sub"))
    return html.Div(children, className="app-kpi-card")
```

- [ ] **Step 4: Run tests, expect 8 pass total (5 header + 3 kpi)**

```bash
.venv/bin/pytest app/tests/test_components.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/components/kpi_card.py app/tests/test_components.py
git commit -m "feat(ui): editorial kpi_card component (3 TDD tests)"
```

---

## Task 6: Refresh `programme_dashboard.py`

**Files:**
- Modify: `app/pages/programme_dashboard.py`

- [ ] **Step 1: Replace the entire file contents**

```python
"""Programme dashboard — homepage. KPI cards + schema heat map."""
from __future__ import annotations

import os
from datetime import date

import pandas as pd
from dash import Input, Output, callback, dcc, html
import dash

from lib import data_loader
from lib.auth import obo_client
from components.kpi_card import kpi_card

dash.register_page(__name__, path="/", name="Dashboard")

TSA_EXIT = date(2028, 4, 1)
WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")


def layout():
    return html.Div([
        html.Div("Programme overview", className="app-eyebrow"),
        html.H2("Mainland divestment data separation"),
        html.P(
            "Track the engineering scope of the Mainland carve-out across "
            "FDP — pinch-points, schemas at risk, and weekly progress.",
            className="app-page__subtitle",
        ),
        html.Div(id="dashboard-error"),
        html.Div(id="kpi-row", className="app-kpi-row"),

        html.Div([
            html.Div([html.H4("Schemas by entanglement risk")], className="app-section-h"),
            dcc.Loading(html.Div(id="schema-heat", className="app-heat")),
        ]),

        dcc.Interval(id="dash-load-once", n_intervals=0, max_intervals=1, interval=100),
    ])


@callback(
    Output("kpi-row", "children"),
    Output("schema-heat", "children"),
    Output("dashboard-error", "children"),
    Input("dash-load-once", "n_intervals"),
)
def _load(_n):
    if not WAREHOUSE:
        return [], [], html.Div("DATABRICKS_WAREHOUSE_ID not set.", className="app-error")
    try:
        client = obo_client()
        classified = data_loader.load_classified(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        status = data_loader.load_pinchpoint_status(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        refresh = data_loader.load_refresh_control(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
    except RuntimeError as e:
        return [], [], html.Div(f"Permission or query error: {e}", className="app-error")

    pinchpoints = classified[classified["category"].str.startswith("CO_MINGLED")]
    cleared = status[status["status"] == "Cleared"] if not status.empty else pd.DataFrame()
    schemas_with_pinch = pinchpoints["schema"].nunique()
    days_to_exit = (TSA_EXIT - date.today()).days
    last_refresh = refresh["run_completed"].iloc[0] if not refresh.empty else "never"

    cards = [
        kpi_card("Mainland-touching", f"{len(classified):,}", "objects in fdp_prd"),
        kpi_card("Pinch-points", f"{len(cleared)} / {len(pinchpoints)}", "cleared"),
        kpi_card("Active schemas", f"{schemas_with_pinch}", "with CO_MINGLED nodes"),
        kpi_card("TSA exit", "1 Apr 2028", f"{days_to_exit} days remaining"),
        kpi_card("Last refresh", str(last_refresh)[:16], "incremental"),
    ]

    schema_summary = (
        classified.groupby("schema")
        .agg(
            n=("node", "count"),
            n_pinch=("category", lambda s: s.isin(["CO_MINGLED_UPSTREAM", "CO_MINGLED_DOWNSTREAM"]).sum()),
            n_source=("category", lambda s: (s == "MAINLAND_SOURCE").sum()),
            n_sink=("category", lambda s: (s == "MAINLAND_SINK").sum()),
        )
        .reset_index()
        .sort_values(["n_pinch", "n"], ascending=[False, False])
    )

    def _tile_class(row):
        if row["n_pinch"] > 0:
            return "app-heat__tile app-heat__tile--danger"
        if row["n_source"] + row["n_sink"] > 0:
            return "app-heat__tile app-heat__tile--warning"
        return "app-heat__tile app-heat__tile--ok"

    tiles = [
        html.Div(
            f"{r['schema']} ({r['n']})",
            title=f"{r['n_pinch']} pinch / {r['n_source']} source / {r['n_sink']} sink",
            className=_tile_class(r),
        )
        for _, r in schema_summary.iterrows()
    ]
    return cards, tiles, ""
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage/app
lsof -ti :8050 | xargs -r kill 2>/dev/null
DATABRICKS_CONFIG_PROFILE=FONTERRA \
DATABRICKS_WAREHOUSE_ID=406253829ca12fd5 \
WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis \
nohup ../.venv/bin/python app.py > /tmp/dashapp.log 2>&1 &
APP_PID=$!
sleep 5
curl -s -o /dev/null -w "Home: %{http_code}\n" http://localhost:8050/
kill $APP_PID 2>/dev/null
lsof -ti :8050 | xargs -r kill 2>/dev/null
```

Expected: 200.

- [ ] **Step 3: Commit**

```bash
git add app/pages/programme_dashboard.py
git commit -m "feat(ui): editorial dashboard with kpi_card + heat map polish"
```

---

## Task 7: Status pill component (TDD)

**Files:**
- Create: `app/components/status_pill.py`
- Modify: `app/tests/test_components.py` (append)

- [ ] **Step 1: Append the failing tests**

```python
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
```

- [ ] **Step 2: Run tests — expect ImportError**

- [ ] **Step 3: Implement `app/components/status_pill.py`**

```python
"""Coloured pill for pinch-point separation status."""
from __future__ import annotations

from dash import html

STATUS_TO_CLASS = {
    "Pending":              "app-pill--pending",
    "UC Tagged":            "app-pill--uc-tagged",
    "Row Filter Applied":   "app-pill--row-filtered",
    "Attested":             "app-pill--attested",
    "Cleared":              "app-pill--cleared",
}


def status_pill(status: str) -> html.Span:
    suffix = STATUS_TO_CLASS.get(status, STATUS_TO_CLASS["Pending"])
    return html.Span(status, className=f"app-pill {suffix}")
```

- [ ] **Step 4: Run tests — expect all pass (8 + 7 = 15)**

```bash
.venv/bin/pytest app/tests/test_components.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/components/status_pill.py app/tests/test_components.py
git commit -m "feat(ui): status_pill component for pinch-point states (7 TDD tests)"
```

---

## Task 8: Refresh `pinchpoint_tracker.py`

**Files:**
- Modify: `app/pages/pinchpoint_tracker.py`

The DataTable status column will keep using the dropdown editor (Dash's data_table dropdown is not skinnable into pills directly — pills would mean a custom React component which is out of scope). Instead: keep dropdown editing, but visually tighten the table, lift the "X / Y cleared" progress bar into a prominent KPI card-style banner, and use the editorial header.

- [ ] **Step 1: Replace the entire file**

```python
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
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage/app
lsof -ti :8050 | xargs -r kill 2>/dev/null
DATABRICKS_CONFIG_PROFILE=FONTERRA \
DATABRICKS_WAREHOUSE_ID=406253829ca12fd5 \
WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis \
nohup ../.venv/bin/python app.py > /tmp/dashapp.log 2>&1 &
APP_PID=$!
sleep 5
curl -s -o /dev/null -w "Pinch: %{http_code}\n" http://localhost:8050/pinchpoints
kill $APP_PID 2>/dev/null
lsof -ti :8050 | xargs -r kill 2>/dev/null
```

Expected: 200.

- [ ] **Step 3: Commit**

```bash
git add app/pages/pinchpoint_tracker.py
git commit -m "feat(ui): editorial pinchpoint tracker with progress banner + table polish"
```

---

## Task 9: Refresh `graph_explorer.py`

**Files:**
- Modify: `app/pages/graph_explorer.py`

- [ ] **Step 1: Replace the entire file**

```python
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
            f"upstream {data['n_upstream']} · downstream {data['n_downstream']} · "
            f"bridge {data['bridge_score']:.2f}",
            style={"marginTop": "4px"},
        ),
    ])
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage/app
lsof -ti :8050 | xargs -r kill 2>/dev/null
DATABRICKS_CONFIG_PROFILE=FONTERRA \
DATABRICKS_WAREHOUSE_ID=406253829ca12fd5 \
WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis \
nohup ../.venv/bin/python app.py > /tmp/dashapp.log 2>&1 &
APP_PID=$!
sleep 5
curl -s -o /dev/null -w "Graph: %{http_code}\n" http://localhost:8050/graph
kill $APP_PID 2>/dev/null
lsof -ti :8050 | xargs -r kill 2>/dev/null
```

Expected: 200.

- [ ] **Step 3: Commit**

```bash
git add app/pages/graph_explorer.py
git commit -m "feat(ui): graph explorer with editorial sidebar + node info panel"
```

---

## Task 10: Refresh `search.py`

**Files:**
- Modify: `app/pages/search.py`

- [ ] **Step 1: Replace the entire file**

```python
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
            html.Span(" · ", style={"color": "var(--muted)", "margin": "0 6px"}),
            html.Span(r["category"]),
            html.Span(" · ", style={"color": "var(--muted)", "margin": "0 6px"}),
            html.Span(f"upstream {int(r['n_upstream'])} · downstream {int(r['n_downstream'])} · "
                      f"bridge {float(r.get('bridge_score') or 0):.2f}"),
        ])
    return elements, summary
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage/app
lsof -ti :8050 | xargs -r kill 2>/dev/null
DATABRICKS_CONFIG_PROFILE=FONTERRA \
DATABRICKS_WAREHOUSE_ID=406253829ca12fd5 \
WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis \
nohup ../.venv/bin/python app.py > /tmp/dashapp.log 2>&1 &
APP_PID=$!
sleep 5
curl -s -o /dev/null -w "Search: %{http_code}\n" http://localhost:8050/search
kill $APP_PID 2>/dev/null
lsof -ti :8050 | xargs -r kill 2>/dev/null
```

- [ ] **Step 3: Commit**

```bash
git add app/pages/search.py
git commit -m "feat(ui): search page with editorial header + bigger search bar"
```

---

## Task 11: Refresh `workspace_identity.py` and `weekly_digest.py`

Both pages get a light editorial header and improved table styling. Combined into one task since they're small.

**Files:**
- Modify: `app/pages/workspace_identity.py`
- Modify: `app/pages/weekly_digest.py`

- [ ] **Step 1: Replace `app/pages/workspace_identity.py`**

```python
"""Workspace identity panel — annotate the 10 workspace IDs from Phase 0."""
from __future__ import annotations

import os

import dash
from dash import Input, Output, State, callback, dash_table, dcc, html

from lib import data_loader, status_writer
from lib.auth import obo_client, user_email

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
        html.Div("Lineage sources", className="app-eyebrow"),
        html.H2("Workspace identities"),
        html.P(
            "Workspace IDs that appear in lineage events over the last 30 days. "
            "Annotate each with a recognisable name so edge tooltips read clearly.",
            className="app-page__subtitle",
        ),
        html.Div(id="ws-error"),
        dash_table.DataTable(
            id="ws-table",
            columns=[
                {"name": "Workspace ID", "id": "workspace_id"},
                {"name": "Events (30d)", "id": "event_count"},
                {"name": "Display name", "id": "display_name", "editable": True},
                {"name": "Notes", "id": "notes", "editable": True},
            ],
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
            style_as_list_view=True,
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
        return [], html.Div("DATABRICKS_WAREHOUSE_ID not set.", className="app-error")
    try:
        c = obo_client()
        events = data_loader._execute(c, warehouse_id=WAREHOUSE, statement=EVENTS_QUERY)
        identities = data_loader.load_workspace_identities(
            c, warehouse_id=WAREHOUSE, working_schema=SCHEMA,
        )
    except RuntimeError as e:
        return [], html.Div(str(e), className="app-error")
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
        c = obo_client()
        for r in diffs:
            status_writer.set_workspace_identity(
                c, warehouse_id=WAREHOUSE, working_schema=SCHEMA,
                workspace_id=r["workspace_id"],
                display_name=r["display_name"] or "",
                notes=r["notes"] or "",
                updated_by=user_email(),
            )
    except RuntimeError as e:
        return html.Div(f"Save failed: {e}", className="app-error")
    return ""
```

- [ ] **Step 2: Replace `app/pages/weekly_digest.py`**

```python
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


def _column(title, body_id):
    return html.Div(
        [
            html.Div(title, className="app-eyebrow", style={"marginBottom": "12px"}),
            html.Div(id=body_id),
        ],
        style={
            "background": "var(--surface)",
            "border": "1px solid var(--rule)",
            "padding": "20px 22px",
        },
    )


def layout():
    return html.Div([
        html.Div("This week", className="app-eyebrow"),
        html.H2("Weekly digest"),
        html.P(
            "Mirrors what changed in lineage and engineering progress. "
            "Populates after the nightly incremental refresh runs.",
            className="app-page__subtitle",
        ),
        html.Div(id="d-error"),
        dbc.Row([
            dbc.Col(_column("New nodes", "d-new-nodes"), width=4),
            dbc.Col(_column("Newly CO_MINGLED", "d-new-pinch"), width=4),
            dbc.Col(_column("Cleared this week", "d-cleared"), width=4),
        ], className="g-3"),
        dcc.Interval(id="d-load-once", n_intervals=0, max_intervals=1, interval=100),
    ])


def _table(df, columns):
    if df.empty:
        return html.Div("none", style={"color": "var(--muted)", "fontStyle": "italic"})
    return dbc.Table.from_dataframe(df[columns], striped=False, size="sm",
                                     className="app-digest-table")


@callback(
    Output("d-new-nodes", "children"),
    Output("d-new-pinch", "children"),
    Output("d-cleared", "children"),
    Output("d-error", "children"),
    Input("d-load-once", "n_intervals"),
)
def _load(_n):
    if not WAREHOUSE:
        return "", "", "", html.Div("DATABRICKS_WAREHOUSE_ID not set.", className="app-error")
    try:
        c = obo_client()
        new_nodes = data_loader._execute(c, warehouse_id=WAREHOUSE,
                                          statement=NEW_NODES_QUERY.format(schema=SCHEMA))
        new_pinch = data_loader._execute(c, warehouse_id=WAREHOUSE,
                                          statement=NEW_PINCH_QUERY.format(schema=SCHEMA))
        cleared = data_loader._execute(c, warehouse_id=WAREHOUSE,
                                        statement=CLEARED_QUERY.format(schema=SCHEMA))
    except RuntimeError as e:
        return "", "", "", html.Div(f"Error: {e}", className="app-error")
    return (
        _table(new_nodes, ["full_name", "category"]),
        _table(new_pinch, ["node", "category"]),
        _table(cleared, ["node", "updated_at", "updated_by"]),
        "",
    )
```

- [ ] **Step 3: Smoke test both routes**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage/app
lsof -ti :8050 | xargs -r kill 2>/dev/null
DATABRICKS_CONFIG_PROFILE=FONTERRA \
DATABRICKS_WAREHOUSE_ID=406253829ca12fd5 \
WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis \
nohup ../.venv/bin/python app.py > /tmp/dashapp.log 2>&1 &
APP_PID=$!
sleep 5
curl -s -o /dev/null -w "Workspaces: %{http_code}\n" http://localhost:8050/workspaces
curl -s -o /dev/null -w "Digest: %{http_code}\n" http://localhost:8050/digest
kill $APP_PID 2>/dev/null
lsof -ti :8050 | xargs -r kill 2>/dev/null
```

- [ ] **Step 4: Commit**

```bash
git add app/pages/workspace_identity.py app/pages/weekly_digest.py
git commit -m "feat(ui): editorial workspace identity + weekly digest"
```

---

## Task 12: Deploy + push

**Files:** none — deploy only.

- [ ] **Step 1: Re-run the test suite end to end**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
.venv/bin/pytest app/ jobs/ -v 2>&1 | tail -20
```

Expected: all tests pass (data_loader 3 + status_writer 3 + cytoscape_builder 5 + nightly_refresh 4 + components 15 = 30).

- [ ] **Step 2: Local end-to-end smoke**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage/app
lsof -ti :8050 | xargs -r kill 2>/dev/null
DATABRICKS_CONFIG_PROFILE=FONTERRA \
DATABRICKS_WAREHOUSE_ID=406253829ca12fd5 \
WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis \
nohup ../.venv/bin/python app.py > /tmp/dashapp.log 2>&1 &
APP_PID=$!
sleep 5
for path in / /pinchpoints /graph /search /workspaces /digest; do
  printf "%-15s" "$path"
  curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8050$path"
done
kill $APP_PID 2>/dev/null
lsof -ti :8050 | xargs -r kill 2>/dev/null
```

Expected: 200 on all six.

- [ ] **Step 3: Bundle deploy**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
databricks bundle deploy --target dev 2>&1 | tail -5
```

Expected: `Deployment complete!`

- [ ] **Step 4: Push the source to the app**

```bash
databricks apps deploy mainland-lineage \
  --source-code-path /Workspace/Users/will.scalioni2@fonterra.com/.bundle/fonterra-mainland-lineage/dev/files/app \
  --profile FONTERRA 2>&1 | tail -10
```

Expected: `state: SUCCEEDED`, `message: App started successfully`.

- [ ] **Step 5: Wait for RUNNING**

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  STATE=$(databricks apps get mainland-lineage --profile FONTERRA --output json | jq -r '.app_status.state // "unknown"')
  echo "Attempt $i: app=$STATE"
  case "$STATE" in
    RUNNING|ACTIVE) break ;;
    UNAVAILABLE|CRASHED) [ $i -gt 3 ] && break ;;
  esac
  sleep 15
done
```

If the app comes back CRASHED, dump `/Users/will.scalioni/git/fonterra-mainland-lineage/app/components/__init__.py` to confirm it exists (empty file). Most commonly an empty package marker missing breaks Apps imports.

- [ ] **Step 6: Push to GitHub**

```bash
gh auth switch --user wscalioni
git push origin main
gh auth switch --user will-scalioni_data
```

- [ ] **Step 7: Manual visual verification (Will, in Arc)**

Open `https://mainland-lineage-2924922257177540.0.azure.databricksapps.com` and walk:

```
/                   header logo + KPI cards + heat map
/pinchpoints        progress banner + table
/graph              sidebar + cytoscape
/search             big search bar + 2-hop subgraph
/workspaces         editable identity table
/digest             3-column digest grid
```

Confirm: Fonterra logo top-left, blue header bar, Assistant typography, clean tables.

If anything looks off (logo wrong colour, fonts missing, header collapsed) report back with a screenshot.

---

## Self-Review

**Spec coverage:**

| Spec item | Plan task |
|---|---|
| Fonterra colour scheme as CSS vars | Task 1 |
| Assistant + Courgette fonts | Task 1 |
| Logo top-left | Task 2 + Task 3 |
| Custom branded header | Task 3 + Task 4 |
| Redesigned KPI card | Task 5 + Task 6 |
| Status pills | Task 7 (component) — pinchpoint table keeps DataTable dropdown for editing |
| Page-by-page polish | Tasks 6, 8, 9, 10, 11 |
| No data layer changes | Confirmed: only `app/assets/`, `app/components/`, `app/app.py`, `app/pages/*.py` modified |
| CATEGORY_COLOUR untouched | Confirmed: `app/lib/colours.py` not in any task's modify list |
| Tests | Components have 15 unit tests across header (5), kpi_card (3), status_pill (7); pages still smoke-tested via curl |
| Deploy | Task 12 |

**Placeholder scan:** No `TBD`, `TODO`, "implement later", or "similar to" patterns. The two intentional caveats (logo asset URL fallback, app.py initial smoke test deferred to Task 4) are explicit and have decision criteria.

**Type consistency:**
- `branded_header(active_path: str = "/")` matches the test signature
- `kpi_card(label, value, sub=None)` — both the dashboard caller and the test pass these positionally
- `status_pill(status: str)` — exposed alongside `STATUS_TO_CLASS` dict for the parametrised test
- All page imports use `from lib.X` and `from components.X` — consistent with the runtime conventions established in the previous plan
