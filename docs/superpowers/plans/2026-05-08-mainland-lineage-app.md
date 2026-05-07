# Mainland Lineage Databricks App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert this repo into a Databricks App on Fonterra dev workspace `adb-2351505639777173` that lets Mike Trotter (programme manager, non-technical) navigate the UC lineage graph, track separation progress on the 49 CO_MINGLED pinch-points, and view a programme dashboard. Add an incremental Lakeflow refresh job replacing the current full re-walk.

**Architecture:** Single DABs bundle at the repo root deploys two resources: (a) a Plotly Dash app on Databricks Apps serverless with OBO auth, and (b) a Lakeflow nightly job that incrementally refreshes the lineage Delta tables via watermark + MERGE. The app reads the four existing pipeline tables (`mainland_lineage_seed`, `_edges`, `_nodes`, `_classified`) and writes status to three new tables (`pinchpoint_status`, `workspace_identities`, `refresh_control`). The existing CLI pipeline (`lib/lineage_walker.py`, `classify.py`, `visualize.py`) stays intact and continues to drive Confluence publishing and full BFS resets.

**Tech Stack:** Plotly Dash 2.18+, dash-cytoscape 1.0+, dash-bootstrap-components, pandas, databricks-sdk (StatementExecutionAPI), Delta Lake, Databricks Asset Bundles, Lakeflow Jobs.

---

## File Structure

```
databricks.yml                      NEW  bundle root, declares app + nightly job
.gitignore                          MOD  add .env, large pyvis HTML
docs/superpowers/plans/             NEW  this plan
app/
  app.py                            NEW  Dash entry point, multi-page router
  requirements.txt                  NEW  dash, dash-cytoscape, dbc, pandas, databricks-sdk
  lib/
    __init__.py                     NEW
    data_loader.py                  NEW  read helpers for all Delta tables
    cytoscape_builder.py            NEW  DataFrame to cytoscape elements
    status_writer.py                NEW  write-backs to status tables
    colours.py                      NEW  re-export CATEGORY_COLOUR from lib/visualize.py
  pages/
    __init__.py                     NEW
    programme_dashboard.py          NEW  homepage, KPI cards + heat map
    pinchpoint_tracker.py           NEW  49 CO_MINGLED with status write-back
    graph_explorer.py               NEW  Cytoscape full graph + filters
    search.py                       NEW  what touches this table
    workspace_identity.py           NEW  annotate the 10 workspace IDs
    weekly_digest.py                NEW  diff vs 7 days ago
  tests/
    test_data_loader.py             NEW  mocked SDK responses
    test_cytoscape_builder.py       NEW  pure transform tests
    test_status_writer.py           NEW  SQL composition tests
jobs/
  nightly_refresh.py                NEW  watermark + MERGE incremental
  tests/
    test_nightly_refresh.py         NEW  watermark/MERGE SQL composition tests
sql/
  00_status_tables.sql              NEW  CREATE TABLE IF NOT EXISTS for 3 status tables
  01_uc_grants.sql                  NEW  UC grants (run once)
lib/                                UNCHANGED  keep visualize.py CATEGORY_COLOUR canonical
```

---

## Conventions

- **Auth:** `from databricks.sdk import WorkspaceClient; w = WorkspaceClient()` — no tokens, no profile, runtime injects the user OBO token. For local dev only, set `DATABRICKS_CONFIG_PROFILE=FONTERRA` in shell before running `python app/app.py`.
- **SQL execution:** use `w.statement_execution.execute_statement(warehouse_id=os.environ["DATABRICKS_WAREHOUSE_ID"], statement=..., wait_timeout="50s")` from inside the app.
- **Working schema:** `aw_internal_adpcoe.mainland_lineage_analysis` — all reads + status writes scoped here.
- **Colours:** import from `lib.visualize.CATEGORY_COLOUR` exactly. Do not redefine.
- **Tests:** pytest. Unit tests mock `WorkspaceClient`. No integration tests in CI — they require live Fonterra auth.
- **Commits:** one per task. Conventional commits (`feat:`, `chore:`, `test:`).

---

## Task 1: Push the existing repo to public GitHub `wscalioni/fonterra-mainland-lineage`

**Files:**
- Modify: `.gitignore`
- New: GitHub repo `wscalioni/fonterra-mainland-lineage` (public)

- [ ] **Step 1: Update .gitignore for app artefacts**

Append to `.gitignore`:

```
# App + bundle
app/.venv/
app/__pycache__/
app/**/__pycache__/
.databricks/
*.bundle.lock

# Large outputs (PNG/SVG keep, HTML excluded — too big for git)
outputs/*.html

# Local dev secrets
.env
```

- [ ] **Step 2: Stage CLAUDE_CODE_PROMPT.md and .gitignore changes**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
git add .gitignore CLAUDE_CODE_PROMPT.md
git status
```

Expected: `.gitignore` modified, `CLAUDE_CODE_PROMPT.md` and the plan file new.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-05-08-mainland-lineage-app.md
git commit -m "chore: add app build plan + CLAUDE_CODE_PROMPT and ignore app artefacts"
```

- [ ] **Step 4: Switch gh to personal account `wscalioni`**

```bash
gh auth switch --user wscalioni
gh auth status | head -5
```

Expected: `Active account: true` for `wscalioni`.

- [ ] **Step 5: Create the public repo**

```bash
gh repo create wscalioni/fonterra-mainland-lineage \
  --public \
  --description "UC lineage spider-web + divestment app — Fonterra Mainland" \
  --source . \
  --remote origin \
  --push
```

If the remote already exists, run `git push -u origin main` instead.

Expected: repo URL printed, `main` pushed.

- [ ] **Step 6: Verify**

```bash
gh repo view wscalioni/fonterra-mainland-lineage --json url,visibility,defaultBranchRef
```

Expected: `"visibility":"PUBLIC"`, default branch `main`.

- [ ] **Step 7: Switch gh back to EMU default**

```bash
gh auth switch --user will-scalioni_data
```

---

## Task 2: Discover the Fonterra dev workspace SQL warehouse ID

**Files:**
- Create: `app/.env.example`

- [ ] **Step 1: List warehouses on dev workspace**

```bash
databricks warehouses list \
  --host https://adb-2351505639777173.13.azuredatabricks.net \
  --output json \
  | jq '.[] | {id, name, warehouse_type, state, enable_serverless_compute}'
```

Pick the first **serverless** warehouse in **RUNNING** or **STOPPED** state. Record its `id` (16-char hex).

- [ ] **Step 2: Create app/.env.example for local dev**

```
# Copy to app/.env (gitignored) for local development.
# In production these are injected by the Databricks Apps runtime.
DATABRICKS_CONFIG_PROFILE=FONTERRA
DATABRICKS_WAREHOUSE_ID=<paste-dev-warehouse-id-here>
WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis
```

- [ ] **Step 3: Commit**

```bash
git add app/.env.example
git commit -m "chore: add .env.example with required runtime vars"
```

- [ ] **Step 4: Record the warehouse ID for later steps**

```bash
export DEV_WAREHOUSE_ID=<the-id>
echo $DEV_WAREHOUSE_ID
```

You will use this in Task 15 (UC grants) and Task 16 (deploy).

---

## Task 3: Add the DABs scaffold

**Files:**
- Create: `databricks.yml`
- Create: `app/app.py` (minimal Dash shell)
- Create: `app/requirements.txt`
- Create: `app/lib/__init__.py`, `app/pages/__init__.py`, `app/tests/__init__.py`
- Create: `jobs/nightly_refresh.py` (placeholder)

- [ ] **Step 1: Write databricks.yml**

```yaml
bundle:
  name: fonterra-mainland-lineage
  git:
    origin_url: https://github.com/wscalioni/fonterra-mainland-lineage
    branch: main

variables:
  warehouse_id:
    description: "Serverless SQL warehouse ID in the target workspace."
    default: "TBD_RUN_databricks_warehouses_list"
  working_schema:
    default: "aw_internal_adpcoe.mainland_lineage_analysis"
  programme_group:
    description: "UC group name for divestment programme users."
    default: "fonterra-divestment-programme"

targets:
  dev:
    mode: development
    default: true
    workspace:
      profile: FONTERRA
      host: https://adb-2351505639777173.13.azuredatabricks.net
      root_path: /Shared/fonterra-mainland-lineage/${bundle.target}
  prod:
    mode: production
    workspace:
      profile: FONTERRA
      host: https://adb-2924922257177540.azuredatabricks.net

resources:
  apps:
    mainland_lineage_app:
      name: "mainland-lineage"
      description: "Fonterra Mainland divestment — lineage explorer for Mike T"
      source_code_path: ./app
      config:
        command: ["python", "app.py"]
        env:
          - name: DATABRICKS_WAREHOUSE_ID
            value: ${var.warehouse_id}
          - name: WORKING_SCHEMA
            value: ${var.working_schema}
      oauth:
        scopes:
          - sql
          - all-apis
      permissions:
        - level: CAN_USE
          group_name: ${var.programme_group}

  jobs:
    mainland_lineage_nightly:
      name: "Mainland Lineage — Nightly Incremental Refresh"
      schedule:
        quartz_cron_expression: "0 0 3 * * ?"
        timezone_id: "Pacific/Auckland"
        pause_status: PAUSED
      tasks:
        - task_key: incremental_refresh
          python_script_task:
            python_file: ./jobs/nightly_refresh.py
            parameters:
              - "--warehouse-id"
              - ${var.warehouse_id}
              - "--working-schema"
              - ${var.working_schema}
          job_cluster_key: refresh_cluster
      job_clusters:
        - job_cluster_key: refresh_cluster
          new_cluster:
            spark_version: "15.4.x-scala2.12"
            node_type_id: Standard_DS3_v2
            num_workers: 1
            spark_conf:
              spark.databricks.cluster.profile: singleNode
      email_notifications:
        on_failure:
          - will.scalioni@databricks.com
```

- [ ] **Step 2: Write app/requirements.txt**

```
dash==2.18.2
dash-cytoscape==1.0.2
dash-bootstrap-components==1.7.1
pandas==2.2.3
databricks-sdk==0.40.0
gunicorn==23.0.0
```

- [ ] **Step 3: Write minimal app/app.py**

```python
"""Dash entry point for the Mainland Lineage app."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
from dash import html

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Mainland Lineage",
)

app.layout = dbc.Container(
    [
        dbc.NavbarSimple(brand="Mainland Lineage", color="dark", dark=True),
        dash.page_container,
    ],
    fluid=True,
)

if __name__ == "__main__":
    port = int(os.environ.get("DATABRICKS_APP_PORT", "8050"))
    app.run(host="0.0.0.0", port=port, debug=False)
```

- [ ] **Step 4: Create empty package markers**

```bash
touch app/lib/__init__.py app/pages/__init__.py app/tests/__init__.py
```

- [ ] **Step 5: Write placeholder jobs/nightly_refresh.py**

```python
"""Placeholder — replaced in Task 14."""
import argparse

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--warehouse-id", required=True)
    p.add_argument("--working-schema", required=True)
    args = p.parse_args()
    print(f"placeholder: warehouse={args.warehouse_id} schema={args.working_schema}")
```

- [ ] **Step 6: Validate the bundle**

```bash
databricks bundle validate --target dev --var="warehouse_id=$DEV_WAREHOUSE_ID"
```

Expected: `Validation OK!`

- [ ] **Step 7: Commit**

```bash
git add databricks.yml app/ jobs/
git commit -m "feat: scaffold DABs bundle with Dash app + nightly job stubs"
```

---

## Task 4: app/lib/colours.py — re-export CATEGORY_COLOUR

**Files:**
- Create: `app/lib/colours.py`

- [ ] **Step 1: Inspect the canonical source**

```bash
grep -A 12 "CATEGORY_COLOUR" lib/visualize.py | head -20
```

Confirm the dict matches the table in `CLAUDE_CODE_PROMPT.md`.

- [ ] **Step 2: Write app/lib/colours.py**

```python
"""Re-export CATEGORY_COLOUR from lib/visualize.py — single source of truth."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.visualize import CATEGORY_COLOUR  # noqa: E402

__all__ = ["CATEGORY_COLOUR"]
```

- [ ] **Step 3: Smoke test the import**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
python -c "from app.lib.colours import CATEGORY_COLOUR; print(sorted(CATEGORY_COLOUR.keys()))"
```

Expected: list of 8 categories.

- [ ] **Step 4: Commit**

```bash
git add app/lib/colours.py
git commit -m "feat(app): re-export CATEGORY_COLOUR from pipeline visualize module"
```

---

## Task 5: app/lib/data_loader.py — Delta read helpers (TDD)

**Files:**
- Create: `app/lib/data_loader.py`
- Create: `app/tests/test_data_loader.py`

- [ ] **Step 1: Write the failing test**

`app/tests/test_data_loader.py`:

```python
"""Unit tests for data_loader. SDK is mocked — no live Databricks calls."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.lib import data_loader


def _mock_client(rows, schema):
    client = MagicMock()
    response = MagicMock()
    response.status.state.value = "SUCCEEDED"
    response.result.data_array = rows
    cols = []
    for name in schema:
        c = MagicMock()
        c.name = name
        cols.append(c)
    response.manifest.schema.columns = cols
    client.statement_execution.execute_statement.return_value = response
    return client


def test_load_classified_returns_dataframe_with_expected_columns():
    rows = [
        ["fdp_prd_x.s.t1", "MAINLAND_TAGGED", "fdp_prd_x", "s", "t1", True, 1, 2,
         0, 0, 0, 0, 0, 0, 1.0, 0.5, 0.7],
    ]
    cols = [
        "node", "category", "catalog", "schema", "table_name", "is_seed",
        "n_upstream", "n_downstream",
        "sep_business_entity", "sep_location", "sep_employee",
        "sep_customer", "sep_material", "sep_sales_org",
        "mainland_in_ratio", "mainland_out_ratio", "bridge_score",
    ]
    client = _mock_client(rows, cols)
    df = data_loader.load_classified(client, warehouse_id="W", working_schema="s.m")
    assert list(df.columns) == cols
    assert len(df) == 1
    assert df.iloc[0]["category"] == "MAINLAND_TAGGED"


def test_load_pinchpoints_filters_to_co_mingled():
    rows = [["n1", "CO_MINGLED_UPSTREAM"], ["n2", "CO_MINGLED_DOWNSTREAM"]]
    client = _mock_client(rows, ["node", "category"])
    df = data_loader.load_pinchpoints(client, warehouse_id="W", working_schema="s.m")
    assert len(df) == 2
    sql = client.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "CO_MINGLED_UPSTREAM" in sql and "CO_MINGLED_DOWNSTREAM" in sql


def test_failed_statement_raises():
    client = MagicMock()
    response = MagicMock()
    response.status.state.value = "FAILED"
    response.status.error.message = "permission denied"
    client.statement_execution.execute_statement.return_value = response
    with pytest.raises(RuntimeError, match="permission denied"):
        data_loader.load_classified(client, warehouse_id="W", working_schema="s.m")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
.venv/bin/pip install -r app/requirements.txt pytest
.venv/bin/pytest app/tests/test_data_loader.py -v
```

Expected: FAIL — module not implemented.

- [ ] **Step 3: Implement app/lib/data_loader.py**

```python
"""Delta table read helpers for the Mainland Lineage app."""
from __future__ import annotations

import pandas as pd
from databricks.sdk import WorkspaceClient


def _execute(client: WorkspaceClient, *, warehouse_id: str, statement: str) -> pd.DataFrame:
    resp = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=statement, wait_timeout="50s",
    )
    state = resp.status.state.value if hasattr(resp.status.state, "value") else resp.status.state
    if state != "SUCCEEDED":
        msg = getattr(resp.status, "error", None)
        msg = msg.message if msg else f"state={state}"
        raise RuntimeError(f"SQL failed: {msg}")
    rows = resp.result.data_array or []
    cols = [c.name for c in resp.manifest.schema.columns]
    return pd.DataFrame(rows, columns=cols)


def load_classified(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id,
                    statement=f"SELECT * FROM {working_schema}.mainland_lineage_classified")


def load_pinchpoints(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id, statement=(
        f"SELECT * FROM {working_schema}.mainland_lineage_classified "
        f"WHERE category IN ('CO_MINGLED_UPSTREAM', 'CO_MINGLED_DOWNSTREAM')"
    ))


def load_edges(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id,
                    statement=f"SELECT * FROM {working_schema}.mainland_lineage_edges")


def load_pinchpoint_status(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id,
                    statement=f"SELECT * FROM {working_schema}.pinchpoint_status")


def load_workspace_identities(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id,
                    statement=f"SELECT * FROM {working_schema}.workspace_identities")


def load_refresh_control(client, *, warehouse_id, working_schema):
    return _execute(client, warehouse_id=warehouse_id, statement=(
        f"SELECT * FROM {working_schema}.refresh_control "
        f"ORDER BY run_completed DESC LIMIT 50"
    ))


def load_neighbourhood(client, *, warehouse_id, working_schema, node, hops=2):
    if hops < 1 or hops > 5:
        raise ValueError("hops must be in [1, 5]")
    safe = node.replace("'", "''")
    statement = f"""
        WITH RECURSIVE walk (n, hop) AS (
          SELECT '{safe}' AS n, 0 AS hop
          UNION ALL
          SELECT CASE WHEN e.src_full_name = w.n THEN e.tgt_full_name
                      ELSE e.src_full_name END AS n,
                 w.hop + 1 AS hop
          FROM walk w
          JOIN {working_schema}.mainland_lineage_edges e
            ON (e.src_full_name = w.n OR e.tgt_full_name = w.n)
          WHERE w.hop < {hops}
        )
        SELECT DISTINCT e.src_full_name, e.tgt_full_name, e.edge_count
        FROM {working_schema}.mainland_lineage_edges e
        WHERE e.src_full_name IN (SELECT n FROM walk)
           OR e.tgt_full_name IN (SELECT n FROM walk)
    """
    return _execute(client, warehouse_id=warehouse_id, statement=statement)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest app/tests/test_data_loader.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/lib/data_loader.py app/tests/test_data_loader.py
git commit -m "feat(app): add data_loader with mocked SDK tests"
```

---

## Task 6: SQL bootstrap — status tables + status_writer (TDD)

**Files:**
- Create: `sql/00_status_tables.sql`
- Create: `app/lib/status_writer.py`
- Create: `app/tests/test_status_writer.py`

- [ ] **Step 1: Write sql/00_status_tables.sql**

```sql
-- Run once per workspace, as a user with CREATE on the working schema. Idempotent.

CREATE TABLE IF NOT EXISTS aw_internal_adpcoe.mainland_lineage_analysis.pinchpoint_status (
  node          STRING,
  status        STRING,
  notes         STRING,
  updated_by    STRING,
  updated_at    TIMESTAMP
) USING DELTA
COMMENT 'Mike T separation status per CO_MINGLED node.';

CREATE TABLE IF NOT EXISTS aw_internal_adpcoe.mainland_lineage_analysis.workspace_identities (
  workspace_id    STRING,
  display_name    STRING,
  notes           STRING,
  updated_by      STRING,
  updated_at      TIMESTAMP
) USING DELTA
COMMENT 'Annotations for workspace IDs in system.access.table_lineage.';

CREATE TABLE IF NOT EXISTS aw_internal_adpcoe.mainland_lineage_analysis.refresh_control (
  run_id         STRING,
  run_type       STRING,
  watermark_ts   TIMESTAMP,
  new_edges      INT,
  new_nodes      INT,
  affected_nodes INT,
  run_started    TIMESTAMP,
  run_completed  TIMESTAMP,
  status         STRING
) USING DELTA
COMMENT 'Lakeflow nightly refresh log.';
```

- [ ] **Step 2: Write the failing test for status_writer**

`app/tests/test_status_writer.py`:

```python
from unittest.mock import MagicMock
import pytest
from app.lib import status_writer


def _ok_client():
    c = MagicMock()
    r = MagicMock()
    r.status.state.value = "SUCCEEDED"
    c.statement_execution.execute_statement.return_value = r
    return c


def test_set_pinchpoint_status_uses_merge_and_quotes_inputs():
    c = _ok_client()
    status_writer.set_pinchpoint_status(
        c, warehouse_id="W", working_schema="s.m",
        node="cat.sch.tbl", status="UC Tagged", notes="needs review",
        updated_by="mike@fonterra.com",
    )
    sql = c.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "MERGE INTO s.m.pinchpoint_status" in sql
    assert "'cat.sch.tbl'" in sql
    assert "'UC Tagged'" in sql
    assert "'mike@fonterra.com'" in sql


def test_set_pinchpoint_status_rejects_unknown_status():
    c = _ok_client()
    with pytest.raises(ValueError, match="status must be one of"):
        status_writer.set_pinchpoint_status(
            c, warehouse_id="W", working_schema="s.m",
            node="x", status="LOL", notes="", updated_by="m@f.com",
        )


def test_set_pinchpoint_status_escapes_single_quotes_in_notes():
    c = _ok_client()
    status_writer.set_pinchpoint_status(
        c, warehouse_id="W", working_schema="s.m",
        node="x", status="Pending", notes="mike's note",
        updated_by="m@f.com",
    )
    sql = c.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "mike''s note" in sql
```

- [ ] **Step 3: Run test to verify it fails**

```bash
.venv/bin/pytest app/tests/test_status_writer.py -v
```

Expected: FAIL.

- [ ] **Step 4: Implement app/lib/status_writer.py**

```python
"""Status write-back helpers — pinchpoint_status, workspace_identities."""
from __future__ import annotations

from databricks.sdk import WorkspaceClient


VALID_STATUSES = {"Pending", "UC Tagged", "Row Filter Applied", "Attested", "Cleared"}


def _q(s: str) -> str:
    return s.replace("'", "''")


def _exec(client, *, warehouse_id, statement):
    resp = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=statement, wait_timeout="50s",
    )
    state = resp.status.state.value if hasattr(resp.status.state, "value") else resp.status.state
    if state != "SUCCEEDED":
        msg = getattr(resp.status, "error", None)
        msg = msg.message if msg else f"state={state}"
        raise RuntimeError(f"SQL failed: {msg}")


def set_pinchpoint_status(client, *, warehouse_id, working_schema,
                           node, status, notes, updated_by):
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
    statement = f"""
        MERGE INTO {working_schema}.pinchpoint_status t
        USING (SELECT '{_q(node)}' AS node) s
          ON t.node = s.node
        WHEN MATCHED THEN UPDATE SET
          status = '{_q(status)}',
          notes = '{_q(notes)}',
          updated_by = '{_q(updated_by)}',
          updated_at = current_timestamp()
        WHEN NOT MATCHED THEN INSERT
          (node, status, notes, updated_by, updated_at)
          VALUES ('{_q(node)}', '{_q(status)}', '{_q(notes)}',
                  '{_q(updated_by)}', current_timestamp())
    """
    _exec(client, warehouse_id=warehouse_id, statement=statement)


def set_workspace_identity(client, *, warehouse_id, working_schema,
                            workspace_id, display_name, notes, updated_by):
    statement = f"""
        MERGE INTO {working_schema}.workspace_identities t
        USING (SELECT '{_q(workspace_id)}' AS workspace_id) s
          ON t.workspace_id = s.workspace_id
        WHEN MATCHED THEN UPDATE SET
          display_name = '{_q(display_name)}',
          notes = '{_q(notes)}',
          updated_by = '{_q(updated_by)}',
          updated_at = current_timestamp()
        WHEN NOT MATCHED THEN INSERT
          (workspace_id, display_name, notes, updated_by, updated_at)
          VALUES ('{_q(workspace_id)}', '{_q(display_name)}', '{_q(notes)}',
                  '{_q(updated_by)}', current_timestamp())
    """
    _exec(client, warehouse_id=warehouse_id, statement=statement)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/pytest app/tests/test_status_writer.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Run the bootstrap SQL against dev workspace**

```bash
for stmt in $(awk 'BEGIN{RS=";"} /CREATE/' sql/00_status_tables.sql); do
  databricks api post /api/2.0/sql/statements --profile FONTERRA \
    --json "$(jq -nc --arg s "$stmt" --arg w "$DEV_WAREHOUSE_ID" \
       '{warehouse_id:$w, statement:$s, wait_timeout:"30s"}')"
done
```

Expected: each call returns `"state":"SUCCEEDED"`. If permissions fail, defer to Task 15.

- [ ] **Step 7: Commit**

```bash
git add sql/00_status_tables.sql app/lib/status_writer.py app/tests/test_status_writer.py
git commit -m "feat: add status tables bootstrap + status_writer with MERGE-based write-back"
```

---

## Task 7: app/lib/cytoscape_builder.py — DataFrame to elements (TDD)

**Files:**
- Create: `app/lib/cytoscape_builder.py`
- Create: `app/tests/test_cytoscape_builder.py`

- [ ] **Step 1: Write the failing test**

`app/tests/test_cytoscape_builder.py`:

```python
import pandas as pd
from app.lib import cytoscape_builder as cb


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest app/tests/test_cytoscape_builder.py -v
```

Expected: FAIL.

- [ ] **Step 3: Implement app/lib/cytoscape_builder.py**

```python
"""Transforms classified-nodes + edges DataFrames into cytoscape elements."""
from __future__ import annotations

import pandas as pd

from app.lib.colours import CATEGORY_COLOUR

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest app/tests/test_cytoscape_builder.py -v
```

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/lib/cytoscape_builder.py app/tests/test_cytoscape_builder.py
git commit -m "feat(app): cytoscape element builder with size formula + pinch class"
```

---

## Task 8: app/pages/programme_dashboard.py — homepage

**Files:**
- Create: `app/pages/programme_dashboard.py`

- [ ] **Step 1: Implement the dashboard**

```python
"""Programme dashboard — homepage. KPI cards + schema heat map."""
from __future__ import annotations

import os
from datetime import date

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, callback, dcc, html
from databricks.sdk import WorkspaceClient

from app.lib import data_loader

dash.register_page(__name__, path="/", name="Dashboard")

TSA_EXIT = date(2028, 4, 1)
WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")


def _kpi_card(title, value, sub=""):
    return dbc.Card(
        dbc.CardBody([
            html.Div(title, className="text-muted small"),
            html.Div(value, className="display-6"),
            html.Div(sub, className="small"),
        ]),
        className="mb-2",
    )


def layout():
    return html.Div([
        html.H2("Mainland divestment — programme dashboard", className="mt-3"),
        html.Div(id="dashboard-error", className="text-danger"),
        dbc.Row(id="kpi-row", className="g-2 mt-2"),
        html.H4("Schemas by entanglement risk", className="mt-4"),
        dcc.Loading(html.Div(id="schema-heat")),
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
        return [], [], "DATABRICKS_WAREHOUSE_ID not set."
    try:
        client = WorkspaceClient()
        classified = data_loader.load_classified(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        status = data_loader.load_pinchpoint_status(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        refresh = data_loader.load_refresh_control(client, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
    except RuntimeError as e:
        return [], [], f"Permission or query error: {e}"

    pinchpoints = classified[classified["category"].str.startswith("CO_MINGLED")]
    cleared = status[status["status"] == "Cleared"] if not status.empty else pd.DataFrame()
    schemas_with_pinch = pinchpoints["schema"].nunique()
    days_to_exit = (TSA_EXIT - date.today()).days
    last_refresh = refresh["run_completed"].iloc[0] if not refresh.empty else "never"

    cards = [
        dbc.Col(_kpi_card("Mainland-touching objects", f"{len(classified):,}", "")),
        dbc.Col(_kpi_card("Pinch-points", f"{len(cleared)} / {len(pinchpoints)}", "cleared")),
        dbc.Col(_kpi_card("Active schemas", f"{schemas_with_pinch}", "with CO_MINGLED nodes")),
        dbc.Col(_kpi_card("TSA exit", "2028-04-01", f"{days_to_exit} days remaining")),
        dbc.Col(_kpi_card("Last refresh", str(last_refresh), "")),
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

    def _colour(row):
        if row["n_pinch"] > 0:
            return "#D32F2F"
        if row["n_source"] + row["n_sink"] > 0:
            return "#FFA000"
        return "#4CAF50"

    tiles = [
        html.Div(
            f"{r['schema']} ({r['n']})",
            title=f"{r['n_pinch']} pinch / {r['n_source']} source / {r['n_sink']} sink",
            style={
                "background": _colour(r),
                "color": "white",
                "padding": "6px 8px",
                "borderRadius": "4px",
                "fontSize": "0.85em",
                "display": "inline-block",
                "margin": "2px",
            },
        )
        for _, r in schema_summary.iterrows()
    ]
    return cards, html.Div(tiles), ""
```

- [ ] **Step 2: Smoke test locally**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
export DATABRICKS_CONFIG_PROFILE=FONTERRA
export DATABRICKS_WAREHOUSE_ID=$DEV_WAREHOUSE_ID
export WORKING_SCHEMA=aw_internal_adpcoe.mainland_lineage_analysis
.venv/bin/python app/app.py
```

Open `http://localhost:8050/` in Arc browser. Expected: KPI cards + heat map render within ~2s. If permission errors appear, defer to Task 15 then retry.

- [ ] **Step 3: Commit**

```bash
git add app/pages/programme_dashboard.py
git commit -m "feat(app): programme dashboard with KPI cards + schema heat map"
```

---

## Task 9: app/pages/pinchpoint_tracker.py — 49-row table with status write-back

**Files:**
- Create: `app/pages/pinchpoint_tracker.py`

- [ ] **Step 1: Implement the page**

```python
"""Pinch-point tracker — 49 CO_MINGLED nodes with status write-back."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dash_table, dcc, html
from databricks.sdk import WorkspaceClient

from app.lib import data_loader, status_writer

dash.register_page(__name__, path="/pinchpoints", name="Pinch-points")

WAREHOUSE = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
SCHEMA = os.environ.get("WORKING_SCHEMA", "aw_internal_adpcoe.mainland_lineage_analysis")
STATUS_OPTIONS = ["Pending", "UC Tagged", "Row Filter Applied", "Attested", "Cleared"]


def layout():
    return html.Div([
        html.H2("Pinch-point tracker", className="mt-3"),
        html.P("49 CO_MINGLED nodes — set separation status to track progress."),
        html.Div(id="pp-progress", className="mb-3"),
        html.Div(id="pp-error", className="text-danger"),
        dash_table.DataTable(
            id="pp-table",
            columns=[
                {"name": "Node", "id": "node"},
                {"name": "Category", "id": "category"},
                {"name": "Schema", "id": "schema"},
                {"name": "Up/Dn", "id": "ud"},
                {"name": "Status", "id": "status", "presentation": "dropdown", "editable": True},
                {"name": "Notes", "id": "notes", "editable": True},
            ],
            dropdown={"status": {"options": [{"label": s, "value": s} for s in STATUS_OPTIONS]}},
            data=[],
            style_cell={"fontSize": "0.85em", "fontFamily": "system-ui"},
            style_data_conditional=[
                {"if": {"filter_query": "{status} = 'Cleared'"}, "backgroundColor": "#E8F5E9"},
                {"if": {"filter_query": "{category} = 'CO_MINGLED_DOWNSTREAM'"},
                 "borderLeft": "4px solid #D32F2F"},
                {"if": {"filter_query": "{category} = 'CO_MINGLED_UPSTREAM'"},
                 "borderLeft": "4px solid #E65100"},
            ],
        ),
        dcc.Store(id="pp-user", data={"email": "unknown@databricks.com"}),
        dcc.Interval(id="pp-load-once", n_intervals=0, max_intervals=1, interval=100),
    ])


def _build_rows(classified, status):
    pp = classified[classified["category"].str.startswith("CO_MINGLED")].copy()
    pp = pp.merge(status[["node", "status", "notes"]], on="node", how="left")
    pp["status"] = pp["status"].fillna("Pending")
    pp["notes"] = pp["notes"].fillna("")
    pp["ud"] = pp["n_upstream"].astype(str) + " / " + pp["n_downstream"].astype(str)
    return pp[["node", "category", "schema", "ud", "status", "notes"]].to_dict("records")


@callback(
    Output("pp-table", "data"),
    Output("pp-progress", "children"),
    Output("pp-error", "children"),
    Input("pp-load-once", "n_intervals"),
)
def _initial(_n):
    if not WAREHOUSE:
        return [], "", "DATABRICKS_WAREHOUSE_ID not set."
    try:
        c = WorkspaceClient()
        cls = data_loader.load_classified(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
        st = data_loader.load_pinchpoint_status(c, warehouse_id=WAREHOUSE, working_schema=SCHEMA)
    except RuntimeError as e:
        return [], "", str(e)
    rows = _build_rows(cls, st)
    cleared = sum(1 for r in rows if r["status"] == "Cleared")
    bar = dbc.Progress(value=100 * cleared / max(1, len(rows)),
                       label=f"{cleared} / {len(rows)} cleared",
                       style={"height": "24px"})
    return rows, bar, ""


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
        c = WorkspaceClient()
        for r in diffs:
            status_writer.set_pinchpoint_status(
                c, warehouse_id=WAREHOUSE, working_schema=SCHEMA,
                node=r["node"], status=r["status"], notes=r["notes"] or "",
                updated_by=user.get("email", "unknown"),
            )
    except (RuntimeError, ValueError) as e:
        return f"Save failed: {e}"
    return ""
```

- [ ] **Step 2: Smoke test**

Reload `http://localhost:8050/pinchpoints`. Expected: 49 rows, progress bar, status dropdown editable. Edit a status, refresh, verify persisted.

- [ ] **Step 3: Verify persistence**

```bash
databricks api post /api/2.0/sql/statements --profile FONTERRA \
  --json "$(jq -nc --arg w "$DEV_WAREHOUSE_ID" \
     '{warehouse_id:$w, statement:"SELECT node, status, updated_at FROM aw_internal_adpcoe.mainland_lineage_analysis.pinchpoint_status ORDER BY updated_at DESC LIMIT 5", wait_timeout:"30s"}')"
```

Expected: most recent row matches your edit.

- [ ] **Step 4: Commit**

```bash
git add app/pages/pinchpoint_tracker.py
git commit -m "feat(app): pinch-point tracker with editable status + write-back"
```

---

## Task 10: app/pages/graph_explorer.py — Cytoscape graph

**Files:**
- Create: `app/pages/graph_explorer.py`

- [ ] **Step 1: Implement the page**

```python
"""Graph explorer — full UC lineage spider-web with filters + focus mode."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import Input, Output, State, callback, dcc, html
from databricks.sdk import WorkspaceClient

from app.lib import cytoscape_builder, data_loader

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
    return dbc.Row([
        dbc.Col([
            html.H5("Filters", className="mt-3"),
            dbc.Checklist(
                id="g-cat",
                options=[{"label": c, "value": c} for c in CATEGORIES],
                value=["CO_MINGLED_UPSTREAM", "CO_MINGLED_DOWNSTREAM"],
                inline=False,
            ),
            html.Hr(),
            dbc.Switch(id="g-pinch-only", label="Pinch-points + 1-hop only", value=True),
            dbc.Switch(id="g-hide-edges", label="Hide edges (faster)", value=False),
            html.Hr(),
            html.Div(id="g-info", className="small"),
        ], width=3),
        dbc.Col([
            cyto.Cytoscape(
                id="g-graph",
                elements=[],
                layout={"name": "dagre", "rankDir": "LR"},
                stylesheet=cytoscape_builder.CYTOSCAPE_STYLESHEET,
                style={"height": "85vh", "width": "100%"},
            ),
            dcc.Interval(id="g-load-once", n_intervals=0, max_intervals=1, interval=100),
        ], width=9),
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
        c = WorkspaceClient()
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
        html.Div(html.Strong(data["id"])),
        html.Div(f"{data['category']}"),
        html.Div(f"up={data['n_upstream']} dn={data['n_downstream']} bridge={data['bridge_score']:.2f}"),
    ])
```

- [ ] **Step 2: Smoke test**

Reload `http://localhost:8050/graph`. Expected: pinch-points-only view renders ~150 nodes within 2s. Toggle filters, click a node.

- [ ] **Step 3: Commit**

```bash
git add app/pages/graph_explorer.py
git commit -m "feat(app): cytoscape graph explorer with category filters + node info"
```

---

## Task 11: app/pages/search.py — what touches this table?

**Files:**
- Create: `app/pages/search.py`

- [ ] **Step 1: Implement the page**

```python
"""Search — what touches this table? Submit a node, get a 2-hop subgraph."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import Input, Output, State, callback, html
from databricks.sdk import WorkspaceClient

from app.lib import cytoscape_builder, data_loader

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
        c = WorkspaceClient()
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
```

- [ ] **Step 2: Smoke test**

`http://localhost:8050/search` — search for `fdp_prd_std_internal.std_internal_sapentbw.company_code_s4__zs4compco`. Expected: 2-hop subgraph renders, summary shows CO_MINGLED_DOWNSTREAM with upstream=1 downstream=23.

- [ ] **Step 3: Commit**

```bash
git add app/pages/search.py
git commit -m "feat(app): search page with N-hop neighbourhood subgraph"
```

---

## Task 12: app/pages/workspace_identity.py — annotate the 10 workspace IDs

**Files:**
- Create: `app/pages/workspace_identity.py`

- [ ] **Step 1: Implement the page**

```python
"""Workspace identity panel — annotate the 10 workspace IDs from Phase 0."""
from __future__ import annotations

import os

import dash
from dash import Input, Output, State, callback, dash_table, dcc, html
from databricks.sdk import WorkspaceClient

from app.lib import data_loader, status_writer

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
```

- [ ] **Step 2: Smoke test**

`http://localhost:8050/workspaces` — expected: 10 rows. Edit display_name on `6179018390893845` to "Production", confirm persisted.

- [ ] **Step 3: Commit**

```bash
git add app/pages/workspace_identity.py
git commit -m "feat(app): workspace identity panel with annotation write-back"
```

---

## Task 13: app/pages/weekly_digest.py — diff vs 7 days ago

**Files:**
- Create: `app/pages/weekly_digest.py`

- [ ] **Step 1: Implement the page**

```python
"""Weekly digest — what changed in the last 7 days."""
from __future__ import annotations

import os

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html
from databricks.sdk import WorkspaceClient

from app.lib import data_loader

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
        c = WorkspaceClient()
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
```

- [ ] **Step 2: Smoke test**

`http://localhost:8050/digest` — expected: three columns. Until the nightly job has run, "new nodes" and "newly CO_MINGLED" show "none".

- [ ] **Step 3: Commit**

```bash
git add app/pages/weekly_digest.py
git commit -m "feat(app): weekly digest page (new nodes, new pinch-points, cleared)"
```

---

## Task 14: jobs/nightly_refresh.py — incremental watermark + MERGE (TDD)

**Files:**
- Modify: `jobs/nightly_refresh.py` (replaces placeholder)
- Create: `jobs/tests/__init__.py`
- Create: `jobs/tests/test_nightly_refresh.py`
- Modify: `sql/00_status_tables.sql` (append v_classify_node_logic)

- [ ] **Step 1: Write the failing test**

`jobs/tests/test_nightly_refresh.py`:

```python
"""Tests for SQL composition in the nightly refresh script."""
from __future__ import annotations

from unittest.mock import MagicMock

from jobs import nightly_refresh as nr


def _ok_client():
    c = MagicMock()
    r = MagicMock()
    r.status.state.value = "SUCCEEDED"
    r.result.data_array = [["2026-05-07 12:00:00"]]
    col = MagicMock()
    col.name = "watermark"
    r.manifest.schema.columns = [col]
    c.statement_execution.execute_statement.return_value = r
    return c


def test_read_watermark_uses_max_last_seen():
    c = _ok_client()
    nr.read_watermark(c, warehouse_id="W", working_schema="s.m")
    sql = c.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "max(last_seen)" in sql.lower()
    assert "s.m.mainland_lineage_edges" in sql


def test_merge_new_edges_query_uses_correct_schema():
    sql = nr.build_merge_edges_sql(working_schema="s.m", watermark_iso="2026-05-07T00:00:00")
    assert "MERGE INTO s.m.mainland_lineage_edges" in sql
    assert "system.access.table_lineage" in sql
    assert "event_time > TIMESTAMP '2026-05-07T00:00:00'" in sql
    assert "WHEN NOT MATCHED THEN INSERT" in sql


def test_classify_affected_filters_to_subset():
    sql = nr.build_classify_affected_sql(
        working_schema="s.m",
        affected_csv="'a.b.c','d.e.f'",
    )
    assert "WHERE full_name IN ('a.b.c','d.e.f')" in sql
    assert "MERGE INTO s.m.mainland_lineage_classified" in sql


def test_run_logs_to_refresh_control(monkeypatch):
    c = _ok_client()
    monkeypatch.setattr(nr, "read_watermark", lambda *a, **k: "2026-05-07T00:00:00")
    monkeypatch.setattr(nr, "merge_new_edges", lambda *a, **k: 5)
    monkeypatch.setattr(nr, "insert_new_nodes", lambda *a, **k: 2)
    monkeypatch.setattr(nr, "classify_affected", lambda *a, **k: 7)
    nr.run(c, warehouse_id="W", working_schema="s.m")
    statements = [
        call.kwargs["statement"]
        for call in c.statement_execution.execute_statement.call_args_list
    ]
    assert any("refresh_control" in s and "INSERT" in s.upper() for s in statements)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest jobs/tests/test_nightly_refresh.py -v
```

Expected: FAIL.

- [ ] **Step 3: Replace jobs/nightly_refresh.py**

```python
"""Nightly incremental refresh — watermark + MERGE.

Reads max(last_seen) from mainland_lineage_edges as the watermark, fetches
new lineage events from system.access.table_lineage, merges them into edges,
inserts any new nodes, and re-classifies the affected node set.

Full BFS hop structure is NOT recomputed here. New edges are tagged with
hop=NULL, direction='incremental' so they are visible to classification but
excluded from the per-hop BFS statistics. Run a full BFS reset monthly via
lib/lineage_walker.py.
"""
from __future__ import annotations

import argparse
import uuid
from datetime import datetime, timezone

from databricks.sdk import WorkspaceClient


def _exec(client, *, warehouse_id, statement):
    resp = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id, statement=statement, wait_timeout="50s",
    )
    state = resp.status.state.value if hasattr(resp.status.state, "value") else resp.status.state
    if state != "SUCCEEDED":
        msg = getattr(resp.status, "error", None)
        msg = msg.message if msg else f"state={state}"
        raise RuntimeError(f"SQL failed: {msg}")
    return resp


def read_watermark(client, *, warehouse_id, working_schema):
    sql = f"SELECT max(last_seen) AS watermark FROM {working_schema}.mainland_lineage_edges"
    resp = _exec(client, warehouse_id=warehouse_id, statement=sql)
    rows = resp.result.data_array or []
    if not rows or rows[0][0] is None:
        return "2000-01-01T00:00:00"
    return str(rows[0][0]).replace(" ", "T")


def build_merge_edges_sql(*, working_schema, watermark_iso):
    return f"""
        MERGE INTO {working_schema}.mainland_lineage_edges t
        USING (
          SELECT
            source_table_full_name AS src_full_name,
            target_table_full_name AS tgt_full_name,
            count(*) AS edge_count_inc,
            max(event_time) AS last_seen
          FROM system.access.table_lineage
          WHERE event_time > TIMESTAMP '{watermark_iso}'
            AND source_table_full_name IS NOT NULL
            AND target_table_full_name IS NOT NULL
            AND source_table_full_name != target_table_full_name
          GROUP BY source_table_full_name, target_table_full_name
        ) s
        ON t.src_full_name = s.src_full_name AND t.tgt_full_name = s.tgt_full_name
        WHEN MATCHED THEN UPDATE SET
          edge_count = t.edge_count + s.edge_count_inc,
          last_seen = greatest(t.last_seen, s.last_seen)
        WHEN NOT MATCHED THEN INSERT
          (src_full_name, tgt_full_name, edge_count, hop, direction, first_seen, last_seen)
          VALUES (s.src_full_name, s.tgt_full_name, s.edge_count_inc, NULL, 'incremental', s.last_seen, s.last_seen)
    """


def merge_new_edges(client, *, warehouse_id, working_schema, watermark_iso):
    sql = build_merge_edges_sql(working_schema=working_schema, watermark_iso=watermark_iso)
    _exec(client, warehouse_id=warehouse_id, statement=sql)
    count_sql = (
        f"SELECT count(*) FROM {working_schema}.mainland_lineage_edges "
        f"WHERE direction = 'incremental' AND last_seen > TIMESTAMP '{watermark_iso}'"
    )
    resp = _exec(client, warehouse_id=warehouse_id, statement=count_sql)
    return int(resp.result.data_array[0][0])


def insert_new_nodes(client, *, warehouse_id, working_schema, watermark_iso):
    sql = f"""
        INSERT INTO {working_schema}.mainland_lineage_nodes
        SELECT DISTINCT n AS full_name, -1 AS first_seen_hop, 'incremental' AS first_seen_dir, FALSE AS is_seed
        FROM (
          SELECT src_full_name AS n FROM {working_schema}.mainland_lineage_edges
          WHERE last_seen > TIMESTAMP '{watermark_iso}'
          UNION
          SELECT tgt_full_name AS n FROM {working_schema}.mainland_lineage_edges
          WHERE last_seen > TIMESTAMP '{watermark_iso}'
        )
        WHERE n NOT IN (SELECT full_name FROM {working_schema}.mainland_lineage_nodes)
    """
    _exec(client, warehouse_id=warehouse_id, statement=sql)
    count_sql = (
        f"SELECT count(*) FROM {working_schema}.mainland_lineage_nodes "
        f"WHERE first_seen_dir = 'incremental'"
    )
    resp = _exec(client, warehouse_id=warehouse_id, statement=count_sql)
    return int(resp.result.data_array[0][0])


def build_classify_affected_sql(*, working_schema, affected_csv):
    """Re-classify a subset by filtering v_classify_node_logic.

    affected_csv must be a quoted, comma-separated list of node names,
    e.g. "'a.b.c','d.e.f'".
    """
    return f"""
        MERGE INTO {working_schema}.mainland_lineage_classified t
        USING (
          SELECT *
          FROM {working_schema}.v_classify_node_logic
          WHERE full_name IN ({affected_csv})
        ) s
        ON t.node = s.full_name
        WHEN MATCHED THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """


def classify_affected(client, *, warehouse_id, working_schema, watermark_iso):
    affected_sql = f"""
        SELECT DISTINCT full_name FROM (
          SELECT src_full_name AS full_name FROM {working_schema}.mainland_lineage_edges
          WHERE last_seen > TIMESTAMP '{watermark_iso}'
          UNION
          SELECT tgt_full_name AS full_name FROM {working_schema}.mainland_lineage_edges
          WHERE last_seen > TIMESTAMP '{watermark_iso}'
        )
    """
    resp = _exec(client, warehouse_id=warehouse_id, statement=affected_sql)
    rows = resp.result.data_array or []
    if not rows:
        return 0
    affected = [r[0] for r in rows]
    quoted = ",".join("'" + n.replace("'", "''") + "'" for n in affected)
    sql = build_classify_affected_sql(working_schema=working_schema, affected_csv=quoted)
    _exec(client, warehouse_id=warehouse_id, statement=sql)
    return len(affected)


def log_run(client, *, warehouse_id, working_schema, run_id, watermark_iso,
            new_edges, new_nodes, affected, started, completed, status):
    sql = f"""
        INSERT INTO {working_schema}.refresh_control
          (run_id, run_type, watermark_ts, new_edges, new_nodes, affected_nodes,
           run_started, run_completed, status)
        VALUES
          ('{run_id}', 'incremental', TIMESTAMP '{watermark_iso}',
           {new_edges}, {new_nodes}, {affected},
           TIMESTAMP '{started}', TIMESTAMP '{completed}', '{status}')
    """
    _exec(client, warehouse_id=warehouse_id, statement=sql)


def run(client, *, warehouse_id, working_schema):
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = str(uuid.uuid4())
    try:
        watermark = read_watermark(client, warehouse_id=warehouse_id, working_schema=working_schema)
        new_edges = merge_new_edges(client, warehouse_id=warehouse_id,
                                    working_schema=working_schema, watermark_iso=watermark)
        new_nodes = insert_new_nodes(client, warehouse_id=warehouse_id,
                                      working_schema=working_schema, watermark_iso=watermark)
        affected = classify_affected(client, warehouse_id=warehouse_id,
                                      working_schema=working_schema, watermark_iso=watermark)
        completed = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log_run(client, warehouse_id=warehouse_id, working_schema=working_schema,
                run_id=run_id, watermark_iso=watermark, new_edges=new_edges,
                new_nodes=new_nodes, affected=affected,
                started=started, completed=completed, status="SUCCEEDED")
    except Exception as e:
        completed = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log_run(client, warehouse_id=warehouse_id, working_schema=working_schema,
                run_id=run_id, watermark_iso="2000-01-01T00:00:00", new_edges=0,
                new_nodes=0, affected=0,
                started=started, completed=completed, status=f"FAILED: {e}")
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--warehouse-id", required=True)
    p.add_argument("--working-schema", required=True)
    args = p.parse_args()
    run(WorkspaceClient(), warehouse_id=args.warehouse_id, working_schema=args.working_schema)
```

- [ ] **Step 4: Append v_classify_node_logic placeholder to sql/00_status_tables.sql**

Append to `sql/00_status_tables.sql`:

```sql
-- View used by the nightly refresh to re-classify a subset of nodes.
-- IMPORTANT: the SELECT body below is a placeholder. Before running the
-- nightly job, replace its body with the canonical classification logic
-- from queries/03_classify_nodes.sql so it computes from edges + seed
-- (NOT from the materialised classified table — that creates a circular
-- dependency).
CREATE OR REPLACE VIEW aw_internal_adpcoe.mainland_lineage_analysis.v_classify_node_logic AS
SELECT
  node       AS full_name,
  category, catalog, schema, table_name, is_seed,
  n_upstream, n_downstream,
  sep_business_entity, sep_location, sep_employee,
  sep_customer, sep_material, sep_sales_org,
  mainland_in_ratio, mainland_out_ratio, bridge_score
FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_classified;
```

- [ ] **Step 5: Inline the canonical classification logic into the view**

Open `queries/03_classify_nodes.sql`. Identify the SELECT body that produces the classified rows from `mainland_lineage_edges` + `mainland_lineage_seed`. Replace the placeholder body in `sql/00_status_tables.sql` with that SELECT. Re-run Step 6 of Task 6 to recreate the view. Verify:

```bash
databricks api post /api/2.0/sql/statements --profile FONTERRA \
  --json "$(jq -nc --arg w "$DEV_WAREHOUSE_ID" \
     '{warehouse_id:$w, statement:"SELECT count(*) FROM aw_internal_adpcoe.mainland_lineage_analysis.v_classify_node_logic", wait_timeout:"30s"}')"
```

Expected: count near 3,949 (matches `mainland_lineage_classified`).

- [ ] **Step 6: Run unit tests**

```bash
.venv/bin/pytest jobs/tests/test_nightly_refresh.py -v
```

Expected: 4 PASS.

- [ ] **Step 7: Manual job dry run**

```bash
cd /Users/will.scalioni/git/fonterra-mainland-lineage
DATABRICKS_CONFIG_PROFILE=FONTERRA \
  .venv/bin/python jobs/nightly_refresh.py \
    --warehouse-id $DEV_WAREHOUSE_ID \
    --working-schema aw_internal_adpcoe.mainland_lineage_analysis
```

Expected: completes within ~2 min on first run; subsequent runs <30s. Check `refresh_control` for SUCCEEDED row.

- [ ] **Step 8: Commit**

```bash
git add jobs/nightly_refresh.py jobs/tests/ sql/00_status_tables.sql
git commit -m "feat: incremental nightly refresh with watermark+MERGE and v_classify_node_logic"
```

---

## Task 15: One-off setup — UC grants + warehouse permissions

**Files:**
- Create: `sql/01_uc_grants.sql`

- [ ] **Step 1: Write sql/01_uc_grants.sql**

```sql
-- Run once per workspace, by a user with MANAGE on the working schema.

GRANT USE CATALOG ON CATALOG aw_internal_adpcoe
  TO `fonterra-divestment-programme`;

GRANT USE SCHEMA ON SCHEMA aw_internal_adpcoe.mainland_lineage_analysis
  TO `fonterra-divestment-programme`;

GRANT SELECT ON ALL TABLES IN SCHEMA aw_internal_adpcoe.mainland_lineage_analysis
  TO `fonterra-divestment-programme`;

GRANT SELECT ON ALL VIEWS IN SCHEMA aw_internal_adpcoe.mainland_lineage_analysis
  TO `fonterra-divestment-programme`;

GRANT MODIFY ON TABLE aw_internal_adpcoe.mainland_lineage_analysis.pinchpoint_status
  TO `fonterra-divestment-programme`;

GRANT MODIFY ON TABLE aw_internal_adpcoe.mainland_lineage_analysis.workspace_identities
  TO `fonterra-divestment-programme`;

GRANT SELECT ON TABLE system.access.table_lineage
  TO `fonterra-divestment-programme`;
```

- [ ] **Step 2: Confirm the UC group exists**

```bash
databricks account groups list --output json | jq '.[] | select(.display_name | test("divestment"; "i")) | {id, display_name}'
```

If no group matches, ask Satya/Aneesh for the correct UC group name and update both `sql/01_uc_grants.sql` and `databricks.yml` `var.programme_group`.

- [ ] **Step 3: Apply the grants**

Each `GRANT` is a separate statement — the SQL Statement Execution API accepts only one per call:

```bash
while IFS= read -r stmt; do
  [ -z "$stmt" ] && continue
  databricks api post /api/2.0/sql/statements --profile FONTERRA \
    --json "$(jq -nc --arg s "$stmt" --arg w "$DEV_WAREHOUSE_ID" \
       '{warehouse_id:$w, statement:$s, wait_timeout:"30s"}')"
done < <(awk 'BEGIN{RS=";"} /GRANT/' sql/01_uc_grants.sql)
```

- [ ] **Step 4: Apply warehouse CAN_USE**

```bash
databricks warehouses set-permissions $DEV_WAREHOUSE_ID \
  --json '{"access_control_list": [{"group_name": "fonterra-divestment-programme", "permission_level": "CAN_USE"}]}' \
  --profile FONTERRA \
  --host https://adb-2351505639777173.13.azuredatabricks.net
```

- [ ] **Step 5: Commit**

```bash
git add sql/01_uc_grants.sql
git commit -m "chore: add UC + warehouse grants script for the programme group"
```

---

## Task 16: Bundle deploy — first push to Fonterra dev

- [ ] **Step 1: Validate**

```bash
databricks bundle validate --target dev --var="warehouse_id=$DEV_WAREHOUSE_ID"
```

Expected: `Validation OK!`

- [ ] **Step 2: Deploy**

```bash
databricks bundle deploy --target dev --var="warehouse_id=$DEV_WAREHOUSE_ID"
```

Expected: bundle uploads, app + job created. Output prints the app URL — capture it.

- [ ] **Step 3: List resources**

```bash
databricks apps list --profile FONTERRA \
  --host https://adb-2351505639777173.13.azuredatabricks.net | grep mainland
databricks jobs list --profile FONTERRA \
  --host https://adb-2351505639777173.13.azuredatabricks.net \
  --output json | jq '.jobs[] | select(.settings.name | test("Mainland"))'
```

Expected: both resources present.

- [ ] **Step 4: Open the app and walk through every page in Arc browser**

```
/                     KPI cards + heat map render
/pinchpoints          49 rows, edit one cell, refresh, persisted
/graph                pinch-only view, ~150 nodes, click a node
/search               2-hop subgraph for a known pinch-point
/workspaces           10 rows, edit a name, persisted
/digest               three columns, populated after manual job run
```

- [ ] **Step 5: Trigger the nightly job manually**

```bash
databricks bundle run mainland_lineage_nightly --target dev
```

Expected: SUCCEEDED row in `refresh_control`.

- [ ] **Step 6: Unpause the schedule**

Edit `databricks.yml` Task 3 — change `pause_status: PAUSED` to `pause_status: UNPAUSED`. Re-deploy:

```bash
databricks bundle deploy --target dev --var="warehouse_id=$DEV_WAREHOUSE_ID"
git add databricks.yml
git commit -m "chore: unpause nightly refresh schedule after first successful manual run"
git push origin main
```

- [ ] **Step 7: Final commit**

```bash
git status
```

Expected: clean tree.

---

## Self-Review

Coverage vs CLAUDE_CODE_PROMPT.md:

| Spec section | Plan task |
|---|---|
| GitHub repo + Git-backed deployment | Task 1 + Task 3 (databricks.yml `git` block) |
| Discover dev warehouse | Task 2 |
| Create the app (first deploy) | Task 16 |
| UC grants | Task 15 |
| SQL warehouse access | Task 15 |
| OBO auth — what to do / not do | Conventions + every page using `WorkspaceClient()` |
| Framework (Dash + dash-cytoscape) | Task 3 (requirements.txt) + Task 10 |
| Repo + bundle structure | Task 3 |
| Graph visualiser — sidebar filters, node interaction, visual encoding, performance | Task 10 |
| Incremental refresh — watermark, schema, MERGE, classification | Task 14 |
| Feature 1 Pinch-point tracker | Task 9 |
| Feature 2 Programme dashboard + heat map | Task 8 |
| Feature 3 Search | Task 11 |
| Feature 4 Workspace identity | Task 12 |
| Feature 5 Weekly digest | Task 13 |
| Don't break existing pipeline | Task 4 only re-exports; pipeline files untouched |
| No hardcoded tokens | All `WorkspaceClient()`-based |
| Colours match Confluence | Task 4 enforces single source of truth |

Placeholder check: the only intentional fill-in is the `v_classify_node_logic` SELECT body (Task 14 Step 4 + Step 5). The placeholder body is wrong on purpose (creates circular dependency) and the engineer is told to inline the body of `queries/03_classify_nodes.sql`. This is unavoidable — the canonical logic lives in the SQL file and must be read in context.

Type/name consistency: `set_pinchpoint_status` / `load_pinchpoint_status` / `pinchpoint_status` consistent. `mainland_lineage_*` table names consistent. `WORKING_SCHEMA` env var consistent across pages.
