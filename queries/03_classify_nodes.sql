-- Phase 3 — Per-node entanglement classification
-- =====================================================================
-- Inputs: mainland_lineage_seed, mainland_lineage_edges, mainland_lineage_nodes
-- Output: mainland_lineage_classified (managed Delta table)
--
-- For each node we compute:
--   n_upstream                 = distinct upstream neighbours (in walked graph)
--   n_upstream_mainland        = of those, how many are Mainland-tagged (in seed)
--   n_downstream               = distinct downstream neighbours
--   n_downstream_mainland      = of those, how many are Mainland-tagged
--
-- mainland_in_ratio  = n_upstream_mainland   / NULLIF(n_upstream,0)
-- mainland_out_ratio = n_downstream_mainland / NULLIF(n_downstream,0)
-- bridge_score       = 1 if BOTH directions are partially-mainland (entangled),
--                      else higher when imbalance is large (see formula)
--
-- Category assignment:
--   MAINLAND_TAGGED          — node is in seed (Channels A/B/C). Treat as
--                              Mainland authoritative.
--   MAINLAND_INTERIOR        — not in seed, but every observed upstream and
--                              downstream neighbour is Mainland-tagged.
--                              Strong "Mainland-only consumer that re-exports
--                              into Mainland" signal.
--   CO_MINGLED_UPSTREAM      — has upstream neighbours from BOTH Mainland and
--                              non-Mainland sources. Join point. Pinch-point
--                              candidate.
--   CO_MINGLED_DOWNSTREAM    — has downstream neighbours feeding BOTH
--                              Mainland and non-Mainland targets. Fan-out
--                              point. Also a pinch-point candidate.
--   MAINLAND_SINK            — terminal consumer, all upstream is Mainland,
--                              no downstream observed.
--   MAINLAND_SOURCE          — pure feeder of Mainland, no observed upstream
--                              and all downstream is Mainland.
--   RETAINED_OR_INDIRECT     — neither in seed nor with any Mainland
--                              neighbour (rare in this dataset since the walk
--                              is anchored to seed).
--   UNCLASSIFIED             — fallback.
--
-- Separator applicability: per-node flags business_entity / location /
-- employee, derived from whether its columns include any column whose name
-- matches the separator regex set (see Deep Research §6.4).
--
-- Run this AFTER the walker (Phase 2) materialises the three input tables.

CREATE OR REPLACE TABLE aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_classified
COMMENT 'Phase 3 entanglement classification per node. Refreshed by 03_classify_nodes.sql.'
AS
WITH
-- Per-node upstream summary
upstream AS (
  SELECT
    e.tgt_full_name AS node,
    COUNT(DISTINCT e.src_full_name) AS n_upstream,
    COUNT(DISTINCT CASE WHEN s.full_name IS NOT NULL THEN e.src_full_name END) AS n_upstream_mainland
  FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_edges e
  LEFT JOIN aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_seed s
    ON s.full_name = e.src_full_name
  GROUP BY 1
),

-- Per-node downstream summary
downstream AS (
  SELECT
    e.src_full_name AS node,
    COUNT(DISTINCT e.tgt_full_name) AS n_downstream,
    COUNT(DISTINCT CASE WHEN s.full_name IS NOT NULL THEN e.tgt_full_name END) AS n_downstream_mainland
  FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_edges e
  LEFT JOIN aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_seed s
    ON s.full_name = e.tgt_full_name
  GROUP BY 1
),

-- Separator-column flags per node (from system.information_schema.columns).
-- Column-name regex set covers SAP technical names and FDP normalised forms.
sep_flags AS (
  SELECT
    CONCAT(c.table_catalog, '.', c.table_schema, '.', c.table_name) AS node,
    MAX(CASE WHEN LOWER(c.column_name) RLIKE '^(bukrs|company_code|company_cd|companycode|prctr|profit_centre|profit_center|kostl|cost_centre|cost_center|wbsn|wbs_element)$'
              OR LOWER(c.column_name) LIKE 'org%company%code%'
              OR LOWER(c.column_name) LIKE 'org%profit%center%' THEN 1 ELSE 0 END) AS sep_business_entity,
    MAX(CASE WHEN LOWER(c.column_name) RLIKE '^(werks|plant|plant_code|plnt|site_code|aot_site|aot_code)$'
              OR LOWER(c.column_name) LIKE 'org%plant%' THEN 1 ELSE 0 END) AS sep_location,
    MAX(CASE WHEN LOWER(c.column_name) RLIKE '^(pernr|personnel_number|employee_id|employee_number|emp_id|emp_number|emp_email)$'
              OR LOWER(c.column_name) LIKE '%employee%email%' THEN 1 ELSE 0 END) AS sep_employee,
    MAX(CASE WHEN LOWER(c.column_name) RLIKE '^(kunnr|customer_id|customer_number|customer_no|customer_code|sold_to|sold_to_party|ship_to|ship_to_party)$'
              THEN 1 ELSE 0 END) AS sep_customer,
    MAX(CASE WHEN LOWER(c.column_name) RLIKE '^(matnr|material_id|material_number|material_no|material_code)$'
              THEN 1 ELSE 0 END) AS sep_material,
    MAX(CASE WHEN LOWER(c.column_name) RLIKE '^(vkorg|sales_org|sales_organization|sales_organisation)$'
              THEN 1 ELSE 0 END) AS sep_sales_org
  FROM system.information_schema.columns c
  WHERE c.table_catalog LIKE 'fdp_prd_%'
     OR c.table_catalog LIKE 'fdp_dev_%'
  GROUP BY 1
)

SELECT
  n.full_name                AS node,
  n.is_seed,
  n.first_seen_hop,
  n.first_seen_dir,
  COALESCE(u.n_upstream, 0)            AS n_upstream,
  COALESCE(u.n_upstream_mainland, 0)   AS n_upstream_mainland,
  COALESCE(d.n_downstream, 0)          AS n_downstream,
  COALESCE(d.n_downstream_mainland, 0) AS n_downstream_mainland,

  -- Ratios. NULL when denominator is 0.
  CASE WHEN COALESCE(u.n_upstream, 0)   > 0
       THEN ROUND(u.n_upstream_mainland   * 1.0 / u.n_upstream,   3) END AS mainland_in_ratio,
  CASE WHEN COALESCE(d.n_downstream, 0) > 0
       THEN ROUND(d.n_downstream_mainland * 1.0 / d.n_downstream, 3) END AS mainland_out_ratio,

  -- bridge_score: how entangled the node is.
  -- 0 when seed, when no mainland neighbours, or when only one direction has data.
  -- Higher when both directions are partially-mainland (true co-mingling).
  -- Formula: min(in_partial, out_partial) where partial = mainland_share * (1-mainland_share).
  CASE
    WHEN n.is_seed THEN 0.0
    WHEN COALESCE(u.n_upstream, 0) > 0 AND COALESCE(d.n_downstream, 0) > 0
         AND u.n_upstream_mainland > 0 AND d.n_downstream_mainland > 0
         AND u.n_upstream_mainland < u.n_upstream
         AND d.n_downstream_mainland < d.n_downstream
    THEN ROUND(LEAST(
           (u.n_upstream_mainland   * 1.0 / u.n_upstream)   * (1 - u.n_upstream_mainland   * 1.0 / u.n_upstream),
           (d.n_downstream_mainland * 1.0 / d.n_downstream) * (1 - d.n_downstream_mainland * 1.0 / d.n_downstream)
         ) * 4.0, 3)
    ELSE 0.0
  END AS bridge_score,

  -- Category
  CASE
    WHEN n.is_seed THEN 'MAINLAND_TAGGED'

    -- Pure Mainland feeder: no upstream observed, all downstream is Mainland.
    WHEN COALESCE(u.n_upstream, 0) = 0
         AND COALESCE(d.n_downstream, 0) > 0
         AND d.n_downstream_mainland = d.n_downstream
      THEN 'MAINLAND_SOURCE'

    -- Pure Mainland sink: no downstream, all upstream is Mainland.
    WHEN COALESCE(d.n_downstream, 0) = 0
         AND COALESCE(u.n_upstream, 0) > 0
         AND u.n_upstream_mainland = u.n_upstream
      THEN 'MAINLAND_SINK'

    -- Interior: every neighbour we see is Mainland.
    WHEN COALESCE(u.n_upstream, 0) > 0
         AND COALESCE(d.n_downstream, 0) > 0
         AND u.n_upstream_mainland   = u.n_upstream
         AND d.n_downstream_mainland = d.n_downstream
      THEN 'MAINLAND_INTERIOR'

    -- Co-mingled upstream: receives data from both Mainland and non-Mainland sources.
    WHEN COALESCE(u.n_upstream, 0) > 0
         AND u.n_upstream_mainland > 0
         AND u.n_upstream_mainland < u.n_upstream
      THEN 'CO_MINGLED_UPSTREAM'

    -- Co-mingled downstream: feeds both Mainland and non-Mainland targets.
    WHEN COALESCE(d.n_downstream, 0) > 0
         AND d.n_downstream_mainland > 0
         AND d.n_downstream_mainland < d.n_downstream
      THEN 'CO_MINGLED_DOWNSTREAM'

    -- No Mainland neighbour observed.
    WHEN COALESCE(u.n_upstream_mainland, 0)   = 0
         AND COALESCE(d.n_downstream_mainland, 0) = 0
      THEN 'RETAINED_OR_INDIRECT'

    ELSE 'UNCLASSIFIED'
  END AS category,

  -- Separators
  COALESCE(sf.sep_business_entity, 0) AS sep_business_entity,
  COALESCE(sf.sep_location,        0) AS sep_location,
  COALESCE(sf.sep_employee,        0) AS sep_employee,
  COALESCE(sf.sep_customer,        0) AS sep_customer,
  COALESCE(sf.sep_material,        0) AS sep_material,
  COALESCE(sf.sep_sales_org,       0) AS sep_sales_org,

  -- Convenience: catalog + schema split for downstream rollups
  SPLIT_PART(n.full_name, '.', 1) AS catalog,
  SPLIT_PART(n.full_name, '.', 2) AS schema,
  SPLIT_PART(n.full_name, '.', 3) AS table_name

FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_nodes n
LEFT JOIN upstream    u  ON u.node  = n.full_name
LEFT JOIN downstream  d  ON d.node  = n.full_name
LEFT JOIN sep_flags   sf ON sf.node = n.full_name;
