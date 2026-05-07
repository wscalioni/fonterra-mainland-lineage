-- Phase 0 confirmation of the Channel A Mainland surface — the 7 known
-- locations from Deep Research §6.3.
--
-- Counts all objects per schema and the subset whose name contains "mainland".
-- The four schemas whose name itself contains "mainland" (std_internal_mainland,
-- itg_restricted_mainland, srv_internal_korora pair, etc.) have all their
-- objects implicitly Mainland-located even when the table name does not.

SELECT
  table_catalog,
  table_schema,
  COUNT(*)                                                         AS n_objects,
  COUNT(DISTINCT CASE WHEN LOWER(table_name) LIKE '%mainland%'
                      THEN table_name END)                         AS n_mainland_named
FROM system.information_schema.tables
WHERE table_catalog LIKE 'fdp_prd_%'
  AND (
        LOWER(table_schema) LIKE '%mainland%'
     OR LOWER(table_schema) IN (
          'itg_internal_korora',
          'itg_restricted_finance',
          'srv_restricted_finance',
          'srv_restricted_people_data',
          'srv_internal_korora'
        )
      )
GROUP BY 1, 2
ORDER BY 1, 2;
