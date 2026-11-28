-- Step 3 of the Phase 3 build: create the five staging tables.
--
-- Decision 5 (docs/project_decisions.md): each CSV is first loaded as-is into a
-- staging table, checked, and only then copied into the final tables.
--   * one staging table per CSV, with the columns in the same order as the
--     file's header row (LOAD DATA matches columns by position);
--   * every column is text, so blanks and values such as 2620945.0 arrive
--     exactly as written, and no keys or constraints can reject a row;
--   * text columns are wide (VARCHAR 500) so nothing is cut off during the
--     load. Step 5 checks every value against the final column length;
--   * the four Ticketmaster ID columns use utf8mb4_bin (Decision 2), so
--     DISTINCT and GROUP BY on them keep IDs that differ only in letter case
--     apart. metro_area_geoid keeps the database default collation, the same
--     as the final tables.
--
-- working_excluded_events.csv is not loaded. The staging tables are dropped
-- only after all final checks pass (Step 8).
--
-- Run from the repository root (no data files are read in this step):
--     mysql -u <your_mysql_user> -p --table < sql/03_create_staging_tables.sql

USE ticket_market_analytics;

-- working_events.csv (13 columns)
CREATE TABLE stg_event (
    event_id            VARCHAR(100) COLLATE utf8mb4_bin,
    event_name          VARCHAR(500),
    event_url           VARCHAR(500),
    status              VARCHAR(500),
    local_date          VARCHAR(500),
    local_time          VARCHAR(500),
    segment_id          VARCHAR(100) COLLATE utf8mb4_bin,
    segment             VARCHAR(500),
    genre_id            VARCHAR(100) COLLATE utf8mb4_bin,
    genre               VARCHAR(500),
    subgenre            VARCHAR(500),
    venue_id            VARCHAR(100) COLLATE utf8mb4_bin,
    ticketing_platform  VARCHAR(500)
) ENGINE = InnoDB;

-- working_venues.csv (9 columns)
CREATE TABLE stg_venue (
    venue_id           VARCHAR(100) COLLATE utf8mb4_bin,
    venue_name         VARCHAR(500),
    venue_address      VARCHAR(500),
    venue_city         VARCHAR(500),
    venue_state        VARCHAR(500),
    venue_postal_code  VARCHAR(500),
    venue_latitude     VARCHAR(500),
    venue_longitude    VARCHAR(500),
    metro_area_geoid   VARCHAR(500)
) ENGINE = InnoDB;

-- market_labels.csv (3 columns)
CREATE TABLE stg_market_label (
    metro_area_geoid   VARCHAR(500),
    census_metro_name  VARCHAR(500),
    market_label       VARCHAR(500)
) ENGINE = InnoDB;

-- working_acs1_2025_metros.csv (3 columns)
CREATE TABLE stg_acs (
    metro_area_geoid         VARCHAR(500),
    population               VARCHAR(500),
    median_household_income  VARCHAR(500)
) ENGINE = InnoDB;

-- working_cbp2023_metros.csv (5 columns)
CREATE TABLE stg_cbp (
    metro_area_geoid  VARCHAR(500),
    naics_code        VARCHAR(500),
    naics_label       VARCHAR(500),
    establishments    VARCHAR(500),
    employees         VARCHAR(500)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------------
-- Checks: compare each result with the expected value in its heading.
-- ---------------------------------------------------------------------------

-- Check A: 5 staging tables, with 13 + 9 + 3 + 3 + 5 = 33 columns.
SELECT TABLE_NAME AS staging_table, COUNT(*) AS columns_found
FROM   information_schema.COLUMNS
WHERE  TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME LIKE 'stg\_%'
GROUP  BY TABLE_NAME
ORDER  BY TABLE_NAME;
-- expected: stg_acs 3, stg_cbp 5, stg_event 13, stg_market_label 3, stg_venue 9

-- Check B: the staging ID columns use utf8mb4_bin (exactly 5 columns).
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, COLLATION_NAME
FROM   information_schema.COLUMNS
WHERE  TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME LIKE 'stg\_%'
  AND  COLLATION_NAME = 'utf8mb4_bin'
ORDER  BY TABLE_NAME, COLUMN_NAME;

-- Check C: the staging tables have no keys and no constraints (expected 0 rows).
SELECT TABLE_NAME, CONSTRAINT_NAME, CONSTRAINT_TYPE
FROM   information_schema.TABLE_CONSTRAINTS
WHERE  TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME LIKE 'stg\_%';

-- Check D: the database now holds 13 tables (the 8 final tables plus 5 staging tables),
-- and the 5 staging tables are empty.
SELECT (SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_TYPE = 'BASE TABLE') AS tables_expected_13,
       (SELECT COUNT(*) FROM stg_event)        AS stg_event_rows_expected_0,
       (SELECT COUNT(*) FROM stg_venue)        AS stg_venue_rows_expected_0,
       (SELECT COUNT(*) FROM stg_market_label) AS stg_market_label_rows_expected_0,
       (SELECT COUNT(*) FROM stg_acs)          AS stg_acs_rows_expected_0,
       (SELECT COUNT(*) FROM stg_cbp)          AS stg_cbp_rows_expected_0;
