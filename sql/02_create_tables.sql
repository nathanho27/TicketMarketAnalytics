-- Step 2 of the Phase 3 build: create the 8 tables of the approved ERD.
--
-- Decisions: docs/project_decisions.md, "2026-11-27: Phase 3 build decisions"
--   Decision 2: the four Ticketmaster ID columns (segment_id, genre_id,
--               venue_id, event_id) use the case-sensitive collation
--               utf8mb4_bin on BOTH sides of every foreign key. MySQL rejects a
--               foreign key whose two columns differ in collation (error 3780).
--   Decision 3: column types, lengths and NULL rules; lowercase table names;
--               UNIQUE on metro_area.census_metro_name and market_label.
--   Decision 4: latitude and longitude are DECIMAL(18,15), nullable.
-- The ERD itself (8 tables, 36 columns, keys and relationships) is unchanged.
--
-- Tables are created parents first, so every foreign key points at a table that
-- already exists. There is no "IF NOT EXISTS": re-running this script stops
-- with error 1050 instead of silently keeping an old table.
--
-- Run from the repository root (no data files are read in this step):
--     mysql -u <your_mysql_user> -p --table < sql/02_create_tables.sql

USE ticket_market_analytics;

-- 1. metro_area (ERD: METRO_AREA)
CREATE TABLE metro_area (
    metro_area_geoid   CHAR(5)     NOT NULL,
    census_metro_name  VARCHAR(80) NOT NULL,
    market_label       VARCHAR(30) NOT NULL,
    PRIMARY KEY (metro_area_geoid),
    UNIQUE KEY uq_metro_area_census_metro_name (census_metro_name),
    UNIQUE KEY uq_metro_area_market_label (market_label)
) ENGINE = InnoDB;

-- 2. segment (ERD: SEGMENT)
CREATE TABLE segment (
    segment_id  CHAR(18) COLLATE utf8mb4_bin NOT NULL,
    segment     VARCHAR(20) NOT NULL,
    PRIMARY KEY (segment_id)
) ENGINE = InnoDB;

-- 3. industry (ERD: INDUSTRY)
CREATE TABLE industry (
    naics_code   VARCHAR(6)   NOT NULL,
    naics_label  VARCHAR(100) NOT NULL,
    PRIMARY KEY (naics_code)
) ENGINE = InnoDB;

-- 4. venue (ERD: VENUE), child of metro_area
CREATE TABLE venue (
    venue_id           VARCHAR(15) COLLATE utf8mb4_bin NOT NULL,
    metro_area_geoid   CHAR(5)      NOT NULL,
    venue_name         VARCHAR(80)  NOT NULL,
    venue_address      VARCHAR(60)  NULL,
    venue_city         VARCHAR(40)  NULL,
    venue_state        CHAR(2)      NULL,
    venue_postal_code  CHAR(5)      NULL,
    venue_latitude     DECIMAL(18,15) NULL,
    venue_longitude    DECIMAL(18,15) NULL,
    PRIMARY KEY (venue_id),
    CONSTRAINT fk_venue_metro_area
        FOREIGN KEY (metro_area_geoid) REFERENCES metro_area (metro_area_geoid)
) ENGINE = InnoDB;

-- 5. genre (ERD: GENRE), child of segment
CREATE TABLE genre (
    genre_id    CHAR(11) COLLATE utf8mb4_bin NOT NULL,
    segment_id  CHAR(18) COLLATE utf8mb4_bin NOT NULL,
    genre       VARCHAR(30) NOT NULL,
    PRIMARY KEY (genre_id),
    CONSTRAINT fk_genre_segment
        FOREIGN KEY (segment_id) REFERENCES segment (segment_id)
) ENGINE = InnoDB;

-- 6. metro_demographic (ERD: METRO_DEMOGRAPHIC), one row per metro
CREATE TABLE metro_demographic (
    metro_area_geoid         CHAR(5) NOT NULL,
    population               INT     NOT NULL,
    median_household_income  INT     NOT NULL,
    PRIMARY KEY (metro_area_geoid),
    CONSTRAINT fk_metro_demographic_metro_area
        FOREIGN KEY (metro_area_geoid) REFERENCES metro_area (metro_area_geoid)
) ENGINE = InnoDB;

-- 7. metro_industry (ERD: METRO_INDUSTRY), composite key, child of metro_area and industry
CREATE TABLE metro_industry (
    metro_area_geoid  CHAR(5)    NOT NULL,
    naics_code        VARCHAR(6) NOT NULL,
    establishments    INT        NULL,
    employees         INT        NULL,
    PRIMARY KEY (metro_area_geoid, naics_code),
    CONSTRAINT fk_metro_industry_metro_area
        FOREIGN KEY (metro_area_geoid) REFERENCES metro_area (metro_area_geoid),
    CONSTRAINT fk_metro_industry_industry
        FOREIGN KEY (naics_code) REFERENCES industry (naics_code)
) ENGINE = InnoDB;

-- 8. event (ERD: EVENT), child of venue and genre
CREATE TABLE event (
    event_id            VARCHAR(25) COLLATE utf8mb4_bin NOT NULL,
    venue_id            VARCHAR(15) COLLATE utf8mb4_bin NOT NULL,
    genre_id            CHAR(11)    COLLATE utf8mb4_bin NOT NULL,
    event_name          VARCHAR(400) NOT NULL,
    event_url           VARCHAR(255) NULL,
    status              VARCHAR(12)  NOT NULL,
    local_date          DATE         NOT NULL,
    local_time          TIME         NULL,
    subgenre            VARCHAR(30)  NULL,
    ticketing_platform  VARCHAR(40)  NULL,
    PRIMARY KEY (event_id),
    CONSTRAINT fk_event_venue
        FOREIGN KEY (venue_id) REFERENCES venue (venue_id),
    CONSTRAINT fk_event_genre
        FOREIGN KEY (genre_id) REFERENCES genre (genre_id)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------------
-- Checks: compare each result with the expected value in its heading.
-- ---------------------------------------------------------------------------

-- Check A: 8 tables, 36 columns.
SELECT (SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_TYPE = 'BASE TABLE') AS tables_expected_8,
       (SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'ticket_market_analytics') AS columns_expected_36;

-- Check B: 7 foreign-key columns; child and parent must show the same collation.
SELECT k.TABLE_NAME                       AS child_table,
       k.COLUMN_NAME                      AS child_column,
       k.REFERENCED_TABLE_NAME            AS parent_table,
       k.REFERENCED_COLUMN_NAME           AS parent_column,
       c.COLLATION_NAME                   AS child_collation,
       p.COLLATION_NAME                   AS parent_collation,
       IF(c.COLLATION_NAME <=> p.COLLATION_NAME, 'match', 'MISMATCH') AS same_collation
FROM   information_schema.KEY_COLUMN_USAGE k
JOIN   information_schema.COLUMNS c
       ON c.TABLE_SCHEMA = k.TABLE_SCHEMA AND c.TABLE_NAME = k.TABLE_NAME
      AND c.COLUMN_NAME = k.COLUMN_NAME
JOIN   information_schema.COLUMNS p
       ON p.TABLE_SCHEMA = k.REFERENCED_TABLE_SCHEMA AND p.TABLE_NAME = k.REFERENCED_TABLE_NAME
      AND p.COLUMN_NAME = k.REFERENCED_COLUMN_NAME
WHERE  k.TABLE_SCHEMA = 'ticket_market_analytics'
  AND  k.REFERENCED_TABLE_NAME IS NOT NULL
ORDER  BY k.TABLE_NAME, k.COLUMN_NAME;

-- Check C: exactly 7 columns use utf8mb4_bin (the Ticketmaster ID columns).
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, COLLATION_NAME
FROM   information_schema.COLUMNS
WHERE  TABLE_SCHEMA = 'ticket_market_analytics' AND COLLATION_NAME = 'utf8mb4_bin'
ORDER  BY TABLE_NAME, COLUMN_NAME;

-- Check D: exactly 12 columns allow NULL (the optional ERD attributes).
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE
FROM   information_schema.COLUMNS
WHERE  TABLE_SCHEMA = 'ticket_market_analytics' AND IS_NULLABLE = 'YES'
ORDER  BY TABLE_NAME, ORDINAL_POSITION;

-- Check E: the two UNIQUE keys on metro_area (non_unique = 0 means unique).
SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE
FROM   information_schema.STATISTICS
WHERE  TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME = 'metro_area'
ORDER  BY INDEX_NAME;
