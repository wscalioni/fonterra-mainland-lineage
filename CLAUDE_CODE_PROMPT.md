# Prompt: Fonterra Mainland Lineage — Databricks App + UX Uplift

## Project context (read this before doing anything else)

This repo (`fonterra-mainland-lineage`) is a UC lineage spider-web analysis for **Fonterra's Mainland divestment**. When Fonterra spins off the Mainland dairy business, every data object shared between Mainland and the retained Fonterra business ("commingled") must be identified, tagged, row-filtered, and attested before the TSA exit on **2028-04-01**.

We have already run a 4-phase pipeline:

- **Phase 1**: 2,952 Mainland candidate objects discovered across 3 channels.
- **Phase 2**: BFS lineage walk — 3,954 edges, 3,949 nodes across 10 workspaces.
- **Phase 3**: Per-node classification. The critical finding: **49 CO_MINGLED pinch-points** — nodes that genuinely bridge Mainland and retained data. These are the actionable engineering scope.
- **Phase 4**: Quantification — per-schema rollups, cross-catalog flow, separator coverage.

### Key files to read before coding

```
analysis/03-phase3-classification.md    # Full classification results + pinch-point clusters
outputs/classified_nodes.csv            # 3,949 rows: node, category, catalog, schema, table_name,
                                        #   is_seed, n_upstream, n_downstream,
                                        #   sep_business_entity, sep_location, sep_employee,
                                        #   sep_customer, sep_material, sep_sales_org,
                                        #   mainland_in_ratio, mainland_out_ratio, bridge_score
outputs/edges.csv                       # 3,954 rows: src_full_name, tgt_full_name, edge_count, hop, direction
outputs/entanglement_pinchpoints.csv    # 49 rows: the actionable pinch-point list with DSR + cluster
outputs/per_schema_rollup.csv          # 69 rows: production-only schema rollup
lib/visualize.py                        # Existing colour scheme + graph-building logic (reuse CATEGORY_COLOUR)
lib/lineage_walker.py                   # BFS walker — read to understand the Delta table schema
```

### Databricks environment

- **CLI profile**: `FONTERRA`
- **Sandbox workspace**: `adb-2924922257177540`
- **Serverless warehouse**: `406253829ca12fd5`
- **Working schema**: `aw_internal_adpcoe.mainland_lineage_analysis`
- **Key Delta tables** (in working schema):
  - `mainland_lineage_seed` — 2,952 candidate objects
  - `mainland_lineage_edges` — (src_full_name, tgt_full_name, edge_count, hop, direction, first_seen, last_seen)
  - `mainland_lineage_nodes` — (full_name, first_seen_hop, first_seen_dir, is_seed)
  - `mainland_lineage_classified` — classification output (same columns as classified_nodes.csv)

### Node categories (reuse these exact colours from `lib/visualize.py`)

| Category | Colour | Meaning |
|---|---|---|
| MAINLAND_TAGGED | #4CAF50 (green) | In the seed — authoritative Mainland object |
| MAINLAND_INTERIOR | #2E7D32 (dark green) | Every neighbour is Mainland |
| MAINLAND_SOURCE | #1976D2 (blue) | Pure Mainland feeder, no observed upstream |
| MAINLAND_SINK | #0288D1 (cyan) | Pure Mainland consumer |
| CO_MINGLED_UPSTREAM | #E65100 (deep orange) | ⚠ Pinch-point: receives from both sides |
| CO_MINGLED_DOWNSTREAM | #D32F2F (red) | ⚠ Pinch-point: feeds both sides |
| RETAINED_OR_INDIRECT | #9E9E9E (grey) | Walked but no Mainland neighbour |
| UNCLASSIFIED | #BDBDBD (light grey) | Edge cases |

---

## What we're building

Convert this repo into a **Databricks App** — a persistent, interactive web application deployed on Databricks serverless compute — that lets **Mike T** (programme manager, non-technical) navigate the full lineage graph, track separation progress, and understand the divestment's data engineering scope. The primary consumer is business + programme management, not engineers.

The current UX (a pyvis `.html` blob and static Graphviz PNGs) is unreadable at 3,949 nodes. We need a proper graph explorer with filtering, focus mode, and business-friendly dashboards.

---

## Pre-requisite: GitHub repo + Git-backed deployment

The app must be deployed from **Git source**, not from the workspace file system. This is required so that the Fonterra dev workspace (`adb-2351505639777173`) can pull code from a repo that is accessible from their environment.

### Step 1 — Create the GitHub repo

Create a new **public** repo under the personal GitHub account **`wscalioni`**:

```bash
gh repo create wscalioni/fonterra-mainland-lineage \
  --public \
  --description "UC lineage spider-web + divestment app — Fonterra Mainland" \
  --source . \
  --push
```

Then set the remote and push:

```bash
git remote set-url origin https://github.com/wscalioni/fonterra-mainland-lineage.git
git push -u origin main
```

Add a `.gitignore` entry for secrets and outputs that should not be committed:

```
.env
.databrickscfg
outputs/*.html   # large files — keep PNGs/SVGs, exclude the pyvis HTML blob
__pycache__/
.venv/
```

### Step 2 — Connect the repo to the Fonterra dev workspace

In the Databricks UI for `https://adb-2351505639777173.13.azuredatabricks.net`:

1. Go to **Workspace → Settings → Linked Git repositories** (or **Source control → Git repos** depending on the UI version).
2. Add the repo: `https://github.com/wscalioni/fonterra-mainland-lineage`
3. Use a **GitHub Personal Access Token (PAT)** scoped to `repo` (read). Will generates this from his GitHub account and stores it as a Databricks secret:
   ```bash
   databricks secrets create-scope fonterra-lineage --profile FONTERRA
   databricks secrets put-secret fonterra-lineage github_pat --string-value <PAT> --profile FONTERRA
   ```

### Step 3 — Configure DABs to deploy from Git

Add a `workspace` source reference in `databricks.yml` so the bundle knows to pull from Git rather than upload local files:

```yaml
# Add inside the `dev` target, under `workspace:`
workspace:
  profile: FONTERRA
  host: https://adb-2351505639777173.13.azuredatabricks.net
  root_path: /Shared/fonterra-mainland-lineage/${bundle.target}
```

And add a `git` block at the bundle root level so the bundle can reference the Git commit SHA:

```yaml
bundle:
  name: fonterra-mainland-lineage
  git:
    origin_url: https://github.com/wscalioni/fonterra-mainland-lineage
    branch: main
```

Deploy from a developer machine (Will's) using:

```bash
databricks bundle deploy --target dev
```

This uploads the bundle state and instructs the workspace to sync from the Git repo. From that point, updates to `main` are picked up on the next `bundle deploy` or can be triggered via a CI push (GitHub Actions → `databricks bundle deploy`).

---

## One-off setup (run once before first deploy)

These steps create the app, grant the right UC privileges, and configure the SQL warehouse — they do not need to repeat on subsequent deploys.

### 1 — Discover the dev warehouse ID

The sandbox warehouse (`406253829ca12fd5`) lives in workspace `2924922257177540`. The dev workspace (`2351505639777173`) has its own warehouses. Before deploying, find the right serverless warehouse ID:

```bash
databricks warehouses list --profile FONTERRA \
  --output json | jq '.[] | {id, name, warehouse_type, state}'
```

Copy the ID of the serverless warehouse, then set it as a bundle variable override:

```bash
# In ~/.databricks/bundle/fonterra-mainland-lineage/dev.vars (gitignored) or pass inline:
databricks bundle deploy --target dev --var="warehouse_id=<actual-id>"
```

Or update the `databricks.yml` default value once confirmed.

### 2 — Create the app (first deploy)

```bash
databricks bundle deploy --target dev
```

On first run this creates the Databricks App resource in the dev workspace. Subsequent runs update it in-place (no recreation).

Verify the app was created:

```bash
databricks apps list --profile FONTERRA | grep mainland
```

### 3 — Grant UC privileges

Run once in the dev workspace, as a user with `MANAGE` on the working schema:

```sql
-- Read access for all programme users
GRANT USE CATALOG ON CATALOG aw_internal_adpcoe
  TO `fonterra-divestment-programme`;

GRANT USE SCHEMA ON SCHEMA aw_internal_adpcoe.mainland_lineage_analysis
  TO `fonterra-divestment-programme`;

GRANT SELECT ON ALL TABLES IN SCHEMA aw_internal_adpcoe.mainland_lineage_analysis
  TO `fonterra-divestment-programme`;

-- Write access for the status write-back tables (Mike T needs this)
GRANT MODIFY ON TABLE aw_internal_adpcoe.mainland_lineage_analysis.pinchpoint_status
  TO `fonterra-divestment-programme`;

GRANT MODIFY ON TABLE aw_internal_adpcoe.mainland_lineage_analysis.workspace_identities
  TO `fonterra-divestment-programme`;

-- Refresh control is read-only for app users; only the job SP writes it
GRANT SELECT ON TABLE aw_internal_adpcoe.mainland_lineage_analysis.refresh_control
  TO `fonterra-divestment-programme`;
```

If the status tables don't exist yet, the app's `data_loader.py` should CREATE them on first startup (with `CREATE TABLE IF NOT EXISTS`).

### 4 — Grant SQL warehouse access

```bash
# Grant CAN_USE on the dev warehouse to the programme group
databricks warehouses set-permissions <warehouse-id> \
  --json '{"access_control_list": [{"group_name": "fonterra-divestment-programme", "permission_level": "CAN_USE"}]}' \
  --profile FONTERRA
```

### 5 — OBO auth: what the app code must and must not do

With OBO, the Databricks Apps runtime injects the **logged-in user's OAuth token** into the app process. `WorkspaceClient()` picks this up automatically — no extra code needed.

**Do:**
```python
from databricks.sdk import WorkspaceClient

def get_client() -> WorkspaceClient:
    # Inside a Databricks App, this automatically uses the user's OBO token.
    # No token, no profile, no env var needed — the runtime provides it.
    return WorkspaceClient()
```

**Do not:**
- Hardcode `DATABRICKS_TOKEN` or `DATABRICKS_CLIENT_SECRET` in the app environment.
- Use `subprocess` + `databricks CLI` for data access inside the app (breaks OBO).
- Store a service principal token in any env var that overrides the runtime-injected token.

The app will inherit the logged-in user's UC permissions automatically. If Mike T lacks `SELECT` on a table, the SDK call will fail with a permission error — surface this as a friendly "You don't have access to this data" message in the UI, not a Python traceback.

---

## Part 1 — Build the Databricks App

### Framework choice: Dash + dash-cytoscape

Use **Plotly Dash** with the **`dash-cytoscape`** component. Rationale:
- `dash-cytoscape` is an official Plotly component wrapping Cytoscape.js — the industry standard for data lineage graph UX (used by dbt Cloud, Atlan, OpenMetadata).
- Cytoscape.js handles 3,949 nodes smoothly with GPU-accelerated canvas rendering.
- The `dagre` layout (hierarchical DAG) maps naturally onto the `std → itg → srv` medallion layer structure already in the codebase.
- Dash has native Databricks Apps support (GA as of 2024); deploy with `databricks bundle deploy` (DABs — see bundle structure below).

Do **not** use Streamlit — it lacks a graph component with the interaction model we need (click-to-expand, multi-select, focus neighbourhood).

### Repo + bundle structure

Everything — the app, the nightly job, and any future notebooks — is deployed through a **single Databricks Asset Bundle (DABs)** rooted at the repo. Create `databricks.yml` at the repo root:

```yaml
# databricks.yml  (repo root)
bundle:
  name: fonterra-mainland-lineage

variables:
  warehouse_id:
    description: "Serverless SQL warehouse ID in the target workspace. MUST be discovered per-workspace — do not assume the sandbox value (406253829ca12fd5) works in dev."
    default: "TBD_RUN_databricks_warehouses_list"
  working_schema:
    default: "aw_internal_adpcoe.mainland_lineage_analysis"

targets:
  dev:
    mode: development
    default: true
    workspace:
      profile: FONTERRA
      host: https://adb-2351505639777173.13.azuredatabricks.net   # Fonterra dev workspace (workspace_id=2351505639777173)
      # Note: this workspace_id appears in Phase 0's lineage data as the 4th-largest
      # workspace (1,206,421 events/30d, 5,440 distinct sources) — previously TBD,
      # now confirmed as the Fonterra dev workspace. Update analysis/00-phase0-ground-truth.md.

  prod:
    mode: production
    workspace:
      profile: FONTERRA
      host: https://adb-2924922257177540.azuredatabricks.net   # sandbox — update to prod host when known

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
        # On-Behalf-Of (OBO): app makes Databricks API calls using the logged-in
        # user's delegated OAuth token, not a service-principal token.
        # UC permissions are enforced per-user — Mike T sees only what he's
        # granted. No DATABRICKS_TOKEN env var should be hardcoded; the app
        # runtime injects the user's token automatically.
        scopes:
          - sql           # execute SQL via the warehouse
          - all-apis      # needed for SDK calls (lineage tables, workspace info)
      permissions:
        - level: CAN_USE
          group_name: fonterra-divestment-programme   # adjust to actual UC group

  jobs:
    mainland_lineage_nightly:
      name: "Mainland Lineage — Nightly Incremental Refresh"
      schedule:
        quartz_cron_expression: "0 0 3 * * ?"
        timezone_id: "Pacific/Auckland"
      tasks:
        - task_key: incremental_refresh
          python_script_task:
            python_file: ./jobs/nightly_refresh.py
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

The app source directory (`app/`) contains the Dash code only — no DABs config there:

```
databricks.yml              # Bundle root — single source of truth for deploy
app/
├── app.py                  # Dash app entry point
├── requirements.txt        # dash, dash-cytoscape, dash-bootstrap-components, pandas, databricks-sdk
├── pages/
│   ├── graph_explorer.py   # Main graph view (see Part 2)
│   ├── pinchpoint_tracker.py  # PM-facing tracker (see Part 4)
│   ├── programme_dashboard.py # Executive summary (see Part 4)
│   └── schema_heatmap.py   # Schema-level risk heat map (see Part 4)
└── lib/
    └── data_loader.py      # Reads from Delta tables via databricks-sdk SQL client
jobs/
└── nightly_refresh.py      # Incremental refresh script (see Part 3)
```

Deploy with:
```bash
databricks bundle deploy --target dev     # deploy app + job to dev
databricks bundle deploy --target prod    # promote to prod
databricks bundle run mainland_lineage_nightly   # trigger a manual refresh run
```

For data access inside the app, use `databricks.sdk` with the `StatementExecutionAPI`:
```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()  # picks up auth from the app's service principal
```

The app runs on serverless compute — no cluster needed. Data is served from the Delta tables in `aw_internal_adpcoe.mainland_lineage_analysis`.

---

## Part 2 — Graph visualiser (Cytoscape)

### Layout strategy

Use **`dagre`** layout as the default (requires `cytoscape-dagre` which dash-cytoscape bundles). Configure it as left-to-right (`rankDir: LR`) so the medallion flow reads naturally: `FOREIGN → STD → ITG → SRV`. Fall back to `cose-bilkent` (force-directed) for the "full graph" view where the layer hierarchy is less relevant.

### The graph explorer view must have

1. **Sidebar filters**:
   - Category multi-select (toggle CO_MINGLED on/off, etc.)
   - Catalog multi-select (`fdp_prd_std_internal`, etc.)
   - Schema search (autocomplete text input)
   - "Pinch-points only" toggle — immediately filters to the 49 CO_MINGLED nodes + their 1-hop neighbours
   - "Seed only" toggle — hides walked nodes, shows just the 2,952 discovery candidates

2. **Node interaction**:
   - Click a node → sidebar panel shows: full name, category badge, separator columns, n_upstream, n_downstream, bridge_score, DSR mapping (from entanglement_pinchpoints.csv if CO_MINGLED)
   - "Focus neighbourhood" button → re-renders graph showing only the clicked node + N-hop subgraph (N = 1 or 2, user-selectable)
   - Right-click → "Copy table name to clipboard"

3. **Visual encoding**:
   - Node colour: category (reuse CATEGORY_COLOUR from lib/visualize.py)
   - Node size: proportional to `n_upstream + n_downstream` (capped, same formula as current pyvis: `max(8, min(40, 8 + 2*(n_up+n_dn)**0.6))`)
   - Edge width: proportional to `edge_count`
   - CO_MINGLED nodes get a pulsing border animation in CSS so Mike can spot them instantly

4. **Performance**: For the full 3,949-node view, start with edges hidden and let the user enable them — Cytoscape struggles with 3,954 rendered edges simultaneously. Show edges only in Focus mode or when fewer than 200 nodes are visible.

---

## Part 3 — Incremental Lakeflow refresh

### Problem with the current approach

The current walker (`lib/lineage_walker.py`) does a full `CREATE OR REPLACE TABLE` on every run — it re-reads the entire 90-day `system.access.table_lineage` window. At production scale (18.97M events/30 days in workspace `6179018390893845`), a nightly full re-read is expensive and slow.

### Incremental strategy: watermark + MERGE

`system.access.table_lineage` has an `event_time` TIMESTAMP column. We can maintain a watermark and only process new events each night.

#### Schema addition needed

Add a control table to the working schema:
```sql
CREATE TABLE IF NOT EXISTS aw_internal_adpcoe.mainland_lineage_analysis.refresh_control (
  run_id        STRING,
  run_type      STRING,   -- 'full' or 'incremental'
  watermark_ts  TIMESTAMP,
  new_edges     INT,
  new_nodes     INT,
  affected_nodes INT,
  run_started   TIMESTAMP,
  run_completed TIMESTAMP,
  status        STRING
) USING DELTA
```

#### Nightly incremental job logic (write as `jobs/nightly_refresh.py`)

```
Step 1 — Read watermark
  SELECT max(last_seen) FROM mainland_lineage_edges → watermark_ts

Step 2 — Fetch new lineage events (edges only)
  SELECT src, tgt, count(*) as edge_count, max(event_time) as last_seen
  FROM system.access.table_lineage
  WHERE event_time > watermark_ts
    AND source_table_full_name IS NOT NULL
    AND target_table_full_name IS NOT NULL
    AND source_table_full_name != target_table_full_name
  GROUP BY src, tgt

Step 3 — MERGE new edges into mainland_lineage_edges
  Match on (src_full_name, tgt_full_name).
  On match: increment edge_count, update last_seen.
  On not match: INSERT with hop=NULL, direction='incremental' (distinguishes from BFS-walked edges)

Step 4 — Add new nodes
  INSERT INTO mainland_lineage_nodes
  SELECT DISTINCT src/tgt as full_name, -1 AS first_seen_hop, 'incremental' AS first_seen_dir, FALSE
  FROM new_edges
  LEFT ANTI JOIN mainland_lineage_nodes ON full_name

Step 5 — Re-classify affected nodes
  Collect: all nodes that appear in new_edges (src or tgt) UNION their 1-hop existing neighbours.
  Re-run the classification logic (queries/03_classify_nodes.sql) scoped to this affected_set
  via a WHERE full_name IN (...) filter.
  MERGE results into mainland_lineage_classified.

Step 6 — Update refresh_control
```

Key design decision: **do not re-run the BFS hop structure on incremental runs**. New edges discovered incrementally get `hop=NULL` with `direction='incremental'` — they're included in classification but excluded from the "per-hop" BFS statistics that go in the analysis markdown files. Run a full BFS reset monthly or on-demand.

#### Lakeflow Job definition

The job is declared in `databricks.yml` at the repo root (see Part 1 — bundle structure). No separate job YAML needed. The refresh script itself lives at `jobs/nightly_refresh.py` and is referenced from the bundle.

---

## Part 4 — Features to build (prioritised)

Read `analysis/03-phase3-classification.md` and `outputs/entanglement_pinchpoints.csv` to understand the business context before building these. The primary user is Mike T — programme manager, not an engineer. Every view needs to answer a business question, not just show data.

### Feature 1 — Pinch-point tracker (highest priority)

A table view of all 49 CO_MINGLED nodes. Each row shows:
- Full table name + schema + catalog
- Category badge (UP vs DOWN)
- Separator columns flagged (biz / loc / emp / cust / mat / so)
- DSR reference (from entanglement_pinchpoints.csv)
- **Separation status** (dropdown Mike can set): `Pending → UC Tagged → Row Filter Applied → Attested → Cleared`
- Notes field (free text)

Status + notes are written back to a `pinchpoint_status` Delta table (create it if it doesn't exist):
```sql
CREATE TABLE IF NOT EXISTS aw_internal_adpcoe.mainland_lineage_analysis.pinchpoint_status (
  node          STRING,
  status        STRING,
  notes         STRING,
  updated_by    STRING,
  updated_at    TIMESTAMP
) USING DELTA
```

The tracker shows a progress bar: **X / 49 pinch-points cleared**. This is the single most valuable thing for Mike — it makes the engineering progress visible to the programme.

### Feature 2 — Programme dashboard (homepage)

Executive-level summary card grid:

- **Total Mainland-touching objects**: 3,158 (30.1% of FDP)
- **Pinch-points**: 49 total → X cleared (from pinchpoint_status)
- **Schemas with active entanglement**: count of schemas containing any CO_MINGLED node
- **Days to TSA exit**: countdown from today to 2028-04-01
- **Last refresh**: timestamp from refresh_control
- **New objects since last week**: delta of node count

Below the cards: a **schema-level risk heat map** — a grid of production schemas, coloured red (has CO_MINGLED) / amber (has MAINLAND_SINK or SOURCE) / green (MAINLAND_TAGGED only, clean). This gives Mike an at-a-glance view of which schemas need attention.

### Feature 3 — "What touches this table?" search

A search box Mike can type any table name into. On submit:
- Query `mainland_lineage_edges` for all edges involving that node
- Render a small Cytoscape subgraph (N-hop neighbourhood, default N=2)
- Show: is it CO_MINGLED? What separator columns does it have? What's its separation status?

This replaces the need for Mike to navigate the full 3,949-node spider-web. Most of his questions will be "is table X entangled?" — this answers it in 2 seconds.

### Feature 4 — Workspace identity panel

Phase 0 found 10 workspace IDs in `system.access.table_lineage`. Only 2 are identified (production: `6179018390893845`, sandbox: `2924922257177540`). The other 8 are unknown.

Build a simple admin panel showing the workspace ID → event count table from Phase 0. Allow Mike / Satya to annotate each with a name (e.g., "China Data Hub", "CRMT", "OneEnv"). Store annotations in a `workspace_identities` Delta table. Show the identity names in the graph explorer's edge tooltips.

### Feature 5 — Weekly change digest

On the Programme Dashboard, add a "Changes this week" section showing:
- New nodes added (from `mainland_lineage_nodes.first_seen_hop` where the refresh timestamp is within 7 days)
- Newly CO_MINGLED nodes (the dangerous case — a table that was previously clean is now entangled)
- Nodes that have been cleared (status moved to Cleared in pinchpoint_status)

This replaces the need for Will to manually diff CSVs each week.

---

## Delivery order

Build in this sequence to get value quickly:

1. `app/lib/data_loader.py` — Delta table reader using databricks-sdk (foundation for everything)
2. `app/pages/programme_dashboard.py` — homepage with the card grid + schema heat map
3. `app/pages/pinchpoint_tracker.py` — the 49 CO_MINGLED table with status write-back
4. `app/pages/graph_explorer.py` — Cytoscape graph (start with pinch-points-only view, then expand)
5. `jobs/nightly_refresh.py` + `jobs/nightly_refresh_job.yml` — incremental Lakeflow job
6. `app/pages/schema_heatmap.py` — schema risk heat map (if not already part of dashboard)
7. Features 3–5 (search, workspace panel, weekly digest) — iterative additions

---

## Constraints and decisions

- **Do not break the existing pipeline**. `lib/lineage_walker.py`, `lib/classify.py`, `lib/visualize.py` are kept as-is for re-runs and Confluence publishing. The app reads from the Delta tables they produce.
- **Auth**: Databricks Apps provides SSO automatically. The app's service principal needs READ on `aw_internal_adpcoe.mainland_lineage_analysis` and WRITE on the status/control tables.
- **No hardcoded tokens**. Use `databricks.sdk` with ambient auth.
- **Colours**: reuse `CATEGORY_COLOUR` from `lib/visualize.py` exactly — Confluence PNGs and the app should look identical.
- The app must work for a **non-technical user**. No raw SQL, no JSON blobs, no engineer jargon. Use plain English labels throughout.
