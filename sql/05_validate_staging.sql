-- Step 5 of the Phase 3 build: validate the staging data BEFORE it is transferred.
--
-- Decisions: docs/project_decisions.md, "2026-11-27: Phase 3 build decisions"
--   Decision 5: staging data is validated before it is copied into the final
--               tables; every check must pass, or we stop and log the problem.
--   Decision 6: expected counts for stray whitespace and blank cells, and the
--               ACS whole-number check that must pass before the values are cast.
--
-- This script only reads the staging tables. It changes nothing.
--
-- Every check shows its expected value, the actual value and PASS or FAIL. The
-- last row, "FAILED CHECKS", must show 0. If anything shows FAIL, do not go on
-- to Step 6: paste the output and we will look at it together.
--
-- Run from the repository root:
--     mysql -u <your_mysql_user> -p --table < sql/05_validate_staging.sql

USE ticket_market_analytics;

WITH results AS (
SELECT 1 AS n, 'rows in stg_event' AS check_name, '10895' AS expected, CAST((SELECT COUNT(*) FROM stg_event) AS CHAR) AS actual
UNION ALL
SELECT 2 AS n, 'rows in stg_venue' AS check_name, '965' AS expected, CAST((SELECT COUNT(*) FROM stg_venue) AS CHAR) AS actual
UNION ALL
SELECT 3 AS n, 'rows in stg_market_label' AS check_name, '24' AS expected, CAST((SELECT COUNT(*) FROM stg_market_label) AS CHAR) AS actual
UNION ALL
SELECT 4 AS n, 'rows in stg_acs' AS check_name, '24' AS expected, CAST((SELECT COUNT(*) FROM stg_acs) AS CHAR) AS actual
UNION ALL
SELECT 5 AS n, 'rows in stg_cbp' AS check_name, '72' AS expected, CAST((SELECT COUNT(*) FROM stg_cbp) AS CHAR) AS actual
UNION ALL
SELECT 6 AS n, 'genre_id with more than one segment_id or genre' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM (SELECT genre_id FROM stg_event GROUP BY genre_id HAVING COUNT(DISTINCT segment_id) > 1 OR COUNT(DISTINCT genre) > 1) x) AS CHAR) AS actual
UNION ALL
SELECT 7 AS n, 'segment_id with more than one segment name' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM (SELECT segment_id FROM stg_event GROUP BY segment_id HAVING COUNT(DISTINCT segment) > 1) x) AS CHAR) AS actual
UNION ALL
SELECT 8 AS n, 'naics_code with more than one naics_label' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM (SELECT naics_code FROM stg_cbp GROUP BY naics_code HAVING COUNT(DISTINCT naics_label) > 1) x) AS CHAR) AS actual
UNION ALL
SELECT 9 AS n, 'distinct segment_id values in stg_event' AS check_name, '2' AS expected, CAST((SELECT COUNT(DISTINCT segment_id) FROM stg_event) AS CHAR) AS actual
UNION ALL
SELECT 10 AS n, 'distinct genre_id values in stg_event (case-sensitive)' AS check_name, '41' AS expected, CAST((SELECT COUNT(DISTINCT genre_id) FROM stg_event) AS CHAR) AS actual
UNION ALL
SELECT 11 AS n, 'distinct naics_code values in stg_cbp' AS check_name, '3' AS expected, CAST((SELECT COUNT(DISTINCT naics_code) FROM stg_cbp) AS CHAR) AS actual
UNION ALL
SELECT 12 AS n, 'distinct status values in stg_event' AS check_name, '4' AS expected, CAST((SELECT COUNT(DISTINCT status) FROM stg_event) AS CHAR) AS actual
UNION ALL
SELECT 13 AS n, 'duplicate event_id in stg_event' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) - COUNT(DISTINCT event_id) FROM stg_event) AS CHAR) AS actual
UNION ALL
SELECT 14 AS n, 'duplicate venue_id in stg_venue' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) - COUNT(DISTINCT venue_id) FROM stg_venue) AS CHAR) AS actual
UNION ALL
SELECT 15 AS n, 'duplicate metro_area_geoid in stg_market_label' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) - COUNT(DISTINCT metro_area_geoid) FROM stg_market_label) AS CHAR) AS actual
UNION ALL
SELECT 16 AS n, 'duplicate census_metro_name in stg_market_label' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) - COUNT(DISTINCT census_metro_name) FROM stg_market_label) AS CHAR) AS actual
UNION ALL
SELECT 17 AS n, 'duplicate market_label in stg_market_label' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) - COUNT(DISTINCT market_label) FROM stg_market_label) AS CHAR) AS actual
UNION ALL
SELECT 18 AS n, 'duplicate metro_area_geoid in stg_acs' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) - COUNT(DISTINCT metro_area_geoid) FROM stg_acs) AS CHAR) AS actual
UNION ALL
SELECT 19 AS n, 'duplicate (metro_area_geoid, naics_code) in stg_cbp' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) - COUNT(DISTINCT metro_area_geoid, naics_code) FROM stg_cbp) AS CHAR) AS actual
UNION ALL
SELECT 20 AS n, 'stg_event rows blank in a NOT NULL column' AS check_name, '0' AS expected, (SELECT CAST(COALESCE(SUM((event_id = '' OR event_id IS NULL) OR (venue_id = '' OR venue_id IS NULL) OR (genre_id = '' OR genre_id IS NULL) OR (genre = '' OR genre IS NULL) OR (segment_id = '' OR segment_id IS NULL) OR (segment = '' OR segment IS NULL) OR (event_name = '' OR event_name IS NULL) OR (status = '' OR status IS NULL) OR (local_date = '' OR local_date IS NULL)),0) AS CHAR) FROM stg_event) AS actual
UNION ALL
SELECT 21 AS n, 'stg_venue rows blank in a NOT NULL column' AS check_name, '0' AS expected, (SELECT CAST(COALESCE(SUM((venue_id = '' OR venue_id IS NULL) OR (metro_area_geoid = '' OR metro_area_geoid IS NULL) OR (venue_name = '' OR venue_name IS NULL)),0) AS CHAR) FROM stg_venue) AS actual
UNION ALL
SELECT 22 AS n, 'stg_market_label rows blank in any column' AS check_name, '0' AS expected, (SELECT CAST(COALESCE(SUM((metro_area_geoid = '' OR metro_area_geoid IS NULL) OR (census_metro_name = '' OR census_metro_name IS NULL) OR (market_label = '' OR market_label IS NULL)),0) AS CHAR) FROM stg_market_label) AS actual
UNION ALL
SELECT 23 AS n, 'stg_acs rows blank in any column' AS check_name, '0' AS expected, (SELECT CAST(COALESCE(SUM((metro_area_geoid = '' OR metro_area_geoid IS NULL) OR (population = '' OR population IS NULL) OR (median_household_income = '' OR median_household_income IS NULL)),0) AS CHAR) FROM stg_acs) AS actual
UNION ALL
SELECT 24 AS n, 'stg_cbp rows blank in a NOT NULL column' AS check_name, '0' AS expected, (SELECT CAST(COALESCE(SUM((metro_area_geoid = '' OR metro_area_geoid IS NULL) OR (naics_code = '' OR naics_code IS NULL) OR (naics_label = '' OR naics_label IS NULL)),0) AS CHAR) FROM stg_cbp) AS actual
UNION ALL
SELECT 25 AS n, 'stg_event.venue_id not found in stg_venue' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_event e LEFT JOIN stg_venue v ON v.venue_id = e.venue_id WHERE v.venue_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 26 AS n, 'stg_venue.metro_area_geoid not found in stg_market_label' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_venue v LEFT JOIN stg_market_label m ON m.metro_area_geoid = v.metro_area_geoid WHERE m.metro_area_geoid IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 27 AS n, 'stg_acs.metro_area_geoid not found in stg_market_label' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_acs a LEFT JOIN stg_market_label m ON m.metro_area_geoid = a.metro_area_geoid WHERE m.metro_area_geoid IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 28 AS n, 'stg_cbp.metro_area_geoid not found in stg_market_label' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_cbp b LEFT JOIN stg_market_label m ON m.metro_area_geoid = b.metro_area_geoid WHERE m.metro_area_geoid IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 29 AS n, 'metros in stg_market_label with no row in stg_acs' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_market_label m LEFT JOIN stg_acs a ON a.metro_area_geoid = m.metro_area_geoid WHERE a.metro_area_geoid IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 30 AS n, 'metros in stg_market_label without exactly 3 rows in stg_cbp' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM (SELECT m.metro_area_geoid FROM stg_market_label m LEFT JOIN stg_cbp b ON b.metro_area_geoid = m.metro_area_geoid GROUP BY m.metro_area_geoid HAVING COUNT(b.naics_code) <> 3) x) AS CHAR) AS actual
UNION ALL
SELECT 31 AS n, 'venues in stg_venue with no event' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_venue v LEFT JOIN stg_event e ON e.venue_id = v.venue_id WHERE e.venue_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 32 AS n, 'venue_name values with leading or trailing whitespace' AS check_name, '12' AS expected, (SELECT CAST(COALESCE(SUM(BINARY venue_name <> BINARY REGEXP_REPLACE(venue_name, '^[[:space:]]+|[[:space:]]+$', '')),0) AS CHAR) FROM stg_venue) AS actual
UNION ALL
SELECT 33 AS n, 'venue_address values with leading or trailing whitespace' AS check_name, '17' AS expected, (SELECT CAST(COALESCE(SUM(BINARY venue_address <> BINARY REGEXP_REPLACE(venue_address, '^[[:space:]]+|[[:space:]]+$', '')),0) AS CHAR) FROM stg_venue) AS actual
UNION ALL
SELECT 34 AS n, 'venue_city values with leading or trailing whitespace' AS check_name, '2' AS expected, (SELECT CAST(COALESCE(SUM(BINARY venue_city <> BINARY REGEXP_REPLACE(venue_city, '^[[:space:]]+|[[:space:]]+$', '')),0) AS CHAR) FROM stg_venue) AS actual
UNION ALL
SELECT 35 AS n, 'venue_postal_code values with leading or trailing whitespace' AS check_name, '3' AS expected, (SELECT CAST(COALESCE(SUM(BINARY venue_postal_code <> BINARY REGEXP_REPLACE(venue_postal_code, '^[[:space:]]+|[[:space:]]+$', '')),0) AS CHAR) FROM stg_venue) AS actual
UNION ALL
SELECT 36 AS n, 'rows with whitespace at the ends of any column NOT being trimmed' AS check_name, '0' AS expected, CAST((SELECT COALESCE(SUM(event_id REGEXP '^[[:space:]]|[[:space:]]$' OR event_name REGEXP '^[[:space:]]|[[:space:]]$' OR event_url REGEXP '^[[:space:]]|[[:space:]]$' OR status REGEXP '^[[:space:]]|[[:space:]]$' OR local_date REGEXP '^[[:space:]]|[[:space:]]$' OR local_time REGEXP '^[[:space:]]|[[:space:]]$' OR segment_id REGEXP '^[[:space:]]|[[:space:]]$' OR segment REGEXP '^[[:space:]]|[[:space:]]$' OR genre_id REGEXP '^[[:space:]]|[[:space:]]$' OR genre REGEXP '^[[:space:]]|[[:space:]]$' OR subgenre REGEXP '^[[:space:]]|[[:space:]]$' OR venue_id REGEXP '^[[:space:]]|[[:space:]]$' OR ticketing_platform REGEXP '^[[:space:]]|[[:space:]]$'),0) FROM stg_event) + (SELECT COALESCE(SUM(venue_id REGEXP '^[[:space:]]|[[:space:]]$' OR venue_state REGEXP '^[[:space:]]|[[:space:]]$' OR venue_latitude REGEXP '^[[:space:]]|[[:space:]]$' OR venue_longitude REGEXP '^[[:space:]]|[[:space:]]$' OR metro_area_geoid REGEXP '^[[:space:]]|[[:space:]]$'),0) FROM stg_venue) + (SELECT COALESCE(SUM(metro_area_geoid REGEXP '^[[:space:]]|[[:space:]]$' OR census_metro_name REGEXP '^[[:space:]]|[[:space:]]$' OR market_label REGEXP '^[[:space:]]|[[:space:]]$'),0) FROM stg_market_label) + (SELECT COALESCE(SUM(metro_area_geoid REGEXP '^[[:space:]]|[[:space:]]$' OR population REGEXP '^[[:space:]]|[[:space:]]$' OR median_household_income REGEXP '^[[:space:]]|[[:space:]]$'),0) FROM stg_acs) + (SELECT COALESCE(SUM(metro_area_geoid REGEXP '^[[:space:]]|[[:space:]]$' OR naics_code REGEXP '^[[:space:]]|[[:space:]]$' OR naics_label REGEXP '^[[:space:]]|[[:space:]]$' OR establishments REGEXP '^[[:space:]]|[[:space:]]$' OR employees REGEXP '^[[:space:]]|[[:space:]]$'),0) FROM stg_cbp) AS CHAR) AS actual
UNION ALL
SELECT 37 AS n, 'blank local_time' AS check_name, '245' AS expected, (SELECT CAST(COALESCE(SUM((local_time = '' OR local_time IS NULL)),0) AS CHAR) FROM stg_event) AS actual
UNION ALL
SELECT 38 AS n, 'blank subgenre' AS check_name, '8693' AS expected, (SELECT CAST(COALESCE(SUM((subgenre = '' OR subgenre IS NULL)),0) AS CHAR) FROM stg_event) AS actual
UNION ALL
SELECT 39 AS n, 'blank venue_address' AS check_name, '16' AS expected, (SELECT CAST(COALESCE(SUM((venue_address = '' OR venue_address IS NULL)),0) AS CHAR) FROM stg_venue) AS actual
UNION ALL
SELECT 40 AS n, 'blank establishments' AS check_name, '1' AS expected, (SELECT CAST(COALESCE(SUM((establishments = '' OR establishments IS NULL)),0) AS CHAR) FROM stg_cbp) AS actual
UNION ALL
SELECT 41 AS n, 'blank employees' AS check_name, '1' AS expected, (SELECT CAST(COALESCE(SUM((employees = '' OR employees IS NULL)),0) AS CHAR) FROM stg_cbp) AS actual
UNION ALL
SELECT 42 AS n, 'blanks in the 7 other nullable columns (event_url, ticketing_platform, venue_city, venue_state, venue_postal_code, venue_latitude, venue_longitude)' AS check_name, '0' AS expected, CAST((SELECT COALESCE(SUM((event_url = '' OR event_url IS NULL)),0) + COALESCE(SUM((ticketing_platform = '' OR ticketing_platform IS NULL)),0) FROM stg_event) + (SELECT COALESCE(SUM((venue_city = '' OR venue_city IS NULL)),0) + COALESCE(SUM((venue_state = '' OR venue_state IS NULL)),0) + COALESCE(SUM((venue_postal_code = '' OR venue_postal_code IS NULL)),0) + COALESCE(SUM((venue_latitude = '' OR venue_latitude IS NULL)),0) + COALESCE(SUM((venue_longitude = '' OR venue_longitude IS NULL)),0) FROM stg_venue) AS CHAR) AS actual
UNION ALL
SELECT 43 AS n, 'ACS population values that are digits followed by .0' AS check_name, '24' AS expected, CAST((SELECT COUNT(*) FROM stg_acs WHERE population REGEXP '^[0-9]+\\.0$') AS CHAR) AS actual
UNION ALL
SELECT 44 AS n, 'ACS median_household_income values that are digits followed by .0' AS check_name, '24' AS expected, CAST((SELECT COUNT(*) FROM stg_acs WHERE median_household_income REGEXP '^[0-9]+\\.0$') AS CHAR) AS actual
UNION ALL
SELECT 45 AS n, 'ACS values above the INT limit 2147483647' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_acs WHERE CAST(population AS DECIMAL(20,1)) > 2147483647 OR CAST(median_household_income AS DECIMAL(20,1)) > 2147483647) AS CHAR) AS actual
UNION ALL
SELECT 46 AS n, 'CBP non-blank establishments' AS check_name, '71' AS expected, CAST((SELECT COUNT(*) FROM stg_cbp WHERE establishments <> '') AS CHAR) AS actual
UNION ALL
SELECT 47 AS n, 'CBP non-blank employees' AS check_name, '71' AS expected, CAST((SELECT COUNT(*) FROM stg_cbp WHERE employees <> '') AS CHAR) AS actual
UNION ALL
SELECT 48 AS n, 'CBP non-blank establishments or employees that are not digits only' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_cbp WHERE (establishments <> '' AND establishments NOT REGEXP '^[0-9]+$') OR (employees <> '' AND employees NOT REGEXP '^[0-9]+$')) AS CHAR) AS actual
UNION ALL
SELECT 49 AS n, 'local_date not in YYYY-MM-DD form or not a real date' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_event WHERE local_date NOT REGEXP '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR STR_TO_DATE(local_date, '%Y-%m-%d') IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 50 AS n, 'non-blank local_time not in HH:MM:SS form' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_event WHERE local_time <> '' AND local_time NOT REGEXP '^[0-9]{2}:[0-9]{2}:[0-9]{2}$') AS CHAR) AS actual
UNION ALL
SELECT 51 AS n, 'venue_postal_code (after trimming) not exactly 5 digits' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_venue WHERE venue_postal_code <> '' AND REGEXP_REPLACE(venue_postal_code, '^[[:space:]]+|[[:space:]]+$', '') NOT REGEXP '^[0-9]{5}$') AS CHAR) AS actual
UNION ALL
SELECT 52 AS n, 'latitude or longitude not a decimal number that fits DECIMAL(18,15)' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_venue WHERE (venue_latitude <> '' AND venue_latitude NOT REGEXP '^-?[0-9]{1,3}(\\.[0-9]{1,15})?$') OR (venue_longitude <> '' AND venue_longitude NOT REGEXP '^-?[0-9]{1,3}(\\.[0-9]{1,15})?$')) AS CHAR) AS actual
UNION ALL
SELECT 53 AS n, 'stg_event values that do not fit the final column length' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_event WHERE CHAR_LENGTH(event_id) > 25 OR CHAR_LENGTH(venue_id) > 15 OR CHAR_LENGTH(genre_id) <> 11 OR CHAR_LENGTH(segment_id) <> 18 OR CHAR_LENGTH(event_name) > 400 OR CHAR_LENGTH(event_url) > 255 OR CHAR_LENGTH(status) > 12 OR CHAR_LENGTH(subgenre) > 30 OR CHAR_LENGTH(ticketing_platform) > 40 OR CHAR_LENGTH(genre) > 30 OR CHAR_LENGTH(segment) > 20) AS CHAR) AS actual
UNION ALL
SELECT 54 AS n, 'stg_venue values that do not fit the final column length (after trimming)' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_venue WHERE CHAR_LENGTH(venue_id) > 15 OR CHAR_LENGTH(REGEXP_REPLACE(venue_name, '^[[:space:]]+|[[:space:]]+$', '')) > 80 OR CHAR_LENGTH(REGEXP_REPLACE(venue_address, '^[[:space:]]+|[[:space:]]+$', '')) > 60 OR CHAR_LENGTH(REGEXP_REPLACE(venue_city, '^[[:space:]]+|[[:space:]]+$', '')) > 40 OR CHAR_LENGTH(venue_state) > 2 OR CHAR_LENGTH(metro_area_geoid) <> 5) AS CHAR) AS actual
UNION ALL
SELECT 55 AS n, 'stg_market_label values that do not fit the final column length' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_market_label WHERE CHAR_LENGTH(metro_area_geoid) <> 5 OR CHAR_LENGTH(census_metro_name) > 80 OR CHAR_LENGTH(market_label) > 30) AS CHAR) AS actual
UNION ALL
SELECT 56 AS n, 'stg_acs metro_area_geoid not exactly 5 characters' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_acs WHERE CHAR_LENGTH(metro_area_geoid) <> 5) AS CHAR) AS actual
UNION ALL
SELECT 57 AS n, 'stg_cbp values that do not fit the final column length' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_cbp WHERE CHAR_LENGTH(metro_area_geoid) <> 5 OR CHAR_LENGTH(naics_code) > 6 OR CHAR_LENGTH(naics_label) > 100) AS CHAR) AS actual
)
SELECT n, check_name, expected, actual, IF(actual = expected, 'PASS', 'FAIL') AS result
FROM   results
UNION ALL
SELECT 999, 'FAILED CHECKS (must be 0)', '0', CAST(SUM(actual <> expected) AS CHAR),
       IF(SUM(actual <> expected) = 0, 'PASS', 'FAIL')
FROM   results
ORDER  BY n;
