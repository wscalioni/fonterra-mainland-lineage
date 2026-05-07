# Phase 1 — Discovery: Mainland candidate seed set

**Date**: 2026-05-07. **Source**: `queries/01_mainland_candidates.sql`. **Output**: `outputs/mainland_candidates.csv` (2,952 rows).

## Result summary

**2,952 candidates** identified across three channels. Confidence split: 2,130 HIGH / 822 MEDIUM.

### By channel

| Channel | Count | Definition | Confidence |
|---|---|---|---|
| A — known Mainland surfaces (Deep Research §6.3) | 91 | Whole-schema Mainland (`std_internal_mainland`, `itg_restricted_mainland`) + Mainland-named views in Korora and `restricted_finance`/`restricted_people_data` | HIGH |
| B — keyword search | 75 | Names matching `mainland`, `mld`, `kapiti`, `galaxy`, `fbnz`, `fbau`, `fonterra_brands_(nz\|au)` outside Channel A schemas | MEDIUM |
| C — high-density source schemas | 2,786 | All tables in `std_internal_sapanzecc` (99 % Mainland), `std_internal_jde` (95 %), `std_internal_apac_malaysia`, `std_internal_apac_vietnam` | HIGH (sapanzecc/jde) / MEDIUM (apac) |

### By catalog × confidence

| Catalog | HIGH | MEDIUM | Total |
|---|---:|---:|---:|
| fdp_dev_itg_internal | 7 | 8 | 15 |
| fdp_dev_std_internal | 1,067 | 235 | 1,302 |
| **fdp_prd_itg_internal** | **5** | **7** | **12** |
| **fdp_prd_itg_restricted** | **32** | **1** | **33** |
| **fdp_prd_srv_internal** | **2** | **11** | **13** |
| **fdp_prd_srv_restricted** | **16** | **0** | **16** |
| **fdp_prd_std_internal** | **1,001** | **560** | **1,561** |

**Production seed set**: 1,635 objects across the six FDP prod catalogs. Dev catalogs (1,317) are kept for inventory completeness but excluded from the Phase-3 separation classification — separation policy applies to production only.

## Channel B value-add (75 keyword hits outside Channel A)

Channel B picked up **8 schemas not enumerated in Deep Research §6.2** that contain Mainland-named tables, indicating ad-hoc or app-specific Mainland separation patterns:

| Schema | Hits | Notes |
|---|---:|---|
| `std_internal_sapanzapo` (prd + dev) | 15 | **SAP ANZ APO** (Advanced Planning & Optimization) — not in Deep Research §6.2. Adds a new high-density source candidate for Phase 2. |
| `itg_internal_inventory` (prd + dev) | 12 | Inventory ITG schema with Mainland-named tables. App-specific separation pattern. |
| `srv_internal_inventory` | 7 | SRV-layer Mainland inventory views. |
| `std_internal_sapanzbw` (prd + dev) | 12 | **SAP ANZ BW** (Business Warehouse) — already on the high-risk apps register but not in Deep Research §6.2 sources. |
| `std_internal_nova` (prd + dev) | 7 | Schema "nova" with Mainland tables, identity TBD. |
| `std_internal_manual_dunnhumby` (prd + dev) | 4 | Manually loaded Dunnhumby (consumer panel) data — Mainland slice. |
| `std_internal_manual_mainland` (dev) | 2 | Manual Mainland load schema. |
| `std_internal_fsa` (prd + dev) | 4 | "FSA" — likely Farm Source Asia. |
| `std_internal_scv` (dev) | 2 | "SCV" — likely Single Customer View. |
| `srv_internal_energy_and_utilities` | 2 | Mainland-named utility view. |

**Recommendation for Phase 2**: extend Channel C with `std_internal_sapanzapo` (HIGH) and `std_internal_sapanzbw` (HIGH) as Mainland-relevant ANZ source schemas. Done in Phase 2 walker config rather than re-running discovery.

## Multi-channel overlap

62 objects matched more than one channel (61 are A+B, 1 is C+B). The A+B overlap is exactly the Korora `*_mainland` paired tables — picked up by both whole-schema-Mainland (none) and keyword-name (yes). Conflict-resolution rule (HIGH > MEDIUM, A > C > B) keeps these classified under Channel A.

## Confidence model

| Confidence | Channels | Phase-3 treatment |
|---|---|---|
| HIGH | A; C: sapanzecc, jde | Treat as Mainland-touching unless retained-row-count says otherwise. |
| MEDIUM | B; C: apac_malaysia, apac_vietnam | Treat as candidate; rely on Phase-2 lineage and Phase-3 row-level evidence to confirm. |

## What this is **not**

The candidate set is a *superset* — the goal is no false-negatives at the Discovery stage. Many Channel C tables (especially the ~1,000 in `std_internal_sapanzecc`) are Mainland-relevant but will only carry Mainland records once the company-code / plant filter is applied. Phase 2 lineage walk fans out from this superset; Phase 3 classification narrows it via the entanglement-scoring model.

## Next: Phase 2

With the seed staged, the lineage walk runs metastore-wide on `system.access.table_lineage` over the trailing 90 days, max depth 5, both directions. Working schema `aw_internal_adpcoe.mainland_lineage_analysis` will materialise:

- `mainland_lineage_seed` — the 2,952 candidates from Phase 1.
- `mainland_lineage_nodes` — every distinct node touched in the walk.
- `mainland_lineage_edges` — every edge, with hop, direction, edge_count.
- `mainland_lineage_jobs` — writing-job context from `system.lakeflow.jobs`.
