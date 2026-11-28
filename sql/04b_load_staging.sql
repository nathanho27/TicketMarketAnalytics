-- Step 4b of the Phase 3 build: load the five CSVs into the staging tables.
--
-- Decisions: docs/project_decisions.md, "2026-11-27: Phase 3 build decisions"
--   Decision 5: the CSVs are only read; nothing is written back to them.
--   Decision 6: CHARACTER SET utf8mb4; fields separated by commas and
--               optionally enclosed in double quotes; Unix line endings; the
--               header row is skipped.
--
-- The CSV paths below are RELATIVE, so the script works on every machine. Run it
-- from the folder that CONTAINS the working_dedup_v5 folder:
--   Nathan:  data/processed/working_2026-11-10_222442
--   Nick:    the "processed copy" folder
-- and give the script's path from there, for example (Nathan, from the repo root):
--     cd data/processed/working_2026-11-10_222442
--     mysql -u <your_mysql_user> -p --local-infile=1 --default-character-set=utf8mb4 --table < ../../../sql/04b_load_staging.sql
--
-- Needs 04a first (server side) and the --local-infile=1 flag (client side).
-- Run 04c afterwards, whether or not this script succeeds.
--
-- After each load, "SHOW COUNT(*) WARNINGS" must report 0.

USE ticket_market_analytics;

LOAD DATA LOCAL INFILE 'working_dedup_v5/working_events.csv'
INTO TABLE stg_event
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
SHOW COUNT(*) WARNINGS;   -- expected 0

LOAD DATA LOCAL INFILE 'working_dedup_v5/working_venues.csv'
INTO TABLE stg_venue
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
SHOW COUNT(*) WARNINGS;   -- expected 0

LOAD DATA LOCAL INFILE 'working_dedup_v5/market_labels.csv'
INTO TABLE stg_market_label
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
SHOW COUNT(*) WARNINGS;   -- expected 0

LOAD DATA LOCAL INFILE 'working_dedup_v5/working_acs1_2025_metros.csv'
INTO TABLE stg_acs
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
SHOW COUNT(*) WARNINGS;   -- expected 0

LOAD DATA LOCAL INFILE 'working_dedup_v5/working_cbp2023_metros.csv'
INTO TABLE stg_cbp
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;
SHOW COUNT(*) WARNINGS;   -- expected 0

-- ---------------------------------------------------------------------------
-- Checks: compare each result with the expected value in its heading.
-- ---------------------------------------------------------------------------

-- Check A: row counts equal the CSV data rows (header excluded).
SELECT (SELECT COUNT(*) FROM stg_event)        AS stg_event_expected_10895,
       (SELECT COUNT(*) FROM stg_venue)        AS stg_venue_expected_965,
       (SELECT COUNT(*) FROM stg_market_label) AS stg_market_label_expected_24,
       (SELECT COUNT(*) FROM stg_acs)          AS stg_acs_expected_24,
       (SELECT COUNT(*) FROM stg_cbp)          AS stg_cbp_expected_72;

-- Check B: distinct IDs under case-sensitive comparison (IDs that differ only in
-- letter case must stay separate).
SELECT COUNT(DISTINCT event_id)   AS event_ids_expected_10895,
       COUNT(DISTINCT venue_id)   AS event_venue_ids_expected_965,
       COUNT(DISTINCT genre_id)   AS genre_ids_expected_41,
       COUNT(DISTINCT segment_id) AS segment_ids_expected_2
FROM   stg_event;
SELECT COUNT(DISTINCT venue_id) AS venue_ids_expected_965 FROM stg_venue;

-- Check C: special characters arrived intact in event names.
SELECT SUM(event_name LIKE '%"%')                       AS with_double_quote_expected_62,
       SUM(event_name LIKE '%,%')                       AS with_comma_expected_558,
       SUM(LENGTH(event_name) <> CHAR_LENGTH(event_name)) AS with_non_ascii_expected_268,
       SUM(event_name LIKE '% | %')                     AS with_pipe_expected_68,
       MAX(CHAR_LENGTH(event_name))                     AS longest_name_expected_347
FROM   stg_event;

-- Check D: a few rows to look at.
SELECT event_id, event_name, local_date, local_time, genre, venue_id
FROM   stg_event
ORDER  BY event_id
LIMIT  3;
SELECT * FROM stg_market_label ORDER BY metro_area_geoid LIMIT 3;
