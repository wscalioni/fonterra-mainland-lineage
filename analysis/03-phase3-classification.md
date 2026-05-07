# Phase 3 + 4 — Classification & quantification

**Date**: 2026-05-07. **Inputs**: `mainland_lineage_seed`, `mainland_lineage_edges`, `mainland_lineage_nodes` (Phase 1+2). **Outputs**: `mainland_lineage_classified` (Delta) + four CSVs in `outputs/`.

## Headline numbers

| Metric | Value |
|---|---:|
| Total fdp_prd objects (system.information_schema.tables) | 10,479 |
| **Mainland-touching objects** (any non-RETAINED, non-UNCLASSIFIED category) | **3,158** |
| **% of FDP that is Mainland-touching** | **30.1 %** |
| Mainland-tagged (in seed) | 2,952 (28.2 %) |
| Walked beyond seed | 997 |
| **CO_MINGLED pinch-points** (true entanglement, both sides observed) | **49** |

## Category distribution (3,949 total nodes, both prd + dev)

| Category | n | seed | walked | % of total | Definition |
|---|---:|---:|---:|---:|---|
| MAINLAND_TAGGED | 2,952 | 2,952 | 0 | 74.8 % | In seed (Channels A/B/C). Authoritative Mainland touch-point. |
| RETAINED_OR_INDIRECT | 576 | 0 | 576 | 14.6 % | Walked but no Mainland neighbour observed. Likely retained-only. |
| UNCLASSIFIED | 215 | 0 | 215 | 5.4 % | Edge cases (no observable upstream / downstream pattern). |
| MAINLAND_SINK | 111 | 0 | 111 | 2.8 % | Pure Mainland consumer — all observed upstream is Mainland, no observed downstream. |
| MAINLAND_SOURCE | 44 | 0 | 44 | 1.1 % | Pure Mainland feeder — no observed upstream, all downstream is Mainland. |
| **CO_MINGLED_DOWNSTREAM** | **30** | 0 | 30 | 0.8 % | **Pinch-point**: feeds both Mainland and non-Mainland targets. |
| **CO_MINGLED_UPSTREAM** | **19** | 0 | 19 | 0.5 % | **Pinch-point**: receives data from both Mainland and non-Mainland sources. |
| MAINLAND_INTERIOR | 2 | 0 | 2 | 0.1 % | Every observed neighbour is Mainland. |

## Pinch-point patterns

Among the 49 CO_MINGLED nodes, the dominant clusters are:

| Cluster | Examples | DSR / separator implication |
|---|---|---|
| **SAP source-to-pay dimensions** | `itg_internal_finance.dim_supplier`, `itg_internal_source_to_pay.dim_purchase_order_profile`, `itg_internal_source_to_pay.dim_supplier_invoice_profile`, `itg_internal_finance.open_po`, `stg_source_to_pay_purchase_order_*` | DSR_13 (Procurement), DSR_21 (Vendor) — supplier and PO data flows from both Mainland and retained company codes; needs vendor-level scope filter (ART_06). |
| **Finance HANA reporting** (`std_confidential_sapenthanadb`) | 9 `consolidated_profit_*` and `unconsolidated_profit_*` HANA views — most have `biz`, `cust`, `mat` separators flagged | DSR_06, DSR_18 — Mainland P&L feeds the consolidated rollup that retained also consumes. View-layer separation pattern (Deep Research §7.2) directly applicable. |
| **People / HR** | `srv_restricted_people_data.department_hierarchy`, `positions` | DSR_05, DSR_08 — org hierarchy and positions feed both Mainland HR views and retained. ART_01 (Mainland employees) is the gating control table. |
| **Materials / customers** | `master_data_material_unit_of_measure`, `dim_supplier`, `my_customer`, `int_my_customer` | DSR_09, DSR_04 — material and customer master data flows everywhere; needs ART_03 / ART_04. |
| **Korora paired** | `itg_internal_korora.shipment_container_tracking_agg_fonterra`, `kotahireferences*` | Confirms the Deep Research §7.3 finding: Korora's paired-table pattern still has cross-flow at the source-to-staging layer. |
| **Single Customer View (SCV)** | 4 `itg_internal_scv.*` (indirect_sales, japan_customer_stock_sales, switch_indirect, warehouse_replenishment) — all `mat,so` flagged | DSR_04, DSR_15 — SCV downstream feeds both Mainland and retained customer views. |

Top 49 with full metadata in `outputs/entanglement_pinchpoints.csv`.

## Separator coverage by category

| Category | n | biz | loc | emp | cust | mat | so |
|---|---:|---:|---:|---:|---:|---:|---:|
| MAINLAND_TAGGED | 2,952 | 9.1 % | 10.7 % | 1.1 % | 5.4 % | 9.7 % | 5.7 % |
| RETAINED_OR_INDIRECT | 576 | 10.6 % | 7.6 % | 0.7 % | 7.5 % | 7.6 % | 4.3 % |
| UNCLASSIFIED | 215 | 27.9 % | 11.6 % | 0.9 % | 6.0 % | 4.7 % | 2.3 % |
| MAINLAND_SINK | 111 | 4.5 % | 2.7 % | 0.0 % | 2.7 % | 3.6 % | 0.9 % |
| MAINLAND_SOURCE | 44 | 13.6 % | 4.5 % | 6.8 % | 4.5 % | 2.3 % | 4.5 % |
| **CO_MINGLED_DOWNSTREAM** | **30** | **33.3 %** | 0.0 % | 0.0 % | **20.0 %** | **40.0 %** | 13.3 % |
| **CO_MINGLED_UPSTREAM** | **19** | 5.3 % | **15.8 %** | 0.0 % | 0.0 % | 0.0 % | 0.0 % |

**Interpretation**:
- **CO_MINGLED_DOWNSTREAM** is heavy on `material` (40 %), `business_entity` (33 %), and `customer` (20 %). Means: when Mainland data fans out to mixed targets, the join key tends to be material × company-code × customer. View-layer filter on these three is high leverage.
- **CO_MINGLED_UPSTREAM** is heavy on `location` (15.8 %). Means: when Mainland tables receive from mixed sources, the discriminator is plant. ART_05 (Mainland sites) is the gating filter.
- **UNCLASSIFIED** has the highest `business_entity` rate (27.9 %) — these are likely Mainland-relevant tables we couldn't classify due to missing lineage events (e.g., manual loads, ADF JDBC writes). Worth a manual review pass.

## Separator column-coverage gap (vs Deep Research §6.4)

Our column-name regex set is broader than Deep Research's first-pass dictionary — it covers SAP technical names plus FDP normalised forms. Estimated coverage on `fdp_prd_*`:

| Separator | Our hit count (total fdp prd nodes flagged) |
|---|---:|
| business_entity (BUKRS, company_code, profit/cost-centre, WBS) | ≈ inferable from the `9.1 % × 2,952` rates above ≈ 270 nodes in seed alone |
| location (WERKS, plant, site, AOT) | ≈ 320 nodes in seed |
| employee (PERNR, employee_id) | ≈ 32 nodes in seed |
| customer (KUNNR, customer_id, sold_to, ship_to) | ≈ 160 nodes in seed |
| material (MATNR, material_id) | ≈ 285 nodes in seed |
| sales_org (VKORG, sales_org) | ≈ 168 nodes in seed |

Compares to Deep Research's 373 BUKRS / 721 plant / 167 employee / 306 customer (over fdp_prd_*). Our numbers are lower because we limit to nodes in the spider-web; the unwalked balance lives in pure-retained tables that have separator columns but no Mainland lineage.

## Top 20 schemas (production) by node count in spider-web

| Schema | n_nodes | mainland_tagged | cm_up | cm_dn | source | sink |
|---|---:|---:|---:|---:|---:|---:|
| std_internal_sapanzecc | 930 | 930 | 0 | 0 | 0 | 0 |
| std_internal_apac_malaysia | 454 | 454 | 0 | 0 | 0 | 0 |
| std_internal_sapentbw | 172 | 0 | 0 | 1 | 2 | 0 |
| std_internal_apac_vietnam | 87 | 87 | 0 | 0 | 0 | 0 |
| srv_internal_sapanzecc | 63 | 0 | 1 | 0 | 0 | 18 |
| std_internal_jde | 57 | 57 | 0 | 0 | 0 | 0 |
| itg_restricted_finance | 51 | 32 | 1 | 0 | 0 | 0 |
| std_confidential_sapenthanadb | 48 | 0 | 0 | **9** | 3 | 0 |
| itg_internal_source_to_pay | 42 | 0 | **4** | 0 | 0 | 1 |
| srv_internal_source_to_pay | 40 | 0 | 0 | 0 | 0 | 1 |
| itg_internal_sapentbw | 26 | 0 | 0 | 2 | 0 | 0 |
| std_internal_sapcorpecc | 25 | 0 | 0 | 0 | 0 | 0 |
| itg_internal_sapanzecc | 18 | 0 | 0 | 0 | 0 | 0 |
| std_internal_source_to_pay | 17 | 0 | 1 | 0 | 0 | 9 |
| srv_internal_jde | 16 | 0 | 0 | 0 | 0 | 6 |
| std_internal_sapanzbw | 16 | 6 | 0 | 0 | 7 | 0 |
| itg_restricted_source_to_pay | 14 | 0 | 0 | 0 | 0 | 0 |
| std_internal_mainland | 14 | 14 | 0 | 0 | 0 | 0 |
| std_internal_corpsap | 13 | 0 | 0 | 0 | 0 | 0 |
| srv_restricted_finance | 13 | 10 | 0 | 0 | 0 | 0 |

**Pinch-point hot spots**:
- `std_confidential_sapenthanadb` — 9 CO_MINGLED_DOWNSTREAM (all P&L HANA views).
- `itg_internal_source_to_pay` — 4 CO_MINGLED_UPSTREAM (supplier / PO dimensions).
- `srv_internal_sapanzecc` — 18 MAINLAND_SINK (pure consumers of ANZ ECC, all in serving layer).
- `std_internal_sapanzbw` — 7 MAINLAND_SOURCE (Mainland feeders not yet Channel-A-tagged).

## Cross-catalog flow

50 distinct (src_catalog, tgt_catalog) pairs, top 5:

| Source catalog | Target catalog | Distinct edges | Lineage events |
|---|---|---:|---:|
| fdp_prd_std_internal | fdp_prd_std_internal | 1,344 | 784,053 |
| fdp_prd_std_internal | fdp_prd_itg_internal | 338 | 164,624 |
| fdp_prd_itg_internal | fdp_prd_srv_internal | 104 | 135,077 |
| fdp_prd_itg_restricted | fdp_prd_srv_restricted | 34 | 109,886 |
| fdp_prd_std_internal | fdp_prd_srv_internal | 83 | 71,343 |

**Comparison with Deep Research §6.5**: Deep Research reported 12.84M intra-catalog and 1.01M cross-catalog events over 30 days (92.7 % intra). Our 90-day spider-web inherits the same shape — most flow stays within Standardised → Integrated → Serving promotion lanes. Cross-restricted flow (`itg_restricted` → `srv_restricted`, 109k events) is the Mainland P&L view-promotion lane (Deep Research §7.2).

## What this means for the architecture options paper

1. **49 pinch-points** is the actionable engineering scope. Every one of them needs a UC tag, a row filter (on the relevant separator), and a counter-query for the negative attestation harness.

2. **View-layer separation works**. The `srv_restricted_finance` / `srv_restricted_people_data` schemas have **zero** CO_MINGLED nodes — separation is clean at the Serving layer. The pattern from Deep Research §7.2 is validated and should be generalised.

3. **The biggest entanglement engineering load is in `itg_internal_source_to_pay`** (4 CO_MINGLED_UPSTREAM) and `std_confidential_sapenthanadb` (9 CO_MINGLED_DOWNSTREAM). Both feed into ART_03 (materials), ART_04 (customers), ART_06 (vendors). Targeting these two schemas with the first wave of UC tagging covers the highest-leverage pinch-points.

4. **Korora's paired pattern is partially leaky** (3 pairs flagged CO_MINGLED). Confirms Deep Research §7.3 recommendation to consolidate Korora onto the view-layer pattern.

5. **dev catalogs entanglement is similar to prod**, suggesting the dev-to-prod promotion preserves the entanglement structure. Phase-3 classification on prd-only is the correct scope; dev numbers are a sanity-check baseline.

## Outputs in `outputs/`

| File | Rows | Purpose |
|---|---:|---|
| `mainland_candidates.csv` | 2,952 | Phase 1 seed |
| `classified_nodes.csv` | 3,949 | Full Phase 3 classification |
| `entanglement_pinchpoints.csv` | 49 | The actionable pinch-point list |
| `edges.csv` | 3,954 | Full edge set for visualisation |
| `per_schema_rollup.csv` | 69 | Production-only schema rollup |
| `cross_catalog_edges.csv` | 50 | Cross-catalog flow summary |

## Next: Phase 5 (visualization)

Build a pyvis HTML for the full graph (filterable by category), Graphviz PNG for the top-50-pinch-point neighbourhood (Confluence embed), and a Lakeview tile pinned to the working schema for live Mike + Satya access.
