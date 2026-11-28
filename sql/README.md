# SQL for the Phase 3 database build

Numbered scripts that build the `ticket_market_analytics` database. Run them in
order. The design behind them is recorded in `docs/project_decisions.md`
("2026-11-27: Phase 3 build decisions"), and each step's real results go in
`docs/database_build_log.md`.

## Requirements

- MySQL 8.0 or later.
- Your own MySQL user. Never put a password in a script or on the command line;
  `-p` makes `mysql` ask for it.
- The six `working_dedup_v5` CSV files (they are not in Git). They are only
  needed for the loading step; the scripts never change them.

## How to run a script

From the repository root:

```bash
mysql -u <your_mysql_user> -p --table < sql/01_create_database.sql
```

The loading step reads CSV files with `LOAD DATA LOCAL INFILE` and a **relative**
path, so it works on any machine. Run that script from the folder that
**contains** `working_dedup_v5/`, and give the script's path as before. The
folder is different on each machine, which is why the path is not written into
the script. The script's own comments say exactly how to run it.

## Scripts

| Script | Step |
|---|---|
| `01_create_database.sql` | Create the database (utf8mb4) |
| `02_create_tables.sql` | Create the 8 tables, keys and constraints, then run 5 checks |
| `03_create_staging_tables.sql` | Create the 5 staging tables (all-text copies of the CSVs), then run 4 checks |
| `04a_enable_local_infile.sql` | Temporarily allow `LOAD DATA LOCAL` (changes a global server setting) |
| `04b_load_staging.sql` | Load the 5 CSVs into the staging tables, then run 4 checks (needs `--local-infile=1`; run from the folder that contains `working_dedup_v5/`) |
| `04c_disable_local_infile.sql` | Switch `LOAD DATA LOCAL` off again, right after 04b |
| `05_validate_staging.sql` | Validate the staging data with 57 read-only checks (PASS/FAIL each) before anything is transferred |
| `06_populate_tables.sql` | Copy the validated staging data into the 8 final tables in one transaction, with the Decision 6 cleaning rules |
| `07_final_checks.sql` | 77 read-only final checks (PASS/FAIL each): structure, counts, orphans, every value against staging, nothing lost by normalizing, NULLs, spot values |
| `08_drop_staging_tables.sql` | Drop only the 5 staging tables (after Step 7 passes and the CSV checksums match); confirm exactly 8 tables remain |

More scripts are added as each step is completed and confirmed.

## Starting over

If a step has to be redone from the beginning, this removes **only** the project
database (no other database is touched) and the scripts can be run again from
`01`:

```bash
mysql -u <your_mysql_user> -p -e "DROP DATABASE ticket_market_analytics;"
```

This deletes everything in that database, so use it only before the real data
has been loaded and checked, or when you intend to reload everything.

## Redoing step 6 only

Step 6 runs in one transaction, so if a statement fails nothing is kept. If the
tables were filled but you need to repeat the step, empty them child-first
(this leaves the staging tables untouched), then run `06` again:

```sql
DELETE FROM event;
DELETE FROM genre;
DELETE FROM metro_industry;
DELETE FROM metro_demographic;
DELETE FROM venue;
DELETE FROM industry;
DELETE FROM segment;
DELETE FROM metro_area;
```
