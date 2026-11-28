# Database Build Log

Chronological record of building and loading the MySQL database (Phase 3).
Add one entry per step or problem, newest last. Record what actually
happened, including the exact error text, so the Phase 3 report's "import
challenges and solutions" section can be written from real events.

Entry format (from CLAUDE.md, "Entry conventions"):

- **Date and who:** e.g. 2026-11-23, Nathan
- **Source file(s):** full name with the run stamp and folder, e.g.
  `working_dedup_v3/working_events.csv` (run `2026-11-10_222442`)
- **Action:** what was done
- **Command or SQL:** the exact statement, in a code block
- **Result:** row counts before and after, and the exact error message if one
  occurred
- **Fix and who decided it:** if there was a problem

Row-count checks can be produced with `scripts/check_import_counts.py` and
compared with the counts in CLAUDE.md, "Working Dataset".

## Entries

### 2026-11-27: MySQL setup check (Nathan; read-only checks run by Claude)

- **Source files:** none loaded yet.
- **Action:** read-only check of the MySQL installation on Nathan's Mac. No
  database or table was created or changed, and no password was entered.
- **Commands:** `mysql --version`, `mysqld --version`,
  `mysqladmin --no-defaults ping`, `brew services list`,
  `mysql_config_editor print --all`, `mysql --help`.
- **Result:**
  - MySQL 9.5.0 (Homebrew, Apple silicon) is installed and the server is
    running as a Homebrew service. Data directory
    `/opt/homebrew/var/mysql` (216 MB); about 37 GB of disk free.
  - The `root` account requires a password. Pinging without one returned:
    `Access denied for user 'root'@'localhost' (using password: NO)`.
  - No saved login paths (`mysql_config_editor`) and no `~/.my.cnf`.
  - The `mysql` client reports `local-infile FALSE` (client-side default).
  - **Not yet checked** (needs a login): the server's `local_infile`
    setting, default character set and collation, and `sql_mode`.
- **Fix / decision:** none needed yet. Next step is for Nathan to run the
  server-side check and record the output here.

### 2026-11-27: MySQL server settings check (Nathan)

- **Source files:** none loaded yet.
- **Action:** Nathan ran a read-only check of the server settings in the
  `mysql` client as `root` and pasted the output. No database or table was
  created or changed.
- **Command:**

  ```sql
  SHOW GLOBAL VARIABLES
  WHERE Variable_name IN ('local_infile', 'character_set_server',
                          'collation_server', 'sql_mode', 'secure_file_priv');
  SHOW DATABASES;
  ```

- **Result:**

  | Variable | Value |
  |---|---|
  | `character_set_server` | `utf8mb4` |
  | `collation_server` | `utf8mb4_0900_ai_ci` |
  | `local_infile` | `OFF` |
  | `secure_file_priv` | `NULL` |
  | `sql_mode` | `ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION` |

  `SHOW DATABASES` listed 6 databases from other work plus the system
  schemas. None is for this project.
- **What this means for the build:**
  - `local_infile = OFF`: `LOAD DATA LOCAL INFILE` is disabled until it is
    turned on at the server and the client connects with `--local-infile=1`.
  - `secure_file_priv = NULL`: server-side `LOAD DATA INFILE` (without
    `LOCAL`) is disabled entirely, so loads must use `LOCAL`.
  - `utf8mb4_0900_ai_ci` is **case- and accent-insensitive**. Ticketmaster
    IDs that differ only in letter case (6 genre IDs, 18 venue IDs and 565
    event IDs in `working_dedup_v5`) would compare as equal, so ID columns
    need a case-sensitive collation.
  - `STRICT_TRANS_TABLES` is on, so values that don't fit a column raise an
    error instead of being silently truncated.
- **Fix / decision:** none yet. Open decisions: database name, ID collation,
  column types, how to load SEGMENT/GENRE/INDUSTRY.

### 2026-11-27: Collation test on a throwaway server (run by Claude for Nathan; not the project database)

- **Purpose:** find out how the server default collation handles Ticketmaster
  IDs that differ only in letter case, before choosing the collation
  (Decision 2 in `docs/project_decisions.md`).
- **What was used:** a temporary MySQL 9.5.0 server started in a scratch
  folder on port 3399 with `--local-infile=1` (for the test only), then
  stopped and deleted. Nathan's server, databases and settings were not
  touched. Source file: `working_dedup_v5/working_events.csv` (10,895 rows).
- **Note:** this was a test, **not** an import challenge on the project
  database. If a collation error or skipped rows happen on the real load,
  log them as separate entries.
- **Results:**

  | Test | Result |
  |---|---|
  | Primary key with the default collation, inserting genre IDs `KnvZfZ7vAde` and `KnvZfZ7vAdE` | `ERROR 1062 (23000): Duplicate entry 'KnvZfZ7vAdE' for key 'g_default.PRIMARY'` |
  | Same table with `COLLATE utf8mb4_bin` on the ID | Both rows stored; `WHERE genre_id = 'knvzfz7vade'` returned 0 rows |
  | Foreign key between columns with different collations | `ERROR 3780 (HY000): Referencing column 'genre_id' and referenced column 'genre_id' in foreign key constraint 'ev_mismatch_ibfk_1' are incompatible.` |
  | Foreign key with matching `utf8mb4_bin` on both sides | Created without error |
  | `LOAD DATA LOCAL INFILE` of all 10,895 events into a primary key with the default collation | **10,610 rows loaded, 285 warnings.** No error was raised: with `LOCAL`, duplicate-key errors become warnings and the rows are skipped |
  | Same load with `utf8mb4_bin` on `event_id` | 10,895 rows loaded, 0 warnings |
  | `COUNT(DISTINCT event_name)` | 7,030 under `utf8mb4_bin`; 6,984 under the default collation |

- **Why it matters:** under the default collation a `LOCAL` load drops the
  colliding rows silently (285 here, from 565 event IDs in 280 groups). After
  every load, check `SHOW WARNINGS` and compare row counts with the source.
- **Decision:** `utf8mb4_bin` on the four Ticketmaster ID columns, approved
  by Nathan (Decision 2).

### 2026-11-27: Data dictionary extractor now reports collation (Nathan approved; change made by Claude)

- **Action:** `scripts/extract_data_dictionary.py` now selects
  `COLLATION_NAME` from `information_schema.COLUMNS` and shows it as a
  `Collation` column in the generated tables (blank for non-text columns).
  No other behavior changed; `scripts/check_import_counts.py` is unaffected.
- **Test:** run against a throwaway MySQL 9.5.0 server (see the next entry),
  with a small `genre`/`event` schema. The `utf8mb4_bin` ID columns and the
  foreign-key pair showed `utf8mb4_bin`, text columns showed
  `utf8mb4_0900_ai_ci`, and `DATE`/`INT` columns showed blank. It has not
  been run against the project database, which does not exist yet.

### 2026-11-27: Latitude/longitude and ZIP load tests on a throwaway server (run by Claude; not the project database)

- **Purpose:** check how `LOAD DATA LOCAL` handles coordinates and ZIP codes
  before choosing types (Decisions 3 and 4 in `docs/project_decisions.md`).
- **What was used:** a temporary MySQL 9.5.0 server in a scratch folder on
  port 3399, with the default strict `sql_mode`, then stopped and deleted.
  Nathan's server and databases were not touched. Source file:
  `working_dedup_v5/working_venues.csv` (965 rows).
- **Note:** these are tests, **not** import challenges on the project
  database. Log any real occurrence separately.
- **Results:**

  | Test | Result |
  |---|---|
  | Latitude/longitude into `DECIMAL(10,7)` | 965 rows loaded; 194 rounding warnings (102 latitudes and 92 longitudes have more than 7 decimals); largest change 0.00000005 degrees (about 0.56 cm) |
  | Same columns into `DECIMAL(18,15)` | 965 rows, 0 warnings, values identical to the file |
  | Same columns into `DOUBLE` | 965 rows, 0 warnings |
  | Distinct latitude/longitude pairs | 808 in both `DECIMAL(10,7)` and `DECIMAL(18,15)` |
  | ZIP `' 32210'` (stray leading space) loaded untrimmed into `CHAR(5)` | stored as `' 3221'` with 1 warning; no error was raised |

- **Why it matters:** with `LOCAL`, a value that does not fit is truncated
  with a warning instead of failing, so a wrong value can be stored without
  an error. ZIP codes must be trimmed in the `LOAD DATA` statement, and the
  warnings checked after every load.

### 2026-11-27: Staging-table test for the derived tables on a throwaway server (run by Claude; not the project database)

- **Purpose:** compare ways to fill `segment`, `genre` and `industry`, which
  have no source file of their own (Decision 5 in
  `docs/project_decisions.md`).
- **What was used:** a temporary MySQL 9.5.0 server in a scratch folder on
  port 3399, then stopped and deleted. Nathan's server and databases were not
  touched. Source files: `working_dedup_v5/working_events.csv` (10,895 rows)
  and `working_cbp2023_metros.csv` (72 rows).
- **Note:** these are tests, **not** import challenges on the project
  database. Log any real occurrence separately.
- **Results:**

  | Test | Result |
  |---|---|
  | Load both files into staging tables (ID columns `utf8mb4_bin`) | 10,895 and 72 rows, 0 warnings |
  | Dependency checks in SQL: `genre_id` determines `segment_id` and `genre`; `segment_id` determines `segment`; `naics_code` determines `naics_label` | 0 violations each |
  | `INSERT ... SELECT DISTINCT` into `segment`, `genre` and `industry` | 2, 41 and 3 rows, 0 warnings |
  | Same staging with the **default** collation on `genre_id` | `COUNT(DISTINCT genre_id)` = 38 instead of 41 (3 pairs of IDs merge) |
  | Loading `working_events.csv` straight into `genre` with `LOAD DATA LOCAL` (duplicates skipped) | 41 rows, but **10,854 warnings** |

- **Why it matters:** staging tables must use the same collation on the ID
  columns, or `DISTINCT`/`GROUP BY` on those IDs merges different genres.
  The direct load reaches the right count but drowns any real warning in
  10,854 routine ones.

### 2026-11-27: Cleaning-rule tests on staging tables on a throwaway server (run by Claude; not the project database)

- **Purpose:** test how stray spaces, blank cells, numbers written as
  `2620945.0` and special characters behave when copied from staging tables,
  before fixing the cleaning rules (Decision 6 in
  `docs/project_decisions.md`).
- **What was used:** a temporary MySQL 9.5.0 server in a scratch folder on
  port 3399, then stopped and deleted. Nathan's server and databases were not
  touched. Source files: the five CSVs in `working_dedup_v5` loaded into
  `VARCHAR` staging tables (`stg_event`, `stg_venue`, `stg_market_label`,
  `stg_acs`, `stg_cbp`).
- **Note:** these are tests, **not** import challenges on the project
  database. Log any real occurrence separately.
- **Results:**

  | Test | Result |
  |---|---|
  | Load the five files into staging | 10,895 / 965 / 24 / 24 / 72 rows, 0 warnings each |
  | Special characters in `event_name` after staging | 62 with double quotes, 558 with commas, 268 with non-ASCII characters, 68 with ` \| `; longest name 347 characters; all intact |
  | Leading or trailing spaces in staging (MySQL `TRIM`) | `venue_name` 11, `venue_address` 17, `venue_city` 2, `venue_postal_code` 3; none in any other column |
  | The same count in Python | `venue_name` 12: venue `rZ7HnEZ17rfqV` ends in a non-breaking space (bytes `C2A0`), which `TRIM` does not remove |
  | `TRIM` + replacing the non-breaking space, or `REGEXP_REPLACE(col, '^[[:space:]]+\|[[:space:]]+$', '')` | 12 / 17 / 2 / 3 values changed (names / addresses / cities / ZIPs) |
  | `'2620945.0'` text into `INT` (directly, or via `CAST(... AS DECIMAL(12,0))`) | 24 rows, 0 warnings both ways; population 880,884 to 20,112,448, sum 120,585,924 |
  | Blank cell into `INT` without `NULLIF` | `ERROR 1366 (HY000): Incorrect integer value: '' for column 'est' at row 24` |
  | Blank cell into `DECIMAL(18,15)` without `NULLIF` | `ERROR 1366 (HY000): Incorrect decimal value: '' for column 'v' at row 1` |
  | Blank `local_time` into `TIME` without `NULLIF` | **no error and 0 warnings**; 245 rows stored as `00:00:00`, 0 NULLs |
  | Same with `NULLIF(local_time, '')` | 245 NULLs, 0 warnings |
  | Blank `subgenre` into `VARCHAR` without `NULLIF` | 8,693 empty strings and 0 NULLs, so `COUNT(subgenre)` returned 10,895 |
  | Same with `NULLIF(subgenre, '')` | 8,693 NULLs; `COUNT(subgenre)` returned 2,202 |
  | `local_date` text into `DATE` | 10,895 rows, 0 warnings, 2026-11-12 to 2027-01-31 |

- **Why it matters:** a blank time becomes a made-up `00:00:00` with no
  warning, and blank text becomes an empty string instead of NULL. Every
  nullable column needs `NULLIF(col, '')` when it is copied out of staging.
- **Also observed (Python, not a MySQL test):** 16 event names contain a
  non-breaking space or similar inside the name (not at the ends). They are
  not touched by edge trimming.

### 2026-11-27: Checksums of the six `working_dedup_v5` files before building (Nathan; run by Claude)

- **Source files:** `data/processed/working_2026-11-10_222442/working_dedup_v5/`
- **Action:** record a SHA-256 checksum of each CSV before any database work,
  so it can be shown afterwards that the files were not changed. The files
  are only read by `LOAD DATA`.
- **Command:** `cd data/processed/working_2026-11-10_222442/working_dedup_v5 && shasum -a 256 *.csv`
- **Result:**

  | File | SHA-256 |
  |---|---|
  | `market_labels.csv` | `001a3da0962f983d2eaa503e72f449379b0d93f034c84e3e02131b297a5859d1` |
  | `working_acs1_2025_metros.csv` | `9a48d11937086c71fd5f55fcec73cfd5c20ffdabd8277f935cfa9f98d6c3f766` |
  | `working_cbp2023_metros.csv` | `406d7314c24ea60077037306be7895a2906697938c0e3dd2aa92e95cedd9d21a` |
  | `working_events.csv` | `6a8346d6137be3401dfa1718b04e7a280baf24f8975df5975bca6b58cdd94d02` |
  | `working_excluded_events.csv` | `33b8b1e1a7a89250987930e65d4d5c1188d82f8f0e33008c67b43d4bd94fedf7` |
  | `working_venues.csv` | `f07211ad1b2cdf9b5caf926986192987eebcda0d7d35fc5f81283f9fe2801940` |

- **Next:** run the same command after the load and before the staging tables
  are dropped; the values must match.
