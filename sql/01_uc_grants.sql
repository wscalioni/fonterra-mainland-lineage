-- UC + warehouse grants for the Mainland Lineage app.
-- NOT applied yet — sandbox is single-user. Apply against the destination
-- workspace once deployed to a shared environment with the programme group
-- defined. Replace `fonterra-divestment-programme` with the actual UC group
-- name confirmed with Satya/Aneesh before running.
--
-- Run once per workspace, by a user with MANAGE on the working schema.

GRANT USE CATALOG ON CATALOG aw_internal_adpcoe
  TO `fonterra-divestment-programme`;

GRANT USE SCHEMA ON SCHEMA aw_internal_adpcoe.mainland_lineage_analysis
  TO `fonterra-divestment-programme`;

GRANT SELECT ON ALL TABLES IN SCHEMA aw_internal_adpcoe.mainland_lineage_analysis
  TO `fonterra-divestment-programme`;

GRANT SELECT ON ALL VIEWS IN SCHEMA aw_internal_adpcoe.mainland_lineage_analysis
  TO `fonterra-divestment-programme`;

GRANT MODIFY ON TABLE aw_internal_adpcoe.mainland_lineage_analysis.pinchpoint_status
  TO `fonterra-divestment-programme`;

GRANT MODIFY ON TABLE aw_internal_adpcoe.mainland_lineage_analysis.workspace_identities
  TO `fonterra-divestment-programme`;

-- Required for system.access.table_lineage in the workspace identity panel.
GRANT SELECT ON TABLE system.access.table_lineage
  TO `fonterra-divestment-programme`;

-- Warehouse access: apply via the CLI, not SQL:
--   databricks warehouses set-permissions <warehouse-id> \
--     --json '{"access_control_list": [{"group_name": "fonterra-divestment-programme", "permission_level": "CAN_USE"}]}' \
--     --profile <profile>
