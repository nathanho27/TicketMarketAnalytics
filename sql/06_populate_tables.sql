-- Step 6 of the Phase 3 build: copy the validated staging data into the 8 final tables.
--
-- Decisions: docs/project_decisions.md, "2026-11-27: Phase 3 build decisions"
--   Decision 5: parents first; the staging tables stay in place until all final
--               checks (Step 7) pass.
--   Decision 6: the cleaning rules below.
--                 * trim whitespace at the start and end of venue_name,
--                   venue_address, venue_city and venue_postal_code, using
--                   REGEXP_REPLACE (plain TRIM() misses a non-breaking space);
--                 * every nullable column goes through NULLIF(col, ''), so a
--                   blank cell becomes NULL (a blank time would otherwise be
--                   stored as 00:00:00);
--                 * ACS values such as 2620945.0 are cast to whole numbers (Step
--                   5 proved all 48 values are whole numbers);
--                 * local_date goes straight into the DATE column; local_time is
--                   NULL when blank and is otherwise cast to TIME with CASE.
--                   (CAST(NULLIF(local_time, '') AS TIME) must NOT be used: in
--                   MySQL 9.5 it turns 12:00:00 into 00:00:12. See the build log.)
--
-- Foreign keys stay switched on, so MySQL itself rejects any row whose parent is
-- missing. Everything runs in ONE transaction: if any statement fails, mysql
-- stops, the connection closes, and MySQL rolls back, so no table is left
-- half-filled. Nothing is saved until the COMMIT at the end.
--
-- Run from the repository root (reads only the staging tables, no CSV files):
--     mysql -u <your_mysql_user> -p --table < sql/06_populate_tables.sql
--
-- After each INSERT, "SHOW COUNT(*) WARNINGS" must report 0.

USE ticket_market_analytics;

START TRANSACTION;

-- 1. metro_area (from stg_market_label)
INSERT INTO metro_area (metro_area_geoid, census_metro_name, market_label)
SELECT metro_area_geoid, census_metro_name, market_label
FROM   stg_market_label
ORDER  BY metro_area_geoid;
SHOW COUNT(*) WARNINGS;   -- expected 0

-- 2. segment (distinct values in stg_event)
INSERT INTO segment (segment_id, segment)
SELECT DISTINCT segment_id, segment
FROM   stg_event
ORDER  BY segment_id;
SHOW COUNT(*) WARNINGS;   -- expected 0

-- 3. industry (distinct values in stg_cbp)
INSERT INTO industry (naics_code, naics_label)
SELECT DISTINCT naics_code, naics_label
FROM   stg_cbp
ORDER  BY naics_code;
SHOW COUNT(*) WARNINGS;   -- expected 0

-- 4. venue (from stg_venue)
INSERT INTO venue (venue_id, metro_area_geoid, venue_name, venue_address, venue_city,
                   venue_state, venue_postal_code, venue_latitude, venue_longitude)
SELECT venue_id,
       metro_area_geoid,
       REGEXP_REPLACE(venue_name, '^[[:space:]]+|[[:space:]]+$', ''),
       NULLIF(REGEXP_REPLACE(venue_address, '^[[:space:]]+|[[:space:]]+$', ''), ''),
       NULLIF(REGEXP_REPLACE(venue_city, '^[[:space:]]+|[[:space:]]+$', ''), ''),
       NULLIF(venue_state, ''),
       NULLIF(REGEXP_REPLACE(venue_postal_code, '^[[:space:]]+|[[:space:]]+$', ''), ''),
       CAST(NULLIF(venue_latitude, '')  AS DECIMAL(18,15)),
       CAST(NULLIF(venue_longitude, '') AS DECIMAL(18,15))
FROM   stg_venue
ORDER  BY venue_id;
SHOW COUNT(*) WARNINGS;   -- expected 0

-- 5. genre (distinct values in stg_event)
INSERT INTO genre (genre_id, segment_id, genre)
SELECT DISTINCT genre_id, segment_id, genre
FROM   stg_event
ORDER  BY genre_id;
SHOW COUNT(*) WARNINGS;   -- expected 0

-- 6. metro_demographic (from stg_acs; values like 2620945.0 become whole numbers)
INSERT INTO metro_demographic (metro_area_geoid, population, median_household_income)
SELECT metro_area_geoid,
       CAST(population AS DECIMAL(12,0)),
       CAST(median_household_income AS DECIMAL(12,0))
FROM   stg_acs
ORDER  BY metro_area_geoid;
SHOW COUNT(*) WARNINGS;   -- expected 0

-- 7. metro_industry (from stg_cbp; the blank El Paso counts become NULL)
INSERT INTO metro_industry (metro_area_geoid, naics_code, establishments, employees)
SELECT metro_area_geoid, naics_code, NULLIF(establishments, ''), NULLIF(employees, '')
FROM   stg_cbp
ORDER  BY metro_area_geoid, naics_code;
SHOW COUNT(*) WARNINGS;   -- expected 0

-- 8. event (from stg_event; segment_id, segment and genre are not stored here)
INSERT INTO event (event_id, venue_id, genre_id, event_name, event_url, status,
                   local_date, local_time, subgenre, ticketing_platform)
SELECT event_id,
       venue_id,
       genre_id,
       event_name,
       NULLIF(event_url, ''),
       status,
       local_date,
       CASE WHEN local_time = '' THEN NULL ELSE CAST(local_time AS TIME) END,
       NULLIF(subgenre, ''),
       NULLIF(ticketing_platform, '')
FROM   stg_event
ORDER  BY event_id;
SHOW COUNT(*) WARNINGS;   -- expected 0

COMMIT;

-- ---------------------------------------------------------------------------
-- Check: row counts of the 8 final tables (the full final checks are Step 7).
-- ---------------------------------------------------------------------------
SELECT table_name, expected, actual, IF(actual = expected, 'PASS', 'FAIL') AS result
FROM (
    SELECT 1 AS n, 'metro_area'        AS table_name, 24    AS expected, (SELECT COUNT(*) FROM metro_area)        AS actual
    UNION ALL SELECT 2, 'segment',           2,     (SELECT COUNT(*) FROM segment)
    UNION ALL SELECT 3, 'industry',          3,     (SELECT COUNT(*) FROM industry)
    UNION ALL SELECT 4, 'venue',             965,   (SELECT COUNT(*) FROM venue)
    UNION ALL SELECT 5, 'genre',             41,    (SELECT COUNT(*) FROM genre)
    UNION ALL SELECT 6, 'metro_demographic', 24,    (SELECT COUNT(*) FROM metro_demographic)
    UNION ALL SELECT 7, 'metro_industry',    72,    (SELECT COUNT(*) FROM metro_industry)
    UNION ALL SELECT 8, 'event',             10895, (SELECT COUNT(*) FROM event)
) t
ORDER BY n;
