-- Step 1 of the Phase 3 build: create the project database.
--
-- Decisions: docs/project_decisions.md, "2026-11-27: Phase 3 build decisions"
--   Decision 1: database name ticket_market_analytics, character set utf8mb4.
--   Decision 2: every text column except the four Ticketmaster ID columns keeps
--               the database default collation utf8mb4_0900_ai_ci. It is written
--               out below so the database is identical on every MySQL 8.0+ server.
--
-- Requires MySQL 8.0 or later (utf8mb4_0900_ai_ci does not exist before 8.0).
--
-- Run it from any folder (no data files are read in this step):
--     mysql -u <your_mysql_user> -p --table < sql/01_create_database.sql
-- Do not put a password in this file or on the command line.
--
-- There is deliberately no "IF NOT EXISTS": if the database already exists, MySQL
-- stops with error 1007 so an existing database is never reused by accident.

-- Before: the database must not exist yet (this should return no rows).
SHOW DATABASES LIKE 'ticket_market_analytics';

CREATE DATABASE ticket_market_analytics
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

-- After: confirm the database and its defaults.
SELECT SCHEMA_NAME              AS database_name,
       DEFAULT_CHARACTER_SET_NAME AS character_set,
       DEFAULT_COLLATION_NAME     AS collation
FROM   information_schema.SCHEMATA
WHERE  SCHEMA_NAME = 'ticket_market_analytics';

-- The new database has no tables yet (this should return no rows).
SELECT TABLE_NAME
FROM   information_schema.TABLES
WHERE  TABLE_SCHEMA = 'ticket_market_analytics';
