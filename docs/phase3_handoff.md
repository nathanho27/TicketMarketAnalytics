# Phase 3 handoff for Nick

Written on Friday 2026-11-27 (evening) from Nathan's working session with
Claude. **Phase 3 is due Monday, November 30, 2026 at 11:59 PM.**

Nathan built and checked the database on his Mac. Everything you need to
reproduce it is already in the repository, so you do not need to design,
write or change anything to get the same database on your machine. This
document says what was done, why, exactly how to reproduce it, and what is
left.

## 1. The short version

1. `git pull`.
2. Read sections 3 and 4 (10 minutes) so you can explain the design.
3. Reproduce the build on your machine with the scripts in `sql/`
   (section 5, about 20 minutes). Your numbers should equal Nathan's.
4. Record your results in `docs/database_build_log.md` (entries tagged with
   your name) and confirm the six decisions in `docs/project_decisions.md`.
5. Then the remaining work (section 9): column descriptions, at least six
   business questions, and the 3 to 4 page report.

You do **not** need to recreate scripts, redesign tables or change the ERD.
If a step does not give the expected result, **stop and tell Nathan**; do not
edit a script to make it pass.

## 2. What was accomplished (Phase 3, Nov 27)

- Phase 3 started; `CLAUDE.md` now says Phase 3 and lists the requirements.
- Nathan's MySQL (9.5.0) was inspected and its settings recorded.
- **Six build decisions** were made and recorded (section 4).
- **Eight numbered SQL scripts** (`sql/01` to `sql/08`) were written. Each
  was rehearsed on a throwaway MySQL server first, then run by Nathan.
- The database `ticket_market_analytics` was built and loaded from the
  finalized `working_dedup_v5` files: **8 tables, 36 columns, 7 foreign
  keys, 12,026 rows in total across the tables** (counts in section 3).
- **134 checks** ran on the data (57 on staging, 77 on the final tables) plus
  14 after cleanup. All passed.
- The six CSV files were never changed (checksums recorded before the build
  and re-verified before cleanup).
- The staging tables were dropped only after every check passed.
- `local_infile` (a global MySQL setting needed for loading CSVs) was turned
  on only for the load and turned off again.
- The **data dictionary metadata** was extracted and verified against the
  approved design. The column descriptions are still to be written.

## 3. The database as built

Database `ticket_market_analytics` (character set `utf8mb4`, default
collation `utf8mb4_0900_ai_ci`). Table names are the ERD entities in
lowercase.

| Table (ERD entity) | Rows | Primary key | Foreign keys | Columns |
|---|---|---|---|---|
| `metro_area` (METRO_AREA) | 24 | `metro_area_geoid` | none | `census_metro_name` (unique), `market_label` (unique) |
| `segment` (SEGMENT) | 2 | `segment_id` | none | `segment` |
| `industry` (INDUSTRY) | 3 | `naics_code` | none | `naics_label` |
| `venue` (VENUE) | 965 | `venue_id` | `metro_area_geoid` to `metro_area` | name, address, city, state, postal code, latitude, longitude |
| `genre` (GENRE) | 41 | `genre_id` | `segment_id` to `segment` | `genre` |
| `metro_demographic` (METRO_DEMOGRAPHIC) | 24 | `metro_area_geoid` | the same column to `metro_area` | `population`, `median_household_income` |
| `metro_industry` (METRO_INDUSTRY) | 72 | `metro_area_geoid` + `naics_code` | both columns | `establishments`, `employees` |
| `event` (EVENT) | 10,895 | `event_id` | `venue_id` to `venue`; `genre_id` to `genre` | name, URL, status, date, time, subgenre, ticketing platform |

The ERD is unchanged: 8 tables, 36 attributes, 7 relationships. The only
additions at the physical level are the column types and lengths, the
case-sensitive collation on four ID columns, and `UNIQUE` on
`census_metro_name` and `market_label` (the candidate keys already in the
Oral Defense Study Points). The full column list with types is in the
generated data dictionary (section 8).

Facts worth knowing: 10,895 events in 24 metros; 41 genres (22 in Music, 19
in Sports); two segments (Music 8,689 events and Sports 2,206); events run
from 2026-11-12 to 2027-01-31; 245 events have no start time (NULL); El Paso
has no published count for NAICS 711320 (NULL).

## 4. The six decisions and why

All six are in `docs/project_decisions.md` under "2026-11-27: Phase 3 build
decisions" (approved by Nathan; **you still need to confirm them**). There is
also a dated correction note for Decision 6.

1. **Database name and character set.** `ticket_market_analytics`, `utf8mb4`.
   Lowercase snake_case behaves the same on every server; `utf8mb4` is needed
   because 268 event names contain non-ASCII characters.
2. **Case-sensitive collation on the four Ticketmaster ID columns**
   (`segment_id`, `genre_id`, `venue_id`, `event_id`) with `utf8mb4_bin`, on
   both sides of every foreign key. Some IDs differ only in letter case (3
   genre pairs, 9 venue pairs, 565 event IDs). With MySQL's default collation
   they count as equal: a primary key fails, and in a `LOAD DATA LOCAL` load
   285 events would have been skipped silently.
3. **Column types, lengths and NULL rules** follow the ERD exactly (bold
   attributes are `NOT NULL`, plain ones allow NULL); lowercase table names;
   `UNIQUE` on `census_metro_name` and `market_label`.
4. **Latitude and longitude** are `DECIMAL(18,15)`, nullable, so the stored
   values are identical to the file (`DECIMAL(10,7)` would round 194 values
   and show 194 warnings on every load).
5. **Staging tables.** Each CSV is loaded as-is into an all-text staging
   table, validated, copied into the final tables with `INSERT ... SELECT`,
   and the staging tables are dropped only after all final checks pass. The
   CSVs stay unchanged.
6. **Cleaning rules** applied while copying: trim whitespace at the ends of
   four venue text columns; turn blank cells into NULL in the 12 nullable
   columns (a blank time would otherwise be stored as `00:00:00`); validate
   that ACS values are whole numbers before casting `2620945.0` to an
   integer; load `local_time` with a `CASE` expression (see section 6).

## 5. How to reproduce the database on your machine

### Prerequisites

- **MySQL 8.0 or later**, running, and the `mysql` command in your terminal.
  Check: `mysql --version`.
- **A MySQL account** that can create a database and set global variables
  (the `root` account works). In the commands below it is written
  `<your_mysql_user>`. Passwords are never typed in a command: `-p` makes
  `mysql` ask.
- **This repository, up to date:** `git pull`.
- **The six `working_dedup_v5` CSV files** in the folder
  `../processed copy/working_dedup_v5/` (next to the repository; this is
  where your `v5` files already are). The files are only read.
- **Python 3** (standard library only), for the last step.
- The database must **not** exist yet. Check:

  ```bash
  mysql -u <your_mysql_user> -p -e "SHOW DATABASES LIKE 'ticket_market_analytics';"
  ```

  Expected: no rows. If it exists, stop and ask Nathan.

Open **one terminal** and keep using it, because the commands below use a
shell variable.

### Step 0: check that your CSV files are the right ones

From the repository root:

```bash
REPO="$(pwd)"
cd "../processed copy"
shasum -a 256 -c "$REPO/sql/v5_checksums.sha256"
```

Expected: six lines ending in `: OK`. **If any line says FAILED, stop and tell
Nathan** (your file differs from the one the build was checked with; do not
load it).

Then go back to the repository root:

```bash
cd "$REPO"
```

All steps below run **from the repository root** except Step 4b.

### Step 1: create the database

```bash
mysql -u <your_mysql_user> -p --table < sql/01_create_database.sql
```

Expected: one result row: `ticket_market_analytics | utf8mb4 | utf8mb4_0900_ai_ci`.
(The other two checks print nothing.) `ERROR 1007` means the database already
exists: stop.

### Step 2: create the 8 tables

```bash
mysql -u <your_mysql_user> -p --table < sql/02_create_tables.sql
```

Expected, five check results:
- A: `tables_expected_8` = 8 and `columns_expected_36` = 36;
- B: 7 foreign-key rows, every `same_collation` = `match`;
- C: 7 columns with `utf8mb4_bin` (`event.event_id`, `event.genre_id`,
  `event.venue_id`, `genre.genre_id`, `genre.segment_id`,
  `segment.segment_id`, `venue.venue_id`);
- D: 12 nullable columns;
- E: three keys on `metro_area`: `PRIMARY`, `uq_metro_area_census_metro_name`,
  `uq_metro_area_market_label`, all with `NON_UNIQUE` = 0.

### Step 3: create the 5 staging tables

```bash
mysql -u <your_mysql_user> -p --table < sql/03_create_staging_tables.sql
```

Expected: A) `stg_acs` 3, `stg_cbp` 5, `stg_event` 13, `stg_market_label` 3,
`stg_venue` 9 columns; B) 5 columns with `utf8mb4_bin`; C) nothing printed;
D) `tables_expected_13` = 13 and all five row counts 0.

### Step 4: load the CSVs into staging (three commands, in this order)

**4a. Allow local file loading** (changes a global MySQL setting; it is
switched off again in 4c). From the repository root:

```bash
mysql -u <your_mysql_user> -p --table < sql/04a_enable_local_infile.sql
```

Expected: `local_infile_before_expected_0` = 0, then
`local_infile_now_expected_1` = 1.

**4b. Load.** This is the one step that runs from a **different folder**: the
folder that *contains* `working_dedup_v5` (the CSV paths in the script are
relative, so nobody's personal path is in it):

```bash
cd "../processed copy"
mysql -u <your_mysql_user> -p --local-infile=1 --default-character-set=utf8mb4 --table < "$REPO/sql/04b_load_staging.sql"
cd "$REPO"
```

Expected:
- five tables headed `@@session.warning_count`, **all 0**;
- check A: 10895 / 965 / 24 / 24 / 72 rows;
- check B: distinct IDs 10895 / 965 / 41 / 2, then 965;
- check C: double quotes 62, commas 558, non-ASCII 268, pipes 68, longest
  name 347;
- check D: three sample events (the first is `1118v0PYZFFVv2`, "Summer
  Breeeze: an Afternoon of Yacht Rock") and three metros (Austin, Boston,
  Charlotte).

**4c. Switch local loading off again, immediately.** Run this **even if 4b
failed**:

```bash
mysql -u <your_mysql_user> -p --table < sql/04c_disable_local_infile.sql
```

Expected: `local_infile_before_expected_1` = 1, then
`local_infile_now_expected_0` = 0.

If 4b fails with `ERROR 3948` you skipped 4a; with `ERROR 2068` you left out
`--local-infile=1`; an error saying a file was not found means you ran it from
the wrong folder. Run 4c, then fix and repeat 4a to 4c.

### Step 5: validate the staging data (read-only)

```bash
mysql -u <your_mysql_user> -p --table < sql/05_validate_staging.sql
```

Expected: 57 checks, every row `PASS`, and the last row
`FAILED CHECKS (must be 0) | 0 | 0 | PASS`. **If anything says FAIL, do not
go on to Step 6; paste the output to Nathan.**

### Step 6: fill the 8 final tables

```bash
mysql -u <your_mysql_user> -p --table < sql/06_populate_tables.sql
```

Expected: eight tables headed `@@session.warning_count`, **all 0**, then a
row-count table with `PASS` for every table: 24, 2, 3, 965, 41, 24, 72,
10895. The script runs in one transaction, so a failure leaves the tables
empty; nothing is half-loaded.

### Step 7: final checks (read-only)

```bash
mysql -u <your_mysql_user> -p --table < sql/07_final_checks.sql
```

Expected: 77 checks, every row `PASS`, and `FAILED CHECKS (must be 0) | 0 | 0 | PASS`.

### Step 8: drop the staging tables

Only after Step 7 passed. Check the CSV files once more (they must still
match; run Step 0's `shasum` command again), then:

```bash
mysql -u <your_mysql_user> -p --table < sql/08_drop_staging_tables.sql
```

Expected: a list of 13 tables, then a list of exactly **8**: `event`,
`genre`, `industry`, `metro_area`, `metro_demographic`, `metro_industry`,
`segment`, `venue`; then 14 checks, all `PASS`, ending with FAILED CHECKS = 0.

### Step 9: extract the data dictionary and compare it with Nathan's

Write your extract **outside the repository** so you do not overwrite
Nathan's committed file:

```bash
python3 scripts/extract_data_dictionary.py --database ticket_market_analytics --user <your_mysql_user> --output /tmp/dictionary_nick.md
diff <(grep -v '^Generated ' docs/data_dictionary_reference_generated.md) <(grep -v '^Generated ' /tmp/dictionary_nick.md) && echo "no differences"
```

Expected: `no differences` (only the `Generated ...` line, which holds the time,
differs, and it is filtered out).

### If something goes wrong

- Stop at the first unexpected result and send Nathan the exact output.
- **Do not edit the scripts** and do not add `IF NOT EXISTS` to anything.
- To redo everything from the start (this deletes only this project's
  database; no other database is touched):

  ```bash
  mysql -u <your_mysql_user> -p -e "DROP DATABASE ticket_market_analytics;"
  ```

  Then run Step 1 again. To redo only Step 6, see "Redoing step 6 only" in
  `sql/README.md`.
- Run 04c if `local_infile` may still be on.

### Recording your results

Append entries to the **bottom** of `docs/database_build_log.md`, one per
step, with the heading `### <date>: Step N, <what> (Nick)` and: the exact
command, the result (paste real output), and any error with its exact
message. Never edit Nathan's entries. `git pull` before editing and push soon
after.

## 6. Validation checks, and the challenges (rehearsal vs the real database)

### The checks

| Step | Checks | What they prove |
|---|---|---|
| 2 | 5 | Tables, columns, keys, collations and NULL rules are as designed |
| 4b | 4 | Staging row counts, case-sensitive distinct IDs, special characters intact |
| 5 | 57 | Staging data is safe to copy: counts, dependencies, key uniqueness, no blanks in required columns, links, whitespace and blank counts, ACS whole numbers, formats, lengths |
| 6 | 8 + counts | Zero warnings on each insert; row counts |
| 7 | 77 | Final tables: structure, counts, no orphans, every value equals its staging value after cleaning, nothing lost by splitting the data, NULLs, spot values computed separately from the CSVs |
| 8 | 14 | Exactly 8 tables remain; counts; foreign keys; `local_infile` off |

### Real database vs rehearsal: what actually happened

**On Nathan's real database no step produced an error, and every load had 0
warnings.** Every check passed on the first run. (Results of Steps 3, 4 and 8
were reported by Nathan rather than pasted into the session; the build log
says which.) The problems below were found by **analyzing the data** or by
**rehearsing the scripts on throwaway MySQL servers** (temporary servers in a
scratch folder, deleted afterwards), and were prevented before they could
reach the real database. In the report, describe each one for what it is.

| Issue | Found by | What happened | How it is handled |
|---|---|---|---|
| IDs that differ only in letter case | Data analysis, tested on a throwaway server | With the default collation: `ERROR 1062 Duplicate entry 'KnvZfZ7vAdE'`; in a `LOAD DATA LOCAL` load of all events, 10,610 of 10,895 loaded with 285 warnings (rows skipped, no error) | `utf8mb4_bin` on the four ID columns (Decision 2) |
| Foreign key between columns with different collations | Throwaway server | `ERROR 3780 ... are incompatible` | Same collation on both sides |
| `DISTINCT` on IDs in a default-collation staging table | Throwaway server | 38 genre IDs instead of 41 | Staging ID columns use `utf8mb4_bin` |
| Local file loading disabled | Throwaway server | `ERROR 3948` without 4a; `ERROR 2068` without `--local-infile=1` | Steps 4a, 4b and 4c |
| Blank cells | Throwaway server | A blank time became `00:00:00` with no warning (245 events); a blank in an `INT` or `DECIMAL` column gave `ERROR 1366`; blank text became `''` instead of NULL | Blank to NULL for the 12 nullable columns (Decision 6) |
| **A wrong expression in Decision 6** | Rehearsal of Step 6 | `CAST(NULLIF(local_time, '') AS TIME)` turned `12:00:00` into `00:00:12` for all 10,650 non-blank times, and stopped the insert with `ERROR 1292 Truncated incorrect INTEGER value: '12:00:00'` | Fixed before the real run: `CASE WHEN local_time = '' THEN NULL ELSE CAST(local_time AS TIME) END`. Decision 6 carries a dated correction note. Step 7 compares every stored value with the source, so this kind of mistake cannot pass silently |
| Whitespace at the ends of venue text | Data analysis; counts confirmed in Step 5 on the real database | 12 names, 17 addresses, 2 cities, 3 ZIP codes. One name (`rZ7HnEZ17rfqV`) ends in a non-breaking space that `TRIM()` does not remove | `REGEXP_REPLACE` on the four venue columns; Step 7 shows 0 left |
| ZIP code with a leading space | Throwaway server | `' 32210'` loaded untrimmed into `CHAR(5)` became `' 3221'` with a warning and no error | Trim before the insert |
| Coordinate precision | Throwaway server | `DECIMAL(10,7)` rounded 102 latitudes and 92 longitudes (194 warnings) | `DECIMAL(18,15)` (Decision 4) |
| ACS numbers written as `2620945.0` | Data analysis; Step 5 on the real database | 24 of 24 values in both columns are whole numbers | Validated, then cast (Decision 6) |
| Quotes, commas and accents in event names | Staging load | 62, 558 and 268 names; arrived intact | Load options in Decision 6 |

Data issues decided **before** the database was built (Phase 2 and the
cleaning passes) are in `docs/project_decisions.md`: duplicate listings
removed, the 9 events with no genre excluded, and the limitation that one
physical venue can have several venue IDs (126 venue IDs share a name; a venue
ID is not a building).

## 7. Limits of what has been verified

- Your `working_dedup_v5` files were not compared with Nathan's byte for byte;
  Step 0 does that for you.
- The six decisions are recorded as approved by Nathan; you have not yet
  confirmed them.

## 8. Where everything is

| What | Where |
|---|---|
| This handoff | `docs/phase3_handoff.md` |
| The scripts to run (01 to 08), how to run them | `sql/`, with `sql/README.md` |
| Checksums of the six `v5` files | `sql/v5_checksums.sha256` |
| The six decisions, the correction, the approved ERD | `docs/project_decisions.md` |
| Every step with commands and results, and the rehearsal findings | `docs/database_build_log.md` |
| **Generated data dictionary** (tables, columns, types, keys) | `docs/data_dictionary_reference_generated.md` |
| Data dictionary reference (descriptions still to be written) | `docs/data_dictionary_reference.md` |
| Data extraction tool | `scripts/extract_data_dictionary.py` |
| Row-count checker (optional) | `scripts/check_import_counts.py` |
| Project rules, requirements, progress log | `CLAUDE.md` |
| Data limitations | `docs/data_sources.md` and `docs/project_decisions.md` |

## 9. What remains, and the deadline

**Phase 3 is due Monday, November 30, 2026 at 11:59 PM.** Requirements (from
`CLAUDE.md`): a populated MySQL database with at least 6 tables (done: 8) and a
3 to 4 page report covering how the dataset was converted into tables, the
actual import challenges and solutions, a complete data dictionary, and at
least 6 business questions of varying complexity.

Still to do:

1. **Reproduce the build** (section 5) and record your results.
2. **Confirm the six decisions** in `docs/project_decisions.md` (or say what
   you want changed, before the weekend is over).
3. **Column descriptions** for the 36 columns and 8 tables in the generated
   dictionary. They must be written or confirmed by Nathan or you; until then
   they stay "to be written".
4. **At least 6 business questions** of varying complexity. You and Nathan
   write them; record their final wording verbatim, with the date approved,
   in `docs/project_decisions.md`. The data can support these themes: event
   activity by metro, genre and segment composition, venue concentration,
   event variety, population and income, and industry establishments and
   employees.
5. **The 3 to 4 page report**, written by you and Nathan. Use the build log
   for the facts; describe the challenges in section 6 accurately (real
   database vs rehearsal).

Suggested pace: Saturday for steps 1 to 3, Sunday for step 4, Monday for the
report and submitting well before 11:59 PM. Phase 4 (SQL queries and charts)
is due December 9.

## 10. Prompt to paste into your own Claude session

```text
I'm Nick. My partner Nathan and I are finishing Phase 3 of our BAX-421
project (due Monday Nov 30, 2026, 11:59 PM). Nathan already built and checked
the MySQL database on his machine. My job now is to REPRODUCE it on my machine
exactly, using the scripts that already exist. Do not redesign anything.

First run git pull. Then read, in this order: docs/phase3_handoff.md, then
CLAUDE.md, then docs/database_build_log.md, then the "2026-11-27: Phase 3
build decisions" section of docs/project_decisions.md, then sql/README.md.

Rules for this session:
- Do not modify, rewrite or recreate any file in sql/ or scripts/, the ERD,
  the decisions or the data files. The six working_dedup_v5 CSVs are read-only.
- Walk me through section 5 of docs/phase3_handoff.md ONE STEP AT A TIME, from
  Step 0. For each step, give me the exact command for my machine (my CSVs are
  in "../processed copy/working_dedup_v5/" and my MySQL user is <FILL IN>).
  I will run the commands in my own terminal and paste the output; you cannot
  type my MySQL password.
- After each step, compare my output line by line with the expected output in
  the handoff and say clearly PASS or MISMATCH. If anything is a mismatch or
  an error, STOP and help me understand it; do not change a script to make it
  pass. If local_infile might still be on, remind me to run sql/04c.
- After each step, append an entry to the bottom of docs/database_build_log.md
  in the format "### <date>: Step N, <what> (Nick)" with the exact command,
  my pasted result and any error message. Never edit Nathan's entries.
- Ask me before you commit or push anything. Run git pull before editing and
  push soon after.
- Do not write our business questions, column descriptions or the report
  unless I ask. You may check facts and explain things.
- When all steps match, help me run the final dictionary comparison (Step 9),
  and tell me what remains for Phase 3.

Start by confirming you've read the handoff, then give me Step 0.
```

## 11. Where things stand (end of Friday 2026-11-27)

- Database built and verified on Nathan's machine; the repository has every
  script, decision, log entry and the generated dictionary.
- Nathan's MySQL has `local_infile` off; the six `v5` files are unchanged.
- Not yet done: your reproduction, your confirmation of the decisions, column
  descriptions, business questions, the report.
