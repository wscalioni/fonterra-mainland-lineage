# Phase 2 — Lineage walk

**Date**: 2026-05-07. **Source**: `lib/lineage_walker.py`. **Output**: managed Delta tables in `aw_internal_adpcoe.mainland_lineage_analysis`.

## Configuration

| Parameter | Value |
|---|---|
| Time window | trailing 90 days |
| Max hops | 5 |
| Directions | downstream from seed, upstream from seed (separately tracked) |
| BFS source | `system.access.table_lineage` (metastore-wide, all 10 workspaces) |
| Self-loops | excluded (`source != target`) |
| Edge dedupe | per `(src, tgt)` within a hop, with `event_count`, `min(event_time)`, `max(event_time)` |

## Per-hop results

| direction | hop | new edges | new nodes | cumulative visited |
|---|---:|---:|---:|---:|
| down | 1 | 1,553 | 283 | 3,235 |
| down | 2 | 327 | 163 | 3,398 |
| down | 3 | 95 | 51 | 3,449 |
| down | 4 | 63 | 28 | 3,477 |
| down | 5 | 31 | 20 | 3,497 |
| up | 1 | 1,337 | 137 | 3,634 |
| up | 2 | 200 | 93 | 3,727 |
| up | 3 | 166 | 106 | 3,833 |
| up | 4 | 158 | 92 | 3,925 |
| up | 5 | 24 | 24 | **3,949** |

**Totals**: 3,954 distinct edges (2,069 down + 1,885 up). 3,949 distinct nodes (2,952 seed + 997 walked).

## Observations

- **Frontier collapses fast**, as expected for a real-world DAG anchored to dense source schemas. Down hops 4-5 added only 94 edges combined. Up hops 4-5 added 182 edges.
- **Down walk added 545 new nodes** beyond the seed — these are the consumers of Mainland data (Integrated/Serving views, downstream apps).
- **Up walk added 452 new nodes** — these are sources contributing to the seed (Raw-layer parquet files, foreign catalogs, ad-hoc tables).
- **Cross-direction overlap is small** (down + up new = 997, hop totals show 545 + 452 = 997, no overlap). Means the seed sits cleanly between source feeders and downstream consumers; very little cross-walking.
- **Sanity vs Deep Research §6.2**: Deep Research counted ~920 distinct sapanzecc downstream tables / 90 days. Our 1,553 hop-1-down edges from a ~2,952-table seed (most of which IS sapanzecc + jde + apac) gives a similar order of magnitude with broader coverage.

## Working tables

| Table | Row count | Purpose |
|---|---:|---|
| `mainland_lineage_seed` | 2,952 | 3-channel discovery output |
| `mainland_lineage_edges` | 3,954 | (src, tgt, edge_count, hop, direction, first_seen, last_seen) |
| `mainland_lineage_nodes` | 3,949 | (full_name, first_seen_hop, first_seen_dir, is_seed) |

## Limitations

- **Lineage gaps**: `system.access.table_lineage` only captures lineage from SQL queries Databricks observed. ADF JDBC writes, external orchestration, and Lakeflow Connect ingestion paths may be invisible. Cross-reference with `system.lakeflow.jobs` (Phase 4) and Will's planned Terraform estate snapshot (item #2 on the ASAP list).
- **Time window cutoff**: 90 days. A pipeline that runs monthly may legitimately not appear in our window. Quarterly/SAP refresh jobs (e.g., MDG full reload) are at risk of being missed.
- **Self-write loops** are excluded — these would otherwise dominate edge counts on tables that MERGE into themselves (SCD pattern). Trade-off: misses the legitimate "table merges into itself from staging" signal, but keeps the spider-web readable.

## Next: Phase 3

Classification per node using the `mainland_lineage_classified` view (see `queries/03_classify_nodes.sql`):

- Counts of upstream / downstream neighbours, distinguishing Mainland-tagged (in seed) from non-Mainland.
- `mainland_in_ratio`, `mainland_out_ratio`, `bridge_score`.
- Categories: MAINLAND_TAGGED, MAINLAND_INTERIOR, CO_MINGLED_UPSTREAM, CO_MINGLED_DOWNSTREAM, MAINLAND_SOURCE, MAINLAND_SINK, RETAINED_OR_INDIRECT, UNCLASSIFIED.
- Separator-column flags per node from `system.information_schema.columns`.
