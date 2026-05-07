# fonterra-mainland-lineage

UC lineage spider-web analysis for Fonterra's Mainland divestment data separation.

**Status**: Phase 0 (in progress, started 2026-05-07).
**Customer**: Fonterra. **Project**: Mainland divestment. **UCO**: pending creation.
**Confluence parent**: [Mainland Divestment - Data Separation - Fonterra](https://databricks.atlassian.net/wiki/spaces/FE/pages/6249414690).
**Source design doc**: [Deep Research (2026-04-22)](https://databricks.atlassian.net/wiki/spaces/FE/pages/6256951298) §10 Task #1.

## Purpose

Layer onto the Deep Research's UC scan with an executable lineage spider-web. Produces:

- The Mainland candidate inventory (3-channel discovery).
- The 90-day lineage walk (recursive CTE, max-depth 5, both directions, metastore-wide).
- Per-node entanglement classification against the three-separator model.
- Top-N pinch-point inventory for the architecture options paper.
- Single Confluence subpage under `6249414690`, embedded Graphviz PNG.

## Layout

```
analysis/                Markdown source of truth (uc-lineage-spiderweb.md).
notebooks/               Phase notebooks (00 setup → 05 visualize).
queries/                 SQL files used by the notebooks.
outputs/                 CSVs, graph artefacts (.html, .png, .svg).
lib/                     Python helpers (lineage walker, classifier, confluence publisher).
```

## Auth

`databricks -p FONTERRA ...` against sandbox `adb-2924922257177540`. Token-based (PAT in `~/.databrickscfg`). Serverless warehouse `406253829ca12fd5`.

## Running

Each phase notebook is idempotent and re-runnable. Working schema: `aw_internal_adpcoe.mainland_lineage_analysis` (managed). Disposable.

## Refresh cadence

Re-run weekly until TSA exit (2028-04-01), or on demand when Mike's commingled-app register lands and after each material UC tagging push.
