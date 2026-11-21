"""Drop the 8 ACS/CBP columns the team removed from the ERD.

Runs after apply_dedup_decisions.py. It reads the six working CSVs from the
input folder and writes a new copy of all six to the output folder. Input
files are never changed.

  - working_acs1_2025_metros.csv: drops geo_name, population_moe,
    population_note, median_household_income_moe, median_household_income_note.
    geo_name duplicates census_metro_name in market_labels.csv (METRO_AREA).
  - working_cbp2023_metros.csv: drops note, employees_noise_flag, published.
  - The other four files are copied through byte for byte.

All rows are kept, and the remaining columns keep their order. Everything is
read as text, so GEOIDs and NAICS codes keep their leading zeros and blanks
stay blank. The script stops with an error if any of the 8 columns is
missing. A log is written to <output-dir>/drop_erd_unused_columns.log.

Run from the project root:
    python3 scripts/drop_erd_unused_columns.py \
        --input-dir '../processed copy/working_dedup_v4' \
        --output-dir '../processed copy/working_dedup_v5'
"""
import argparse
import logging
import shutil
import sys
from pathlib import Path

import pandas as pd

DROP = {
    "working_acs1_2025_metros.csv": ["geo_name", "population_moe", "population_note",
                                     "median_household_income_moe", "median_household_income_note"],
    "working_cbp2023_metros.csv": ["note", "employees_noise_flag", "published"],
}
COPY = ["working_events.csv", "working_venues.csv", "working_excluded_events.csv", "market_labels.csv"]

log = logging.getLogger("drop_erd_unused_columns")


def read(path):
    """Read a CSV as text so IDs keep their leading zeros; blanks stay missing."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input-dir", type=Path, required=True, help="Folder with the six working CSVs")
    parser.add_argument("--output-dir", type=Path, required=True, help="New folder for the output")
    args = parser.parse_args()
    input_dir, output_dir = args.input_dir.resolve(), args.output_dir.resolve()
    if output_dir == input_dir:
        sys.exit("Output folder must differ from the input folder; input files are never overwritten.")

    # Check every input file and column before writing anything.
    frames = {}
    for name, cols in DROP.items():
        df = read(input_dir / name)
        missing = [c for c in cols if c not in df.columns]
        if missing:
            sys.exit(f"{name} is missing columns: {missing}")
        frames[name] = df
    for name in COPY:
        if not (input_dir / name).is_file():
            sys.exit(f"Missing input file: {input_dir / name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True,
                        handlers=[logging.FileHandler(output_dir / "drop_erd_unused_columns.log", mode="w"),
                                  logging.StreamHandler(sys.stdout)])
    log.info("Input folder: %s | output folder: %s", input_dir, output_dir)

    problems = []
    for name, cols in DROP.items():
        df = frames[name]
        out = df.drop(columns=cols)
        out.to_csv(output_dir / name, index=False)
        back = read(output_dir / name)
        log.info("%s: dropped %s", name, cols)
        log.info("  rows %d -> %d | columns %d -> %d | kept: %s",
                 len(df), len(back), len(df.columns), len(back.columns), list(back.columns))
        if len(back) != len(df):
            problems.append(f"{name}: row count changed")
        if not back.equals(df[list(back.columns)]):
            problems.append(f"{name}: remaining values differ from input")

    for name in COPY:
        shutil.copyfile(input_dir / name, output_dir / name)
        same = (input_dir / name).read_bytes() == (output_dir / name).read_bytes()
        log.info("%s: copied, byte-identical: %s", name, same)
        if not same:
            problems.append(f"{name}: copy differs from input")

    log.info("Problems: %s", problems or "none")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
