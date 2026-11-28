-- Step 8 of the Phase 3 build: drop the five staging tables.
--
-- Decision 5 (docs/project_decisions.md): the staging tables are dropped ONLY
-- after all final checks pass. Run this only when:
--   * Step 7 (sql/07_final_checks.sql) ended with FAILED CHECKS = 0, and
--   * the SHA-256 checksums of the six working_dedup_v5 CSV files still equal the
--     values recorded in docs/database_build_log.md (the files were not changed).
--
-- Only these five tables are dropped, each named explicitly (no wildcards):
--   stg_event, stg_venue, stg_market_label, stg_acs, stg_cbp
-- The 8 ERD tables are not touched. There is no "IF EXISTS": if a staging table
-- is already gone, MySQL stops with error 1051 and nothing else changes.
--
-- Run from the repository root:
--     mysql -u <your_mysql_user> -p --table < sql/08_drop_staging_tables.sql

USE ticket_market_analytics;

-- Before: the 13 tables in the database (this list is what the DROP changes).
SELECT TABLE_NAME AS tables_before_expected_13
FROM   information_schema.TABLES
WHERE  TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_TYPE = 'BASE TABLE'
ORDER  BY TABLE_NAME;

DROP TABLE stg_event, stg_venue, stg_market_label, stg_acs, stg_cbp;

-- After: the 8 permanent tables.
SELECT TABLE_NAME AS tables_after_expected_8
FROM   information_schema.TABLES
WHERE  TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_TYPE = 'BASE TABLE'
ORDER  BY TABLE_NAME;

-- Checks: compare each result with its expected value.
WITH results AS (
    SELECT 1 AS n, 'tables in the database' AS check_name, '8' AS expected,
           CAST((SELECT COUNT(*) FROM information_schema.TABLES
                 WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_TYPE = 'BASE TABLE') AS CHAR) AS actual
    UNION ALL SELECT 2, 'tables whose name starts with stg_', '0',
           CAST((SELECT COUNT(*) FROM information_schema.TABLES
                 WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME LIKE 'stg\_%') AS CHAR)
    UNION ALL SELECT 3, 'tables that are the 8 ERD tables', '8',
           CAST((SELECT COUNT(*) FROM information_schema.TABLES
                 WHERE TABLE_SCHEMA = 'ticket_market_analytics'
                   AND TABLE_NAME IN ('metro_area', 'segment', 'industry', 'venue', 'genre',
                                      'metro_demographic', 'metro_industry', 'event')) AS CHAR)
    UNION ALL SELECT 4,  'rows in metro_area',        '24',    CAST((SELECT COUNT(*) FROM metro_area) AS CHAR)
    UNION ALL SELECT 5,  'rows in segment',           '2',     CAST((SELECT COUNT(*) FROM segment) AS CHAR)
    UNION ALL SELECT 6,  'rows in industry',          '3',     CAST((SELECT COUNT(*) FROM industry) AS CHAR)
    UNION ALL SELECT 7,  'rows in venue',             '965',   CAST((SELECT COUNT(*) FROM venue) AS CHAR)
    UNION ALL SELECT 8,  'rows in genre',             '41',    CAST((SELECT COUNT(*) FROM genre) AS CHAR)
    UNION ALL SELECT 9,  'rows in metro_demographic', '24',    CAST((SELECT COUNT(*) FROM metro_demographic) AS CHAR)
    UNION ALL SELECT 10, 'rows in metro_industry',    '72',    CAST((SELECT COUNT(*) FROM metro_industry) AS CHAR)
    UNION ALL SELECT 11, 'rows in event',             '10895', CAST((SELECT COUNT(*) FROM event) AS CHAR)
    UNION ALL SELECT 12, 'foreign-key columns', '7',
           CAST((SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
                 WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND REFERENCED_TABLE_NAME IS NOT NULL) AS CHAR)
    UNION ALL SELECT 13, 'columns in the database', '36',
           CAST((SELECT COUNT(*) FROM information_schema.COLUMNS
                 WHERE TABLE_SCHEMA = 'ticket_market_analytics') AS CHAR)
    UNION ALL SELECT 14, 'global local_infile setting (must be off)', '0', CAST(@@GLOBAL.local_infile AS CHAR)
)
SELECT n, check_name, expected, actual, IF(actual = expected, 'PASS', 'FAIL') AS result
FROM   results
UNION ALL
SELECT 999, 'FAILED CHECKS (must be 0)', '0', CAST(SUM(actual <> expected) AS CHAR),
       IF(SUM(actual <> expected) = 0, 'PASS', 'FAIL')
FROM   results
ORDER  BY n;
