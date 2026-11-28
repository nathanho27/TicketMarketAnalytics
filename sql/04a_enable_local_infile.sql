-- Step 4a of the Phase 3 build: temporarily allow LOAD DATA LOCAL INFILE.
--
-- This changes a GLOBAL server setting (local_infile). It is needed only for the
-- CSV load in 04b, and it is switched off again by 04c immediately afterwards.
-- (The setting would also return to OFF if the MySQL server restarted.)
-- It needs an account that may set global variables, such as root.
--
-- Run from the repository root:
--     mysql -u <your_mysql_user> -p --table < sql/04a_enable_local_infile.sql

SELECT @@GLOBAL.local_infile AS local_infile_before_expected_0;

SET GLOBAL local_infile = 1;

SELECT @@GLOBAL.local_infile AS local_infile_now_expected_1;
