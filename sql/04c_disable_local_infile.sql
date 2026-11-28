-- Step 4c of the Phase 3 build: switch LOAD DATA LOCAL INFILE off again.
--
-- Run this right after 04b, whether or not the load succeeded, so the global
-- server setting is back to its original value (OFF).
--
-- Run from the repository root:
--     mysql -u <your_mysql_user> -p --table < sql/04c_disable_local_infile.sql

SELECT @@GLOBAL.local_infile AS local_infile_before_expected_1;

SET GLOBAL local_infile = 0;

SELECT @@GLOBAL.local_infile AS local_infile_now_expected_0;
