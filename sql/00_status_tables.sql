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
