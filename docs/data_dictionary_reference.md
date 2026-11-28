# Data Dictionary Reference

Factual metadata extracted from the live MySQL database, for the Phase 3
data dictionary. This is reference material, not submission text.

Rules (from CLAUDE.md, "Entry conventions"):

- Table names, column names, MySQL types, nullability and key constraints
  come from the live database (`information_schema`), with the query used
  and the date it was run.
- Descriptions are only as written or confirmed by Nathan or Nick. Until
  then, they stay blank and are marked "to be written".

To generate the metadata, run from the repository root (it prompts for the
MySQL password and only reads `information_schema`):

```bash
.venv/bin/python scripts/extract_data_dictionary.py --database <your_database_name> --output docs/data_dictionary_reference_generated.md
```

Review the generated file, then copy the tables into this document and add
descriptions.

## Extraction

- **Database:** `ticket_market_analytics` (MySQL 9.5.0), built in Phase 3 with
  the scripts in `sql/`; see `docs/database_build_log.md`.
- **Run:** 2026-11-27 21:09, after the staging tables were dropped, with
  `scripts/extract_data_dictionary.py`. The query used is printed in the
  generated file.
- **Generated file:** [`data_dictionary_reference_generated.md`](data_dictionary_reference_generated.md)
  lists, for each of the 8 tables, every column with its MySQL type, collation,
  nullability, primary-key and foreign-key information, default and extra.
- **Verified:** the generated metadata matches the approved column
  specification (Decisions 2 to 4 in `docs/project_decisions.md`) column by
  column: 8 tables, 36 columns, 9 primary-key columns, 7 foreign-key columns, 12
  nullable columns, 7 `utf8mb4_bin` columns, no differences.

## Tables

The table and column metadata is in the generated file above. The description
of each table and column is still **to be written** by Nathan and Nick; once
written or confirmed it is added here.
