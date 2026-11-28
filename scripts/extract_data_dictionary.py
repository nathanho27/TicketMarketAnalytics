"""Extract factual column metadata from the team's live MySQL database.

Read-only: runs one SELECT against information_schema and writes a Markdown
reference with, for every base table in the database:
  - column name, MySQL column type, collation (text columns only),
    nullability, default, extra (e.g. auto_increment);
  - primary-key membership and foreign-key references.

Descriptions are left as "to be written": per CLAUDE.md, only Nathan or Nick
write or confirm them. The output records the query used and the date run.

Uses the `mysql` command-line client (installed with MySQL), so no extra
Python package is needed. By default it prompts for the password
(`mysql -p`). Use --login-path to read saved credentials from
`mysql_config_editor` instead.

Run from the project root:
    .venv/bin/python scripts/extract_data_dictionary.py --database DB_NAME
    .venv/bin/python scripts/extract_data_dictionary.py --database DB_NAME \
        --output docs/data_dictionary_reference_generated.md
Options: --user (default root), --host, --port, --login-path, --dry-run
(print the SQL and stop).
"""
import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

IDENTIFIER = re.compile(r"^[A-Za-z0-9_$]+$")

QUERY = """SELECT
  c.TABLE_NAME       AS table_name,
  c.ORDINAL_POSITION AS position,
  c.COLUMN_NAME      AS column_name,
  c.COLUMN_TYPE      AS column_type,
  c.COLLATION_NAME   AS collation_name,
  c.IS_NULLABLE      AS is_nullable,
  c.COLUMN_DEFAULT   AS column_default,
  c.EXTRA            AS extra,
  (SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE p
    WHERE p.TABLE_SCHEMA = c.TABLE_SCHEMA AND p.TABLE_NAME = c.TABLE_NAME
      AND p.COLUMN_NAME = c.COLUMN_NAME AND p.CONSTRAINT_NAME = 'PRIMARY') AS is_pk,
  (SELECT GROUP_CONCAT(CONCAT(k.REFERENCED_TABLE_NAME, '.', k.REFERENCED_COLUMN_NAME)
                       ORDER BY k.REFERENCED_TABLE_NAME SEPARATOR ', ')
     FROM information_schema.KEY_COLUMN_USAGE k
    WHERE k.TABLE_SCHEMA = c.TABLE_SCHEMA AND k.TABLE_NAME = c.TABLE_NAME
      AND k.COLUMN_NAME = c.COLUMN_NAME AND k.REFERENCED_TABLE_NAME IS NOT NULL) AS references_to
FROM information_schema.COLUMNS c
JOIN information_schema.TABLES t
  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
 AND t.TABLE_TYPE = 'BASE TABLE'
WHERE c.TABLE_SCHEMA = '{database}'
ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION;"""


def check_identifier(name, what):
    """Allow only plain MySQL identifiers, so names can be placed in SQL safely."""
    if not IDENTIFIER.match(name):
        sys.exit(f"Invalid {what} name {name!r}: use letters, digits, _ or $ only.")
    return name


def add_connection_args(parser):
    parser.add_argument("--database", required=True, help="Database (schema) name")
    parser.add_argument("--user", default="root", help="MySQL user (default root)")
    parser.add_argument("--host", help="MySQL host (default: local socket)")
    parser.add_argument("--port", type=int, help="MySQL port")
    parser.add_argument("--socket", help="MySQL socket file")
    parser.add_argument("--login-path", help="Saved mysql_config_editor login path; skips the password prompt")
    parser.add_argument("--dry-run", action="store_true", help="Print the SQL and stop")


def run_query(args, sql):
    """Run one SQL statement with the mysql client in batch mode.

    Returns a list of dicts, one per row. MySQL NULL comes back as None.
    """
    cmd = ["mysql"]
    if args.login_path:
        cmd.append(f"--login-path={args.login_path}")  # must be the first option
    cmd += ["--batch", "--raw", "--default-character-set=utf8mb4", f"--user={args.user}"]
    if args.host:
        cmd.append(f"--host={args.host}")
    if args.port:
        cmd.append(f"--port={args.port}")
    if args.socket:
        cmd.append(f"--socket={args.socket}")
    if not args.login_path:
        cmd.append("-p")  # the client prompts on the terminal; the password never passes through this script
    cmd += ["-e", sql]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    if result.returncode != 0:
        sys.exit(f"mysql exited with code {result.returncode} (error shown above).")
    return parse_batch(result.stdout)


def parse_batch(text):
    """Parse `mysql --batch` output: tab-separated, header row first, NULL as the word NULL."""
    lines = [line for line in text.splitlines() if line]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = [None if v == "NULL" else v for v in line.split("\t")]
        rows.append(dict(zip(header, values)))
    return rows


def md(value):
    """Format a value for a Markdown table cell."""
    if value is None or value == "":
        return ""
    return str(value).replace("|", "\\|")


def to_markdown(rows, database, sql, run_at):
    out = [
        f"# Data dictionary metadata: `{database}`",
        "",
        f"Generated {run_at} by `scripts/extract_data_dictionary.py` from the live database.",
        "Descriptions are blank until written or confirmed by Nathan or Nick.",
        "",
        "Query used:",
        "",
        "```sql",
        sql,
        "```",
        "",
    ]
    if not rows:
        out.append(f"No base tables found in `{database}`.")
        return "\n".join(out) + "\n"
    tables = {}
    for r in rows:
        tables.setdefault(r["table_name"], []).append(r)
    out.append(f"Tables: {len(tables)}. Columns: {len(rows)}.")
    out.append("")
    for table, cols in tables.items():
        pk = [c["column_name"] for c in cols if c["is_pk"] not in (None, "0")]
        fks = [c for c in cols if c["references_to"]]
        out += [
            f"## `{table}`",
            "",
            f"- Primary key: {', '.join(f'`{c}`' for c in pk) if pk else 'none defined'}",
            f"- Foreign keys: {len(fks)}",
            "- Table description: to be written",
            "",
            "| # | Column | MySQL type | Collation | Nullable | PK | References | Default | Extra | Description |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for c in cols:
            out.append("| " + " | ".join([
                md(c["position"]), f"`{md(c['column_name'])}`", f"`{md(c['column_type'])}`",
                md(c["collation_name"]), md(c["is_nullable"]), "PK" if c["is_pk"] not in (None, "0") else "",
                md(c["references_to"]), md(c["column_default"]), md(c["extra"]), "to be written",
            ]) + " |")
        out.append("")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_connection_args(parser)
    parser.add_argument("--output", type=Path, help="Write Markdown here (default: print it)")
    args = parser.parse_args()
    sql = QUERY.format(database=check_identifier(args.database, "database"))
    if args.dry_run:
        print(sql)
        return
    run_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    text = to_markdown(run_query(args, sql), args.database, sql, run_at)
    if args.output:
        args.output.write_text(text)
        print(f"Wrote {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
