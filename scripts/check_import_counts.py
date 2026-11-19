"""Compare row counts in MySQL tables with the CSV files they were loaded from.

Read-only: runs SELECT COUNT(*) on each named table and counts the data rows
in each CSV (header excluded, quoted fields handled). Prints a Markdown table
for docs/database_build_log.md and exits with code 1 if any count differs.

The table-to-file pairs are given on the command line, so the script makes
no assumption about how the CSVs map to tables. A table loaded from part of
a file, or from several files, will legitimately differ; explain those
differences in the build log.

Uses the `mysql` command-line client; prompts for the password unless
--login-path is given (see extract_data_dictionary.py).

Run from the project root:
    .venv/bin/python scripts/check_import_counts.py --database DB_NAME \
        --pair TABLE_A=path/to/file_a.csv --pair TABLE_B=path/to/file_b.csv
    .venv/bin/python scripts/check_import_counts.py --database DB_NAME --all-tables
--all-tables also lists every base table's row count, paired or not. It
needs a second query, so the password is asked for twice.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from extract_data_dictionary import add_connection_args, check_identifier, run_query


def csv_rows(path):
    """Data rows in a CSV, excluding the header; quoted line breaks are counted correctly."""
    with open(path, newline="", encoding="utf-8") as f:
        return max(sum(1 for _ in csv.reader(f)) - 1, 0)


def parse_pairs(pairs):
    parsed = []
    for p in pairs:
        if "=" not in p:
            sys.exit(f"--pair must look like TABLE=path/to/file.csv, got {p!r}")
        table, path = p.split("=", 1)
        path = Path(path).expanduser()
        if not path.is_file():
            sys.exit(f"CSV not found: {path}")
        parsed.append((check_identifier(table, "table"), path))
    return parsed


def build_sql(database, tables, all_tables):
    parts = [f"SELECT '{t}' AS table_name, COUNT(*) AS n FROM `{database}`.`{t}`" for t in tables]
    if all_tables:
        parts.append(
            "SELECT CONCAT('*', TABLE_NAME), 0 FROM information_schema.TABLES "
            f"WHERE TABLE_SCHEMA = '{database}' AND TABLE_TYPE = 'BASE TABLE'")
    return "\nUNION ALL\n".join(parts) + ";"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_connection_args(parser)
    parser.add_argument("--pair", action="append", default=[], metavar="TABLE=CSV",
                        help="A table and the CSV it was loaded from (repeatable)")
    parser.add_argument("--all-tables", action="store_true", help="Also list every table's row count")
    args = parser.parse_args()
    database = check_identifier(args.database, "database")
    pairs = parse_pairs(args.pair)
    if not pairs and not args.all_tables:
        sys.exit("Give at least one --pair TABLE=CSV, or --all-tables.")

    sql = build_sql(database, [t for t, _ in pairs], args.all_tables)
    if args.dry_run:
        print(sql)
        return
    rows = run_query(args, sql)
    counts = {r["table_name"]: int(r["n"]) for r in rows if not r["table_name"].startswith("*")}
    others = sorted(r["table_name"][1:] for r in rows if r["table_name"].startswith("*"))
    if others:  # count unpaired tables too (a second query, so only tables that exist are counted)
        missing = [t for t in others if t not in counts]
        if missing:
            more = run_query(args, build_sql(database, [check_identifier(t, "table") for t in missing], False))
            counts.update({r["table_name"]: int(r["n"]) for r in more})

    print(f"Row-count check, database `{database}`, {datetime.now():%Y-%m-%d %H:%M}\n")
    mismatches = 0
    if pairs:
        print("| Table | MySQL rows | CSV | CSV rows | Difference | Status |")
        print("|---|---|---|---|---|---|")
        for table, path in pairs:
            n_db, n_csv = counts[table], csv_rows(path)
            diff = n_db - n_csv
            mismatches += diff != 0
            print(f"| `{table}` | {n_db:,} | `{path.name}` | {n_csv:,} | {diff:+,} | {'match' if diff == 0 else 'DIFFERENT'} |")
        print()
    if others:
        print("| Table | MySQL rows |")
        print("|---|---|")
        for t in others:
            print(f"| `{t}` | {counts[t]:,} |")
        print()
    print(f"Mismatches: {mismatches}")
    if mismatches:
        sys.exit(1)


if __name__ == "__main__":
    main()
