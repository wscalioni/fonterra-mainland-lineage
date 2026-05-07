-- Phase 1 — Mainland candidate discovery, three channels
-- =====================================================================
-- Output: one row per (catalog, schema, table) Mainland-candidate object
-- with the channel that picked it up and a confidence label.
--
-- Channels:
--  A — Known Mainland surfaces from Deep Research §6.3 (HIGH confidence).
--      Schemas whose name is Mainland-located (whole-schema membership) or
--      where a name-pattern match is the canonical Mainland-suffix view
--      pattern in itg_restricted_finance / srv_restricted_finance /
--      srv_restricted_people_data / itg_internal_korora /
--      srv_internal_korora.
--
--  B — Keyword search over fdp_prd_* + fdp_dev_* table/view names
--      (MEDIUM-HIGH). Catches Mainland-named assets outside the Channel A
--      schemas (e.g. ad-hoc ITG views).
--
--  C — High-Mainland-density source schemas at the Standardised layer
--      (HIGH for sapanzecc/jde, MEDIUM for apac_malaysia/vietnam).
--      Per Deep Research §6.2, std_internal_sapanzecc is 99 % Mainland and
--      std_internal_jde is 95 % Mainland. apac_malaysia / apac_vietnam are
--      geographically Mainland-relevant and Asian operations were sold to
--      Lactalis under the JDE transaction set.
--
-- Anchor and NZMP brand-keyword matches are intentionally excluded
-- (Anchor is a global brand, NZMP is global food-services). They are
-- caught later by lineage from Channel C sources.
--
-- A single object can match more than one channel; the highest-confidence
-- channel wins and the others are listed in `also_matched`.

WITH all_objects AS (
  SELECT
    table_catalog,
    table_schema,
    table_name,
    table_type,
    CONCAT(table_catalog, '.', table_schema, '.', table_name) AS full_name
  FROM system.information_schema.tables
  WHERE table_catalog LIKE 'fdp_prd_%'
     OR table_catalog LIKE 'fdp_dev_%'
),

-- Channel A — known Mainland surfaces (Deep Research §6.3)
channel_a AS (
  SELECT
    full_name,
    'A' AS channel,
    CASE
      WHEN LOWER(table_schema) IN ('std_internal_mainland', 'itg_restricted_mainland')
        THEN 'whole_schema_mainland'
      WHEN LOWER(table_schema) = 'itg_internal_korora'
           AND LOWER(table_name) LIKE '%mainland%'
        THEN 'korora_mainland_pair'
      WHEN LOWER(table_schema) IN ('itg_restricted_finance', 'srv_restricted_finance',
                                    'srv_restricted_people_data', 'srv_internal_korora')
           AND LOWER(table_name) LIKE '%mainland%'
        THEN 'restricted_mainland_view'
    END AS match_reason,
    'HIGH' AS confidence
  FROM all_objects
  WHERE
    LOWER(table_schema) IN ('std_internal_mainland', 'itg_restricted_mainland')
    OR (
      LOWER(table_schema) IN ('itg_internal_korora', 'itg_restricted_finance',
                              'srv_restricted_finance', 'srv_restricted_people_data',
                              'srv_internal_korora')
      AND LOWER(table_name) LIKE '%mainland%'
    )
),

-- Channel B — keyword search over names
channel_b AS (
  SELECT
    full_name,
    'B' AS channel,
    CONCAT('keyword:',
      CASE
        WHEN LOWER(table_name) LIKE '%mainland%' THEN 'mainland'
        WHEN LOWER(table_name) LIKE '%kapiti%'   THEN 'kapiti'
        WHEN LOWER(table_name) LIKE '%galaxy%'   THEN 'galaxy'
        WHEN LOWER(table_name) LIKE '%_mld_%' OR LOWER(table_name) LIKE 'mld_%'
             OR LOWER(table_name) LIKE '%_mld'  THEN 'mld'
        WHEN LOWER(table_name) LIKE '%fbnz%'  THEN 'fbnz'
        WHEN LOWER(table_name) LIKE '%fbau%'  THEN 'fbau'
        WHEN LOWER(table_name) LIKE '%fonterra_brands_nz%' THEN 'fonterra_brands_nz'
        WHEN LOWER(table_name) LIKE '%fonterra_brands_au%' THEN 'fonterra_brands_au'
      END
    ) AS match_reason,
    'MEDIUM' AS confidence
  FROM all_objects
  WHERE
       LOWER(table_name) LIKE '%mainland%'
    OR LOWER(table_name) LIKE '%kapiti%'
    OR LOWER(table_name) LIKE '%galaxy%'
    OR LOWER(table_name) LIKE '%_mld_%'
    OR LOWER(table_name) LIKE 'mld_%'
    OR LOWER(table_name) LIKE '%_mld'
    OR LOWER(table_name) LIKE '%fbnz%'
    OR LOWER(table_name) LIKE '%fbau%'
    OR LOWER(table_name) LIKE '%fonterra_brands_nz%'
    OR LOWER(table_name) LIKE '%fonterra_brands_au%'
),

-- Channel C — high-Mainland-density source schemas
channel_c AS (
  SELECT
    full_name,
    'C' AS channel,
    CASE
      WHEN LOWER(table_schema) = 'std_internal_sapanzecc'
        THEN 'high_density_source:sapanzecc_99pct'
      WHEN LOWER(table_schema) = 'std_internal_jde'
        THEN 'high_density_source:jde_95pct'
      WHEN LOWER(table_schema) = 'std_internal_apac_malaysia'
        THEN 'asian_ops_source:malaysia'
      WHEN LOWER(table_schema) = 'std_internal_apac_vietnam'
        THEN 'asian_ops_source:vietnam'
    END AS match_reason,
    CASE
      WHEN LOWER(table_schema) IN ('std_internal_sapanzecc', 'std_internal_jde')
        THEN 'HIGH'
      ELSE 'MEDIUM'
    END AS confidence
  FROM all_objects
  WHERE LOWER(table_schema) IN (
    'std_internal_sapanzecc',
    'std_internal_jde',
    'std_internal_apac_malaysia',
    'std_internal_apac_vietnam'
  )
),

unioned AS (
  SELECT * FROM channel_a
  UNION ALL
  SELECT * FROM channel_b
  UNION ALL
  SELECT * FROM channel_c
),

-- Collapse multi-channel hits, prefer HIGH > MEDIUM, A > C > B for ties.
ranked AS (
  SELECT
    full_name,
    channel,
    match_reason,
    confidence,
    ROW_NUMBER() OVER (
      PARTITION BY full_name
      ORDER BY
        CASE confidence WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
        CASE channel    WHEN 'A' THEN 1 WHEN 'C' THEN 2 WHEN 'B' THEN 3 END
    ) AS rk,
    COUNT(*) OVER (PARTITION BY full_name) AS n_channels,
    COLLECT_SET(channel) OVER (PARTITION BY full_name) AS all_channels
  FROM unioned
)

SELECT
  full_name,
  channel        AS primary_channel,
  match_reason   AS primary_match_reason,
  confidence     AS primary_confidence,
  ARRAY_JOIN(all_channels, ',') AS all_channels,
  n_channels     AS channel_count
FROM ranked
WHERE rk = 1
ORDER BY confidence, primary_channel, full_name;
