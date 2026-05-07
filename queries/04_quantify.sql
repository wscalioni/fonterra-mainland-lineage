-- Phase 4 — Quantification queries
-- =====================================================================
-- Each query is independent. They produce the numbers cited in
-- analysis/uc-lineage-spiderweb.md and the Confluence subpage.
-- All read from aw_internal_adpcoe.mainland_lineage_analysis.* and
-- system.information_schema.* (denominator reference).

-- 4.1 — Total fdp_prd object count (denominator)
-- ---------------------------------------------------------------------
-- Used to compute "Mainland-touching tables / total FDP tables".

WITH denom AS (
  SELECT COUNT(*) AS total_fdp_prd_objects
  FROM system.information_schema.tables
  WHERE table_catalog LIKE 'fdp_prd_%'
)
SELECT * FROM denom;


-- 4.2 — Category distribution (full)
-- ---------------------------------------------------------------------

SELECT
  category,
  COUNT(*)                                        AS n_nodes,
  COUNT(*) FILTER (WHERE is_seed)                 AS n_seed,
  COUNT(*) FILTER (WHERE NOT is_seed)             AS n_walked,
  ROUND(100.0 * COUNT(*) /
        SUM(COUNT(*)) OVER (), 1)                 AS pct_of_total
FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_classified
GROUP BY category
ORDER BY n_nodes DESC;


-- 4.3 — Top 20 pinch-point nodes (by bridge_score)
-- ---------------------------------------------------------------------

SELECT
  node,
  category,
  ROUND(bridge_score, 3) AS bridge_score,
  n_upstream, n_upstream_mainland, mainland_in_ratio,
  n_downstream, n_downstream_mainland, mainland_out_ratio,
  CONCAT_WS(',',
    CASE WHEN sep_business_entity = 1 THEN 'business_entity' END,
    CASE WHEN sep_location        = 1 THEN 'location' END,
    CASE WHEN sep_employee        = 1 THEN 'employee' END,
    CASE WHEN sep_customer        = 1 THEN 'customer' END,
    CASE WHEN sep_material        = 1 THEN 'material' END,
    CASE WHEN sep_sales_org       = 1 THEN 'sales_org' END
  ) AS separators
FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_classified
WHERE bridge_score > 0
ORDER BY bridge_score DESC, n_upstream + n_downstream DESC
LIMIT 20;


-- 4.4 — Separator coverage matrix per category
-- ---------------------------------------------------------------------

SELECT
  category,
  COUNT(*) AS n_nodes,
  ROUND(100.0 * AVG(sep_business_entity), 1) AS pct_business_entity,
  ROUND(100.0 * AVG(sep_location),        1) AS pct_location,
  ROUND(100.0 * AVG(sep_employee),        1) AS pct_employee,
  ROUND(100.0 * AVG(sep_customer),        1) AS pct_customer,
  ROUND(100.0 * AVG(sep_material),        1) AS pct_material,
  ROUND(100.0 * AVG(sep_sales_org),       1) AS pct_sales_org
FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_classified
GROUP BY category
ORDER BY n_nodes DESC;


-- 4.5 — Per-schema rollup (production only)
-- ---------------------------------------------------------------------

SELECT
  catalog,
  schema,
  COUNT(*)                                                    AS n_nodes,
  COUNT(*) FILTER (WHERE category = 'MAINLAND_TAGGED')        AS n_mainland_tagged,
  COUNT(*) FILTER (WHERE category = 'CO_MINGLED_UPSTREAM')    AS n_comingled_up,
  COUNT(*) FILTER (WHERE category = 'CO_MINGLED_DOWNSTREAM')  AS n_comingled_down,
  COUNT(*) FILTER (WHERE category = 'MAINLAND_INTERIOR')      AS n_interior,
  COUNT(*) FILTER (WHERE category = 'MAINLAND_SOURCE')        AS n_source,
  COUNT(*) FILTER (WHERE category = 'MAINLAND_SINK')          AS n_sink,
  COUNT(*) FILTER (WHERE category = 'RETAINED_OR_INDIRECT')   AS n_retained,
  COUNT(*) FILTER (WHERE bridge_score > 0)                    AS n_bridges,
  ROUND(MAX(bridge_score), 3)                                 AS max_bridge
FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_classified
WHERE catalog LIKE 'fdp_prd_%'
GROUP BY catalog, schema
ORDER BY n_nodes DESC;


-- 4.6 — Cross-catalog edges (entanglement at the catalog level)
-- ---------------------------------------------------------------------
-- Compares against Deep Research §6.5 (12.84M intra / 1.01M cross over 30d).

WITH
edges_classified AS (
  SELECT
    SPLIT_PART(src_full_name, '.', 1) AS src_catalog,
    SPLIT_PART(tgt_full_name, '.', 1) AS tgt_catalog,
    edge_count
  FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_edges
)
SELECT
  src_catalog,
  tgt_catalog,
  COUNT(*)            AS distinct_edges,
  SUM(edge_count)     AS total_events
FROM edges_classified
GROUP BY src_catalog, tgt_catalog
ORDER BY total_events DESC
LIMIT 30;
