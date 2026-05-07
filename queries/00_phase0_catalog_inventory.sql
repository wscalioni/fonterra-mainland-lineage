-- Phase 0 catalog inventory: cross-check Deep Research §6.1 numbers (drift since
-- 2026-04-22). Confirms the view-only invariant of srv_* catalogs.

SELECT
  table_catalog,
  COUNT(*) FILTER (WHERE table_type IN ('MANAGED','EXTERNAL')) AS managed_tables,
  COUNT(*) FILTER (WHERE table_type = 'VIEW')                  AS views
FROM system.information_schema.tables
WHERE table_catalog LIKE 'fdp_prd_%'
GROUP BY table_catalog
ORDER BY table_catalog;
