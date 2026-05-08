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

-- View used by jobs/nightly_refresh.py to re-classify a subset of nodes.
-- Mirrors queries/03_classify_nodes.sql exactly. Refresh both together if
-- the canonical query changes.
CREATE OR REPLACE VIEW aw_internal_adpcoe.mainland_lineage_analysis.v_classify_node_logic AS
WITH
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
  CASE WHEN COALESCE(u.n_upstream, 0)   > 0
       THEN ROUND(u.n_upstream_mainland   * 1.0 / u.n_upstream,   3) END AS mainland_in_ratio,
  CASE WHEN COALESCE(d.n_downstream, 0) > 0
       THEN ROUND(d.n_downstream_mainland * 1.0 / d.n_downstream, 3) END AS mainland_out_ratio,
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
  CASE
    WHEN n.is_seed THEN 'MAINLAND_TAGGED'
    WHEN COALESCE(u.n_upstream, 0) = 0
         AND COALESCE(d.n_downstream, 0) > 0
         AND d.n_downstream_mainland = d.n_downstream
      THEN 'MAINLAND_SOURCE'
    WHEN COALESCE(d.n_downstream, 0) = 0
         AND COALESCE(u.n_upstream, 0) > 0
         AND u.n_upstream_mainland = u.n_upstream
      THEN 'MAINLAND_SINK'
    WHEN COALESCE(u.n_upstream, 0) > 0
         AND COALESCE(d.n_downstream, 0) > 0
         AND u.n_upstream_mainland   = u.n_upstream
         AND d.n_downstream_mainland = d.n_downstream
      THEN 'MAINLAND_INTERIOR'
    WHEN COALESCE(u.n_upstream, 0) > 0
         AND u.n_upstream_mainland > 0
         AND u.n_upstream_mainland < u.n_upstream
      THEN 'CO_MINGLED_UPSTREAM'
    WHEN COALESCE(d.n_downstream, 0) > 0
         AND d.n_downstream_mainland > 0
         AND d.n_downstream_mainland < d.n_downstream
      THEN 'CO_MINGLED_DOWNSTREAM'
    WHEN COALESCE(u.n_upstream_mainland, 0)   = 0
         AND COALESCE(d.n_downstream_mainland, 0) = 0
      THEN 'RETAINED_OR_INDIRECT'
    ELSE 'UNCLASSIFIED'
  END AS category,
  COALESCE(sf.sep_business_entity, 0) AS sep_business_entity,
  COALESCE(sf.sep_location,        0) AS sep_location,
  COALESCE(sf.sep_employee,        0) AS sep_employee,
  COALESCE(sf.sep_customer,        0) AS sep_customer,
  COALESCE(sf.sep_material,        0) AS sep_material,
  COALESCE(sf.sep_sales_org,       0) AS sep_sales_org,
  SPLIT_PART(n.full_name, '.', 1) AS catalog,
  SPLIT_PART(n.full_name, '.', 2) AS schema,
  SPLIT_PART(n.full_name, '.', 3) AS table_name
FROM aw_internal_adpcoe.mainland_lineage_analysis.mainland_lineage_nodes n
LEFT JOIN upstream    u  ON u.node  = n.full_name
LEFT JOIN downstream  d  ON d.node  = n.full_name
LEFT JOIN sep_flags   sf ON sf.node = n.full_name;
