# Phase 0 — Ground truth & metastore visibility

**Date**: 2026-05-07. **Verified by**: Will Scalioni (will.scalioni2@fonterra.com), via FONTERRA CLI profile against sandbox `adb-2924922257177540`, serverless warehouse `406253829ca12fd5`.

## Auth & access

| Check | Result |
|---|---|
| `databricks -p FONTERRA current-user me` | `will.scalioni2@fonterra.com`, active |
| Catalogs visible | 15 (matches Deep Research §6.1) |
| FDP catalogs in scope | `fdp_prd_std_internal`, `fdp_prd_std_confidential`, `fdp_prd_itg_internal`, `fdp_prd_itg_restricted`, `fdp_prd_srv_internal`, `fdp_prd_srv_restricted` |
| FDP dev catalogs | `fdp_dev_itg_internal`, `fdp_dev_std_internal` (out of scope, but visible) |
| Foreign catalogs | `fc_prd_mssql_asudb_internal`, `fc_dev_mssql_asudb_internal` (legacy SQL Server framework — Whakapai retiring) |
| ADP CoE catalogs | `aw_internal_adpcoe`, `aw_restricted_adpcoe` (write target for working schema) |
| Out of scope | `rearc_foreign_exchange_rates_h_10_federal_reserve` (Delta Sharing recipient), `samples`, `system` |

## Critical Phase 0 finding: metastore visibility is metastore-wide

`system.access.table_lineage` from the sandbox sees lineage events from **10 distinct workspace IDs** in the trailing 30 days. The production workspace `6179018390893845` is the largest by event count (18.97M events). Sandbox `2924922257177540` is small by comparison (55,969 events).

| workspace_id | events_30d | distinct_sources | distinct_targets | likely identity |
|---|---|---|---|---|
| 6179018390893845 | 18,969,294 | 10,938 | 8,496 | **Production** (per `mainland.md`) |
| 2849572929806476 | 1,612,965 | 980 | 732 | TBD |
| 847219297868314 | 1,233,940 | 1,168 | 1,039 | TBD |
| 2351505639777173 | 1,206,421 | 5,440 | 2,952 | TBD |
| 2701056834588822 | 185,520 | 1,298 | 626 | TBD |
| 260446927376157 | 169,544 | 2,477 | 1,820 | TBD |
| 2924922257177540 | 55,969 | 423 | 277 | **Sandbox** (current workspace) |
| 218599578558390 | 43,777 | 129 | 89 | TBD |
| 7405617098336858 | 145 | 6 | 6 | likely test/CRMT |
| 463923631839441 | 5 | 4 | 1 | likely test/CRMT |

**Implication**: the spider-web analysis runs metastore-wide, not sandbox-only. The plan's Risk #1 (production-workspace lineage visibility) is resolved favourably. The other 8 workspaces will need a quick identity reconciliation in Phase 1 (Mike, Satya, or `system.access.audit` cross-walk).

## Catalog inventory drift since Deep Research (2026-04-22, ~15 days)

| Catalog | Now (managed / views) | Deep Research §6.1 | Drift |
|---|---|---|---|
| fdp_prd_std_internal | 4,869 / 2,185 | 4,569 / 2,185 | +300 managed, 0 views |
| fdp_prd_std_confidential | 810 / 225 | 802 / 224 | +8 / +1 |
| fdp_prd_itg_internal | 610 / 130 | 591 / 129 | +19 / +1 |
| fdp_prd_itg_restricted | 153 / 162 | 142 / 162 | +11 / 0 |
| fdp_prd_srv_internal | 0 / 1,057 | 0 / 1,018 | 0 / +39 |
| fdp_prd_srv_restricted | 0 / 278 | 0 / 276 | 0 / +2 |

3-5% growth in 15 days, plausible. **Confirms `srv_*` catalogs are still view-only** (zero managed tables) — view-layer separation pattern remains correct.

## Channel A surface — confirmed

The 7 known Mainland surfaces from Deep Research §6.3 are intact:

| Schema | Total objects | Mainland-named | Notes |
|---|---|---|---|
| `fdp_prd_std_internal.std_internal_mainland` | 14 | 14 (whole schema) | Nielsen NZ basket / beverages, no drift |
| `fdp_prd_itg_internal.itg_internal_korora` | 12 | 5 paired | +2 since Deep Research, paired pattern intact |
| `fdp_prd_itg_restricted.itg_restricted_finance` | 164 | 31 P&L views | Confirmed Mainland P&L view inventory |
| `fdp_prd_itg_restricted.itg_restricted_mainland` | 1 | 1 (whole schema) | `au_farm_milksupply` only |
| `fdp_prd_srv_internal.srv_internal_korora` | 4 | 2 | Mainland shipment summary + delivery check |
| `fdp_prd_srv_restricted.srv_restricted_finance` | 53 | 10 fact views | Consol VPCM, regional P&Ls |
| `fdp_prd_srv_restricted.srv_restricted_people_data` | 17 | 6 HR views | Org/HR weekly + monthly |

**Total Channel A confirmed: 14 + 1 + 31 + 5 + 2 + 10 + 6 = 69 directly Mainland-located/named objects.** Drift since Deep Research is ~+2 (Korora pairs).

## Inputs locked in for Phase 1

- Mainland identifier ground truth from Deep Research §5.2 (ART_01–07), §6.3 (existing surface), §6.4 (separator columns 373/721/167/306).
- Working schema: `aw_internal_adpcoe.mainland_lineage_analysis` (write access confirmed via catalog visibility, schema to be created in Phase 2).
- Time window: 90 days (consistent with Deep Research's lineage statistics).
- Hop depth: 5 (from approved plan).

## Open items rolling to Phase 1

- Identify the 8 unknown workspace IDs (likely dev / China Data Hub / CRMT / OneEnv / training).
- Decide whether dev workspace lineage (`fdp_dev_*`) is in scope — initial answer: include for Phase 1 inventory, exclude from final classification (separation policy applies to `_prd` only).
- Confirm `aw_internal_adpcoe.mainland_lineage_analysis` write access at start of Phase 2 (CREATE SCHEMA + CREATE TABLE smoke test).
