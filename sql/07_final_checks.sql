-- Step 7 of the Phase 3 build: final checks on the populated tables.
--
-- Decision 5 (docs/project_decisions.md): the staging tables are dropped only
-- after ALL of these checks pass. This script only reads; it changes nothing.
--
-- The checks cover:
--   A  the structure is unchanged (tables, columns, foreign keys, collations, NULL rules);
--   B  row counts of the 8 tables;
--   C  no orphan rows for any foreign key, and no parent without children;
--   D  every value in the final tables equals its staging value after the
--      Decision 6 rules (rows missing, extra or different must be 0);
--   E  nothing was lost by splitting the data: segment, genre, naics_label and
--      market_label rebuilt through the new tables equal the original CSV columns;
--   F  NULLs, empty strings, invented times and leftover whitespace;
--   G  spot values computed independently from the CSV files with pandas.
--
-- Every check shows its expected value, the actual value and PASS or FAIL. The
-- last row, "FAILED CHECKS", must show 0. If anything shows FAIL, do not drop the
-- staging tables: paste the output and we will look at it together.
--
-- Run from the repository root:
--     mysql -u <your_mysql_user> -p --table < sql/07_final_checks.sql

USE ticket_market_analytics;

WITH results AS (
SELECT 1 AS n, 'tables in the database (8 final + 5 staging)' AS check_name, '13' AS expected, CAST((SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_TYPE = 'BASE TABLE') AS CHAR) AS actual
UNION ALL
SELECT 2 AS n, 'columns in the 8 final tables' AS check_name, '36' AS expected, CAST((SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME NOT LIKE 'stg\_%') AS CHAR) AS actual
UNION ALL
SELECT 3 AS n, 'foreign keys on the final tables (columns)' AS check_name, '7' AS expected, CAST((SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND REFERENCED_TABLE_NAME IS NOT NULL) AS CHAR) AS actual
UNION ALL
SELECT 4 AS n, 'foreign-key columns whose collation differs from the parent column' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE k JOIN information_schema.COLUMNS c ON c.TABLE_SCHEMA = k.TABLE_SCHEMA AND c.TABLE_NAME = k.TABLE_NAME AND c.COLUMN_NAME = k.COLUMN_NAME JOIN information_schema.COLUMNS p ON p.TABLE_SCHEMA = k.REFERENCED_TABLE_SCHEMA AND p.TABLE_NAME = k.REFERENCED_TABLE_NAME AND p.COLUMN_NAME = k.REFERENCED_COLUMN_NAME WHERE k.TABLE_SCHEMA = 'ticket_market_analytics' AND k.REFERENCED_TABLE_NAME IS NOT NULL AND NOT (c.COLLATION_NAME <=> p.COLLATION_NAME)) AS CHAR) AS actual
UNION ALL
SELECT 5 AS n, 'columns using utf8mb4_bin in the final tables' AS check_name, '7' AS expected, CAST((SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME NOT LIKE 'stg\_%' AND COLLATION_NAME = 'utf8mb4_bin') AS CHAR) AS actual
UNION ALL
SELECT 6 AS n, 'columns that allow NULL in the final tables' AS check_name, '12' AS expected, CAST((SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME NOT LIKE 'stg\_%' AND IS_NULLABLE = 'YES') AS CHAR) AS actual
UNION ALL
SELECT 7 AS n, 'UNIQUE keys on metro_area besides the primary key' AS check_name, '2' AS expected, CAST((SELECT COUNT(DISTINCT INDEX_NAME) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = 'ticket_market_analytics' AND TABLE_NAME = 'metro_area' AND NON_UNIQUE = 0 AND INDEX_NAME <> 'PRIMARY') AS CHAR) AS actual
UNION ALL
SELECT 8 AS n, 'rows in metro_area' AS check_name, '24' AS expected, CAST((SELECT COUNT(*) FROM metro_area) AS CHAR) AS actual
UNION ALL
SELECT 9 AS n, 'rows in segment' AS check_name, '2' AS expected, CAST((SELECT COUNT(*) FROM segment) AS CHAR) AS actual
UNION ALL
SELECT 10 AS n, 'rows in industry' AS check_name, '3' AS expected, CAST((SELECT COUNT(*) FROM industry) AS CHAR) AS actual
UNION ALL
SELECT 11 AS n, 'rows in venue' AS check_name, '965' AS expected, CAST((SELECT COUNT(*) FROM venue) AS CHAR) AS actual
UNION ALL
SELECT 12 AS n, 'rows in genre' AS check_name, '41' AS expected, CAST((SELECT COUNT(*) FROM genre) AS CHAR) AS actual
UNION ALL
SELECT 13 AS n, 'rows in metro_demographic' AS check_name, '24' AS expected, CAST((SELECT COUNT(*) FROM metro_demographic) AS CHAR) AS actual
UNION ALL
SELECT 14 AS n, 'rows in metro_industry' AS check_name, '72' AS expected, CAST((SELECT COUNT(*) FROM metro_industry) AS CHAR) AS actual
UNION ALL
SELECT 15 AS n, 'rows in event' AS check_name, '10895' AS expected, CAST((SELECT COUNT(*) FROM event) AS CHAR) AS actual
UNION ALL
SELECT 16 AS n, 'venue.metro_area_geoid rows with no matching metro_area row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM venue c LEFT JOIN metro_area p ON p.metro_area_geoid = c.metro_area_geoid WHERE p.metro_area_geoid IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 17 AS n, 'genre.segment_id rows with no matching segment row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM genre c LEFT JOIN segment p ON p.segment_id = c.segment_id WHERE p.segment_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 18 AS n, 'metro_demographic.metro_area_geoid rows with no matching metro_area row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM metro_demographic c LEFT JOIN metro_area p ON p.metro_area_geoid = c.metro_area_geoid WHERE p.metro_area_geoid IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 19 AS n, 'metro_industry.metro_area_geoid rows with no matching metro_area row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM metro_industry c LEFT JOIN metro_area p ON p.metro_area_geoid = c.metro_area_geoid WHERE p.metro_area_geoid IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 20 AS n, 'metro_industry.naics_code rows with no matching industry row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM metro_industry c LEFT JOIN industry p ON p.naics_code = c.naics_code WHERE p.naics_code IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 21 AS n, 'event.venue_id rows with no matching venue row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM event c LEFT JOIN venue p ON p.venue_id = c.venue_id WHERE p.venue_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 22 AS n, 'event.genre_id rows with no matching genre row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM event c LEFT JOIN genre p ON p.genre_id = c.genre_id WHERE p.genre_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 23 AS n, 'metro_area rows with no venue' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM metro_area m LEFT JOIN venue v ON v.metro_area_geoid = m.metro_area_geoid WHERE v.venue_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 24 AS n, 'venue rows with no event' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM venue v LEFT JOIN event e ON e.venue_id = v.venue_id WHERE e.event_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 25 AS n, 'genre rows with no event' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM genre g LEFT JOIN event e ON e.genre_id = g.genre_id WHERE e.event_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 26 AS n, 'segment rows with no genre' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM segment s LEFT JOIN genre g ON g.segment_id = s.segment_id WHERE g.genre_id IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 27 AS n, 'industry rows with no metro_industry row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM industry i LEFT JOIN metro_industry mi ON mi.naics_code = i.naics_code WHERE mi.naics_code IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 28 AS n, 'metro_area rows with no metro_demographic row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM metro_area m LEFT JOIN metro_demographic d ON d.metro_area_geoid = m.metro_area_geoid WHERE d.metro_area_geoid IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 29 AS n, 'metro_area rows without exactly 3 metro_industry rows' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM (SELECT m.metro_area_geoid FROM metro_area m LEFT JOIN metro_industry mi ON mi.metro_area_geoid = m.metro_area_geoid GROUP BY m.metro_area_geoid HAVING COUNT(mi.naics_code) <> 3) x) AS CHAR) AS actual
UNION ALL
SELECT 30 AS n, 'metro_area rows that differ from stg_market_label, or are missing or extra' AS check_name, '0' AS expected, CAST(((SELECT COUNT(*) FROM stg_market_label s LEFT JOIN metro_area t ON t.metro_area_geoid = s.metro_area_geoid AND BINARY t.census_metro_name = BINARY s.census_metro_name AND BINARY t.market_label = BINARY s.market_label WHERE t.metro_area_geoid IS NULL) + (SELECT COUNT(*) FROM metro_area t LEFT JOIN stg_market_label s ON s.metro_area_geoid = t.metro_area_geoid WHERE s.metro_area_geoid IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 31 AS n, 'segment rows that differ from the distinct values in stg_event, or are missing or extra' AS check_name, '0' AS expected, CAST(((SELECT COUNT(*) FROM (SELECT DISTINCT segment_id, segment FROM stg_event) s LEFT JOIN segment t ON t.segment_id = s.segment_id AND BINARY t.segment = BINARY s.segment WHERE t.segment_id IS NULL) + (SELECT COUNT(*) FROM segment t LEFT JOIN (SELECT DISTINCT segment_id FROM stg_event) s ON s.segment_id = t.segment_id WHERE s.segment_id IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 32 AS n, 'genre rows that differ from the distinct values in stg_event, or are missing or extra' AS check_name, '0' AS expected, CAST(((SELECT COUNT(*) FROM (SELECT DISTINCT genre_id, segment_id, genre FROM stg_event) s LEFT JOIN genre t ON t.genre_id = s.genre_id AND BINARY t.segment_id = BINARY s.segment_id AND BINARY t.genre = BINARY s.genre WHERE t.genre_id IS NULL) + (SELECT COUNT(*) FROM genre t LEFT JOIN (SELECT DISTINCT genre_id FROM stg_event) s ON s.genre_id = t.genre_id WHERE s.genre_id IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 33 AS n, 'industry rows that differ from the distinct values in stg_cbp, or are missing or extra' AS check_name, '0' AS expected, CAST(((SELECT COUNT(*) FROM (SELECT DISTINCT naics_code, naics_label FROM stg_cbp) s LEFT JOIN industry t ON t.naics_code = s.naics_code AND BINARY t.naics_label = BINARY s.naics_label WHERE t.naics_code IS NULL) + (SELECT COUNT(*) FROM industry t LEFT JOIN (SELECT DISTINCT naics_code FROM stg_cbp) s ON s.naics_code = t.naics_code WHERE s.naics_code IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 34 AS n, 'venue rows that differ from stg_venue (after the Decision 6 rules), or are missing or extra' AS check_name, '0' AS expected, CAST(((SELECT COUNT(*) FROM stg_venue s LEFT JOIN venue t ON t.venue_id = s.venue_id AND BINARY t.venue_name = BINARY REGEXP_REPLACE(s.venue_name, '^[[:space:]]+|[[:space:]]+$', '') AND BINARY t.venue_address <=> BINARY NULLIF(REGEXP_REPLACE(s.venue_address, '^[[:space:]]+|[[:space:]]+$', ''), '') AND BINARY t.venue_city <=> BINARY NULLIF(REGEXP_REPLACE(s.venue_city, '^[[:space:]]+|[[:space:]]+$', ''), '') AND BINARY t.venue_state <=> BINARY NULLIF(s.venue_state, '') AND BINARY t.venue_postal_code <=> BINARY NULLIF(REGEXP_REPLACE(s.venue_postal_code, '^[[:space:]]+|[[:space:]]+$', ''), '') AND t.venue_latitude <=> CAST(NULLIF(s.venue_latitude, '') AS DECIMAL(18,15)) AND t.venue_longitude <=> CAST(NULLIF(s.venue_longitude, '') AS DECIMAL(18,15)) AND t.metro_area_geoid = s.metro_area_geoid WHERE t.venue_id IS NULL) + (SELECT COUNT(*) FROM venue t LEFT JOIN stg_venue s ON s.venue_id = t.venue_id WHERE s.venue_id IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 35 AS n, 'metro_demographic rows that differ from stg_acs, or are missing or extra' AS check_name, '0' AS expected, CAST(((SELECT COUNT(*) FROM stg_acs s LEFT JOIN metro_demographic t ON t.metro_area_geoid = s.metro_area_geoid AND t.population = CAST(s.population AS DECIMAL(12,0)) AND t.median_household_income = CAST(s.median_household_income AS DECIMAL(12,0)) WHERE t.metro_area_geoid IS NULL) + (SELECT COUNT(*) FROM metro_demographic t LEFT JOIN stg_acs s ON s.metro_area_geoid = t.metro_area_geoid WHERE s.metro_area_geoid IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 36 AS n, 'metro_industry rows that differ from stg_cbp, or are missing or extra' AS check_name, '0' AS expected, CAST(((SELECT COUNT(*) FROM stg_cbp s LEFT JOIN metro_industry t ON t.metro_area_geoid = s.metro_area_geoid AND t.naics_code = s.naics_code AND t.establishments <=> (CASE WHEN s.establishments = '' THEN NULL ELSE CAST(s.establishments AS UNSIGNED) END) AND t.employees <=> (CASE WHEN s.employees = '' THEN NULL ELSE CAST(s.employees AS UNSIGNED) END) WHERE t.naics_code IS NULL) + (SELECT COUNT(*) FROM metro_industry t LEFT JOIN stg_cbp s ON s.metro_area_geoid = t.metro_area_geoid AND s.naics_code = t.naics_code WHERE s.naics_code IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 37 AS n, 'event rows that differ from stg_event (after the Decision 6 rules), or are missing or extra' AS check_name, '0' AS expected, CAST(((SELECT COUNT(*) FROM stg_event s LEFT JOIN event t ON t.event_id = s.event_id AND BINARY t.venue_id = BINARY s.venue_id AND BINARY t.genre_id = BINARY s.genre_id AND BINARY t.event_name = BINARY s.event_name AND BINARY t.event_url <=> BINARY NULLIF(s.event_url, '') AND BINARY t.status = BINARY s.status AND t.local_date = CAST(s.local_date AS DATE) AND t.local_time <=> (CASE WHEN s.local_time = '' THEN NULL ELSE CAST(s.local_time AS TIME) END) AND BINARY t.subgenre <=> BINARY NULLIF(s.subgenre, '') AND BINARY t.ticketing_platform <=> BINARY NULLIF(s.ticketing_platform, '') WHERE t.event_id IS NULL) + (SELECT COUNT(*) FROM event t LEFT JOIN stg_event s ON s.event_id = t.event_id WHERE s.event_id IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 38 AS n, 'event rows whose local_time differs from the source text (non-blank times)' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_event s JOIN event t ON t.event_id = s.event_id WHERE s.local_time <> '' AND (t.local_time IS NULL OR t.local_time <> CAST(s.local_time AS TIME))) AS CHAR) AS actual
UNION ALL
SELECT 39 AS n, 'events whose segment_id, segment or genre, rebuilt through genre and segment, differ from the original row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_event s JOIN event e ON e.event_id = s.event_id JOIN genre g ON g.genre_id = e.genre_id JOIN segment sg ON sg.segment_id = g.segment_id WHERE BINARY sg.segment_id <> BINARY s.segment_id OR BINARY sg.segment <> BINARY s.segment OR BINARY g.genre <> BINARY s.genre OR BINARY g.genre_id <> BINARY s.genre_id) AS CHAR) AS actual
UNION ALL
SELECT 40 AS n, 'metro_industry rows whose naics_label, rebuilt through industry, differs from the original row' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_cbp s JOIN metro_industry mi ON mi.metro_area_geoid = s.metro_area_geoid AND mi.naics_code = s.naics_code JOIN industry i ON i.naics_code = mi.naics_code WHERE BINARY i.naics_label <> BINARY s.naics_label) AS CHAR) AS actual
UNION ALL
SELECT 41 AS n, 'venues whose market_label, rebuilt through metro_area, differs from market_labels' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM stg_venue s JOIN venue v ON v.venue_id = s.venue_id JOIN metro_area m ON m.metro_area_geoid = v.metro_area_geoid JOIN stg_market_label l ON l.metro_area_geoid = s.metro_area_geoid WHERE BINARY m.market_label <> BINARY l.market_label) AS CHAR) AS actual
UNION ALL
SELECT 42 AS n, 'NULL local_time' AS check_name, '245' AS expected, CAST((SELECT COUNT(*) FROM event WHERE local_time IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 43 AS n, 'NULL subgenre' AS check_name, '8693' AS expected, CAST((SELECT COUNT(*) FROM event WHERE subgenre IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 44 AS n, 'NULL venue_address' AS check_name, '16' AS expected, CAST((SELECT COUNT(*) FROM venue WHERE venue_address IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 45 AS n, 'NULL establishments' AS check_name, '1' AS expected, CAST((SELECT COUNT(*) FROM metro_industry WHERE establishments IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 46 AS n, 'NULL employees' AS check_name, '1' AS expected, CAST((SELECT COUNT(*) FROM metro_industry WHERE employees IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 47 AS n, 'NULLs in the 7 other nullable columns (event_url, ticketing_platform, venue_city, venue_state, venue_postal_code, venue_latitude, venue_longitude)' AS check_name, '0' AS expected, CAST((SELECT (SELECT COUNT(*) FROM event WHERE event_url IS NULL OR ticketing_platform IS NULL) + (SELECT COUNT(*) FROM venue WHERE venue_city IS NULL OR venue_state IS NULL OR venue_postal_code IS NULL OR venue_latitude IS NULL OR venue_longitude IS NULL)) AS CHAR) AS actual
UNION ALL
SELECT 48 AS n, 'empty strings left in nullable text columns (blanks must be NULL, not empty text)' AS check_name, '0' AS expected, CAST((SELECT (SELECT COUNT(*) FROM event WHERE event_url = '' OR subgenre = '' OR ticketing_platform = '') + (SELECT COUNT(*) FROM venue WHERE venue_address = '' OR venue_city = '' OR venue_state = '' OR venue_postal_code = '')) AS CHAR) AS actual
UNION ALL
SELECT 49 AS n, 'events with an invented local_time of 00:00:00' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM event WHERE local_time = '00:00:00') AS CHAR) AS actual
UNION ALL
SELECT 50 AS n, 'venue text values with whitespace at the start or end' AS check_name, '0' AS expected, CAST((SELECT COUNT(*) FROM venue WHERE venue_name REGEXP '^[[:space:]]|[[:space:]]$' OR venue_address REGEXP '^[[:space:]]|[[:space:]]$' OR venue_city REGEXP '^[[:space:]]|[[:space:]]$' OR venue_postal_code REGEXP '^[[:space:]]|[[:space:]]$') AS CHAR) AS actual
UNION ALL
SELECT 51 AS n, 'Austin population (ACS file: 2620945.0)' AS check_name, '2620945' AS expected, CAST((SELECT population FROM metro_demographic WHERE metro_area_geoid = '12420') AS CHAR) AS actual
UNION ALL
SELECT 52 AS n, 'Austin median household income (ACS file: 102427.0)' AS check_name, '102427' AS expected, CAST((SELECT median_household_income FROM metro_demographic WHERE metro_area_geoid = '12420') AS CHAR) AS actual
UNION ALL
SELECT 53 AS n, 'sum of population over the 24 metros' AS check_name, '120585924' AS expected, CAST((SELECT SUM(population) FROM metro_demographic) AS CHAR) AS actual
UNION ALL
SELECT 54 AS n, 'sum of median_household_income over the 24 metros' AS check_name, '2390556' AS expected, CAST((SELECT SUM(median_household_income) FROM metro_demographic) AS CHAR) AS actual
UNION ALL
SELECT 55 AS n, 'Austin NAICS 7112 establishments' AS check_name, '28' AS expected, CAST((SELECT establishments FROM metro_industry WHERE metro_area_geoid = '12420' AND naics_code = '7112') AS CHAR) AS actual
UNION ALL
SELECT 56 AS n, 'Austin NAICS 711310 employees' AS check_name, '660' AS expected, CAST((SELECT employees FROM metro_industry WHERE metro_area_geoid = '12420' AND naics_code = '711310') AS CHAR) AS actual
UNION ALL
SELECT 57 AS n, 'El Paso NAICS 711320 row with NULL establishments and employees' AS check_name, '1' AS expected, CAST((SELECT COUNT(*) FROM metro_industry WHERE metro_area_geoid = '21340' AND naics_code = '711320' AND establishments IS NULL AND employees IS NULL) AS CHAR) AS actual
UNION ALL
SELECT 58 AS n, 'sum of establishments over all CBP rows' AS check_name, '5671' AS expected, CAST((SELECT SUM(establishments) FROM metro_industry) AS CHAR) AS actual
UNION ALL
SELECT 59 AS n, 'sum of employees over all CBP rows' AS check_name, '158097' AS expected, CAST((SELECT SUM(employees) FROM metro_industry) AS CHAR) AS actual
UNION ALL
SELECT 60 AS n, 'events in New York (event to venue to metro_area)' AS check_name, '2319' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN venue v ON v.venue_id = e.venue_id JOIN metro_area m ON m.metro_area_geoid = v.metro_area_geoid WHERE m.market_label = 'New York') AS CHAR) AS actual
UNION ALL
SELECT 61 AS n, 'events in Los Angeles (event to venue to metro_area)' AS check_name, '973' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN venue v ON v.venue_id = e.venue_id JOIN metro_area m ON m.metro_area_geoid = v.metro_area_geoid WHERE m.market_label = 'Los Angeles') AS CHAR) AS actual
UNION ALL
SELECT 62 AS n, 'events in Las Vegas (event to venue to metro_area)' AS check_name, '930' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN venue v ON v.venue_id = e.venue_id JOIN metro_area m ON m.metro_area_geoid = v.metro_area_geoid WHERE m.market_label = 'Las Vegas') AS CHAR) AS actual
UNION ALL
SELECT 63 AS n, 'events in El Paso (event to venue to metro_area)' AS check_name, '70' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN venue v ON v.venue_id = e.venue_id JOIN metro_area m ON m.metro_area_geoid = v.metro_area_geoid WHERE m.market_label = 'El Paso') AS CHAR) AS actual
UNION ALL
SELECT 64 AS n, 'venues in New York' AS check_name, '117' AS expected, CAST((SELECT COUNT(*) FROM venue v JOIN metro_area m ON m.metro_area_geoid = v.metro_area_geoid WHERE m.market_label = 'New York') AS CHAR) AS actual
UNION ALL
SELECT 65 AS n, 'events at the busiest venue (Mezzrow, rZ7HnEZ17OePV)' AS check_name, '253' AS expected, CAST((SELECT COUNT(*) FROM event WHERE venue_id = 'rZ7HnEZ17OePV') AS CHAR) AS actual
UNION ALL
SELECT 66 AS n, 'Music events (event to genre to segment)' AS check_name, '8689' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN genre g ON g.genre_id = e.genre_id JOIN segment s ON s.segment_id = g.segment_id WHERE s.segment = 'Music') AS CHAR) AS actual
UNION ALL
SELECT 67 AS n, 'Sports events (event to genre to segment)' AS check_name, '2206' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN genre g ON g.genre_id = e.genre_id JOIN segment s ON s.segment_id = g.segment_id WHERE s.segment = 'Sports') AS CHAR) AS actual
UNION ALL
SELECT 68 AS n, 'events with status onsale' AS check_name, '10291' AS expected, CAST((SELECT COUNT(*) FROM event WHERE status = 'onsale') AS CHAR) AS actual
UNION ALL
SELECT 69 AS n, 'events with status cancelled' AS check_name, '160' AS expected, CAST((SELECT COUNT(*) FROM event WHERE status = 'cancelled') AS CHAR) AS actual
UNION ALL
SELECT 70 AS n, 'events with genre Rock' AS check_name, '1676' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN genre g ON g.genre_id = e.genre_id WHERE g.genre = 'Rock') AS CHAR) AS actual
UNION ALL
SELECT 71 AS n, 'events with genre Jazz' AS check_name, '1387' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN genre g ON g.genre_id = e.genre_id WHERE g.genre = 'Jazz') AS CHAR) AS actual
UNION ALL
SELECT 72 AS n, 'events with genre Other' AS check_name, '1123' AS expected, CAST((SELECT COUNT(*) FROM event e JOIN genre g ON g.genre_id = e.genre_id WHERE g.genre = 'Other') AS CHAR) AS actual
UNION ALL
SELECT 73 AS n, 'earliest local_date' AS check_name, '2026-11-12' AS expected, CAST((SELECT MIN(local_date) FROM event) AS CHAR) AS actual
UNION ALL
SELECT 74 AS n, 'latest local_date' AS check_name, '2027-01-31' AS expected, CAST((SELECT MAX(local_date) FROM event) AS CHAR) AS actual
UNION ALL
SELECT 75 AS n, 'distinct event names (exact comparison)' AS check_name, '7030' AS expected, CAST((SELECT COUNT(DISTINCT BINARY event_name) FROM event) AS CHAR) AS actual
UNION ALL
SELECT 76 AS n, 'sum of venue_latitude (rounded to 6 decimals)' AS check_name, '35867.716865' AS expected, CAST((SELECT ROUND(SUM(venue_latitude), 6) FROM venue) AS CHAR) AS actual
UNION ALL
SELECT 77 AS n, 'sum of venue_longitude (rounded to 6 decimals)' AS check_name, '-92871.581492' AS expected, CAST((SELECT ROUND(SUM(venue_longitude), 6) FROM venue) AS CHAR) AS actual
)
SELECT n, check_name, expected, actual, IF(actual = expected, 'PASS', 'FAIL') AS result
FROM   results
UNION ALL
SELECT 999, 'FAILED CHECKS (must be 0)', '0', CAST(SUM(actual <> expected) AS CHAR),
       IF(SUM(actual <> expected) = 0, 'PASS', 'FAIL')
FROM   results
ORDER  BY n;
