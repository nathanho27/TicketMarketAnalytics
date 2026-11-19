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

_Not run yet: the database has not been built._

## Tables

_None yet._
