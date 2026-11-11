# CLAUDE.md

Permanent project reference for the BAX-421 final project (Nathan and Nick).
It describes where the data came from, how it was processed, and how the
team documents the MySQL database work for Phase 3. Read it before
answering project-specific questions.

## Project Data and Documentation Reference

This repository must maintain accurate documentation of the datasets,
processing steps, and technical implementation so Nathan and Nick can
reference their own work when preparing the final project deliverables.

### Source of Truth

Before answering project-specific questions, consult the relevant files:

- `docs/data_sources.md`: original data sources, API collection
  methodology, geographic matching, cleaning rules, exclusions, missing
  values, and limitations.
- `data/processed/`: cleaned CSV datasets used for database development.
- `data/raw/`: original collected data, retained for reproducibility.
- `scripts/`: collection, conversion, geocoding, and evaluation scripts.
- `requirements.txt`: Python dependencies.
- `README.md`: project overview and setup instructions.
- `CLAUDE.md`: project instructions and documentation conventions.

Do not assume that documentation is current. Verify facts against the
relevant files whenever possible.

## Course Requirements and AI Policy

Confirmed BAX-421 requirements as provided by Nathan on 2026-11-11. Team:
Nathan and Nick. **Both partners must participate in every phase.**

### Course requirements

| Phase | Due | Points | Requirements |
|---|---|---|---|
| Phase 2: ER diagram | November 19, 2026 | 25 | Must include all entities, attributes, primary keys, foreign keys, relationships, cardinalities, and proper normalization. |
| Phase 3: Database creation and business questions | November 30, 2026 | 25 | Build and populate the MySQL database with at least 6 tables. Submit a 3–4 page report explaining how the dataset was converted into tables, actual import challenges and solutions, a complete data dictionary, and at least 6 business questions of varying complexity. |
| Phase 4: SQL queries and visualizations | December 9, 2026 | 35 | Submit a `.sql` file and a visualization PDF. Queries should demonstrate joins, grouping, subqueries, and window functions. |
| Phase 5: Video presentation | December 9, 2026 | 15 | Maximum 15 minutes, one business question per slide, business-focused insights, and no SQL on slides. |

Dataset approval (stated by Nathan earlier in the project): datasets that
already have a published ERD, normalized tables or written SQL queries are
rejected. The TA approved the Ticketmaster + Census dataset, which the team
collected and combined itself.

### AI policy

- **AI can assist with:** dataset discovery, general SQL syntax, and
  understanding errors.
- **AI cannot:** use the team's uploaded data, files, or schema to design the
  ERD, table definitions, business questions, or SQL queries, or write the
  report or video script.
- **Nathan and Nick must** do the actual modeling, analysis, and writing
  themselves and be able to explain everything.

### Team working rules for AI assistance

Nathan has set these rules for this project, in line with the AI policy:

- **Database design is the team's work.** Do not design or propose the
  ERD, database tables, relationships, primary or foreign keys, normalized
  structures, SQL queries, or business questions. Nathan and Nick do these
  themselves.
- **Allowed:** help with data collection, cleaning scripts, verification,
  general SQL syntax, understanding errors, and retrieving factual metadata
  from a database they have built.
- **Reports and video:** do not write the submitted Phase 3 report, the
  video script, or other graded text.
- **Ask before:**
  - committing or pushing anything;
  - creating or modifying documentation files;
  - changing the dataset.

## Repository Map (verified 2026-11-11)

```
README.md                Project overview, setup, how to run the pipeline
CLAUDE.md                This file
requirements.txt         requests, pandas, python-dotenv (pinned versions)
.env.example             Template for TICKETMASTER_API_KEY, CENSUS_API_KEY, LASTFM_API_KEY
scripts/
  config.py              25 cities, search points, 25-mile radius, event window
  api_client.py          Shared rate-limited client; keeps API keys out of logs
  collect_ticketmaster.py   Discovery API -> data/raw/ticketmaster/<run>/
  convert_to_csv.py      Raw JSON -> ticketmaster_events / ticketmaster_excluded CSVs
  geocode_venues.py      Census Geocoder -> venues_geocoded CSV
  collect_census.py      ACS 1-year 2025, ACS 5-year 2020-2024, CBP 2023, search-area tracts
  evaluate_collection.py Read-only data-quality report
  probes/                Exploratory scripts (resale, Last.fm, Census pilot); not part of the pipeline
docs/
  data_sources.md        Main data documentation: sources, missing values, limitations, file inventory
  phase1_guide.md        LA/NYC pilot notes; full column reference for the events CSV
  ticketmaster_pricing_investigation.md, resale_source_options.md,
  lastfm_pivot_feasibility.md, census_option_assessment.md
                         Earlier research notes (historical)
data/                    Local only, git-ignored
logs/                    Local only, git-ignored
```

`data/`, `logs/` and `.env` are git-ignored and are **not on GitHub**. They
exist only on the machine that ran the pipeline (Nathan's). Never commit
them, and never print or commit API keys.

## Working Dataset

The approved working dataset for the database is collection run
**`2026-11-10_222442`**. Every working file name ends with this run stamp.
Verified counts (header row excluded):

| File in `data/processed/` | Rows | Columns | One row per |
|---|---|---|---|
| `ticketmaster_events_2026-11-10_222442.csv` | 11,443 | 91 | Ticketmaster event ID |
| `ticketmaster_excluded_2026-11-10_222442.csv` | 645 | 92 | Excluded non-event listing (`exclusion_reason`) |
| `venues_geocoded_2026-11-10_222442.csv` | 1,019 | 35 | Ticketmaster venue ID |
| `census_acs1_2025_2026-11-10_222442.csv` | 2,071 | 12 | Geography (`geo_level` + `geoid`) |
| `census_acs5_2024_2026-11-10_222442.csv` | 129,646 | 12 | Geography (`geo_level` + `geoid`) |
| `census_cbp2023_2026-11-10_222442.csv` | 7,302 | 12 | Geography + `naics_code` |
| `search_area_tracts_2026-11-10_222442.csv` | 22,088 | 9 | Search area + tract |

Other files in `data/processed/` and `data/raw/` are **not** part of the
working dataset:
- the LA/NYC pilot (`2026-11-02_203943`);
- the Census probe (`census_probe_2026-11-05_220517.csv`, `geocoder_2026-11-05_*.json`);
- the Ticketmaster Resale probe (`data/raw/ticketmaster_tmr/`);
- an empty `data/raw/seatgeek/`.

Raw sources for the working run:
- `data/raw/ticketmaster/2026-11-10_222442/`: 25 city files and
  `manifest.json`.
- `data/raw/census/2026-11-10_222442/`: `geocoder_venues.jsonl`,
  `acs1_2025.json`, `acs5_2024.json`, `cbp_2023.json`.
- Census reference files in `data/raw/census/`: Gazetteer, CBP bulk files,
  and the pilot's ACS table files.

Logs for the run are in `logs/`, named `*_2026-11-10_222442.log`.

Facts to keep in mind when working with these files (details in
`docs/data_sources.md`):
- **Prices:** they are Ticketmaster *listed* price ranges, not verified face
  value. Only about 23% of events have one. Missing prices are blank.
- **Search areas:** a search area (`search_cities`) is a 25-mile circle,
  not city limits. Use the geocoded identifiers in `venues_geocoded` for
  real geography.
- **Census IDs** have leading zeros and must be read as text.
  - In the ACS files the same `geoid` can appear at different `geo_level`s.
  - Unpublished CBP cells (`published = False`) mean 0–2 establishments,
    not zero.
- **Multi-value cells:** some event columns hold several values joined with
  ` | ` (performers, genres, promoters, presales, add-ons, DMAs, search
  cities). The performer columns line up by position.
- **Review flags:** 17 events carry `review_attraction_admission`. They are
  kept, pending the team's decision.

## How the Data Was Produced

Pipeline commands, in order, from the repository root (each script's
docstring documents its own usage):

```bash
.venv/bin/python scripts/collect_ticketmaster.py
.venv/bin/python scripts/convert_to_csv.py
.venv/bin/python scripts/geocode_venues.py
.venv/bin/python scripts/collect_census.py
.venv/bin/python scripts/evaluate_collection.py
```

Processing history of the working run:
- **2026-11-10:** collection.
  - 606 Ticketmaster requests (0 failed).
  - 1,020 venues geocoded.
  - 45 Census API requests (0 failed).
- **2026-11-11:** the non-event filter in `scripts/convert_to_csv.py` was
  tightened.
  - 500 more listings excluded: skating sessions, museum tours, stadium and
    arena tours.
  - `convert_to_csv.py` and `geocode_venues.py` were re-run from the saved
    raw data, with no new API requests. Raw data unchanged (checksums
    verified).
  - The venue file went from 1,020 to 1,019 rows.

To regenerate the CSVs from the saved raw data, rerun `convert_to_csv.py`
and `geocode_venues.py`. Do not rerun `collect_ticketmaster.py` to "refresh"
the working dataset: Ticketmaster only returns upcoming events, so a new run
would be a different snapshot.

## Phase 3 Documentation Requirements

The Phase 3 report must address four areas.

### 1. Dataset-to-table conversion

Maintain a factual record of:

- Which original CSV files were used.
- Which columns were retained, transformed, or excluded.
- How many records were imported.
- Which scripts or manual steps performed transformations.
- Any differences between the original and imported datasets.

Nathan and Nick are responsible for deciding the relational database
structure. Do not design tables or relationships on their behalf.

### 2. Import challenges and solutions

Maintain a technical record of:

- Import errors and their actual error messages.
- Data type conversion issues.
- Missing values and placeholder values.
- Duplicate or inconsistent identifiers.
- Character encoding problems.
- Foreign key or constraint errors.
- How Nathan and Nick resolved each issue.

Only document issues that actually occurred. Do not invent challenges or
solutions.

### 3. Data dictionary

Once Nathan and Nick have independently created their MySQL database, help
them retrieve and document factual metadata from the existing database,
including:

- Table names.
- Column names.
- Actual MySQL data types.
- Nullability.
- Primary and foreign key constraints.
- Column descriptions supplied or verified by Nathan and Nick.

Do not invent descriptions, infer unverified business definitions, or
design missing columns.

### 4. Business questions

Maintain a reference to the business questions written and approved by
Nathan and Nick.

Do not generate, rewrite, or select their questions. Record their final
wording exactly as supplied.

## Documentation Rules

- Keep factual technical notes separate from graded report writing.
- Cite file paths, scripts, logs, and database metadata when explaining
  technical decisions.
- Record actual observations rather than assumptions.
- Preserve original data and processing history.
- Do not fabricate missing values, transformations, errors, or results.
- Ask for clarification when a decision or implementation step is
  undocumented.
- Do not write the submitted Phase 3 report; Nathan and Nick must write it
  themselves.

## Recommended Documentation Organization

Use these locations if Nathan and Nick choose to create them. None of them
exists yet (as of 2026-11-11).

- `docs/data_sources.md`: data collection and cleaning (exists).
- `docs/database_build_log.md`: chronological record of database
  implementation and import issues.
- `docs/data_dictionary_reference.md`: factual metadata extracted from the
  completed database.
- `docs/project_decisions.md`: decisions recorded by Nathan and Nick,
  including the business questions they authored.

These documentation files are reference materials, not automatically
generated submission content.

Do not create or modify documentation files without explicit permission.

### Entry conventions (once those files exist)

These describe how to *record* information, not what the database should be.

- **Build log entries** (`docs/database_build_log.md`), one per event, newest
  last:
  - date and who did the step;
  - the source file(s), using the full name with the run stamp;
  - the action taken;
  - the exact command or SQL, if any;
  - the result: row counts before and after, and the exact error message
    if one occurred;
  - the fix, and who decided it.
- **Data dictionary entries** (`docs/data_dictionary_reference.md`):
  - generate from the live database, e.g. `information_schema`, with the
    query used and the date run;
  - descriptions only as written or confirmed by Nathan or Nick; otherwise
    leave them blank and marked "to be written".
- **Decision entries** (`docs/project_decisions.md`):
  - date, decision, who made it, and the reason as they stated it;
  - business questions verbatim, with the date approved.
- **Record row counts against the source.** For any imported data, compare
  with the counts in the "Working Dataset" table and explain differences.
