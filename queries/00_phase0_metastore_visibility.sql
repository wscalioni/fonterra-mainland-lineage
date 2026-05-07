-- Phase 0 metastore visibility: distinct workspace IDs producing lineage events
-- in the trailing 30 days. Confirms the analysis is metastore-wide rather than
-- sandbox-only.
--
-- Run from sandbox via FONTERRA profile, serverless warehouse 406253829ca12fd5.
--
-- Output is the table reproduced in analysis/00-phase0-ground-truth.md.

SELECT
  workspace_id,
  COUNT(*)                                       AS events_30d,
  COUNT(DISTINCT source_table_full_name)         AS distinct_sources,
  COUNT(DISTINCT target_table_full_name)         AS distinct_targets
FROM system.access.table_lineage
WHERE event_time > current_date() - INTERVAL 30 DAYS
GROUP BY workspace_id
ORDER BY events_30d DESC;
