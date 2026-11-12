"""Apply the team's duplicate-listing decisions to the working dataset.

Runs after build_working_dataset.py. It reads the six working CSVs and the
decisions file, and writes a new copy of all six to an output folder. Input
files are never changed.

  - Every event_id with action EXCLUDE is moved from working_events.csv to
    working_excluded_events.csv, with the decision's `reason` as
    exclusion_reason and metro_area_geoid taken from working_venues.csv.
  - KEEP rows are not applied; they are checked to still be in working_events.
  - Venues left with no remaining events are dropped from working_venues.csv
    (each is listed in the log), so every venue keeps at least one event.
    Excluded events can still reference these dropped venue IDs.
  - The other three working files are copied through unchanged.

Decisions file columns used: event_id, action (EXCLUDE/KEEP), reason,
duplicate_of_event_id (one ID, or several joined with " | "). Other columns
are ignored.

Run from the project root:
    python scripts/apply_dedup_decisions.py --input-dir "../processed copy"
    python scripts/apply_dedup_decisions.py --input-dir DIR --decisions FILE --output-dir DIR
Output defaults to <input-dir>/working_dedup_v2/.
"""
import argparse
import logging
import shutil
import sys
from pathlib import Path

import pandas as pd

import config

DEFAULT_DECISIONS = config.PROJECT_ROOT / "docs" / "dedup_decisions.csv"
EXPECTED_EXCLUDE = 167

EVENTS, EXCLUDED, VENUES = "working_events.csv", "working_excluded_events.csv", "working_venues.csv"
PASS_THROUGH = ["working_acs1_2025_metros.csv", "working_cbp2023_metros.csv", "market_labels.csv"]

log = logging.getLogger("apply_dedup")


def read(path):
    """Read a CSV as text so IDs keep their leading zeros; blanks stay missing."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def apply(input_dir, decisions_path):
    events, excluded = read(input_dir / EVENTS), read(input_dir / EXCLUDED)
    venues, decisions = read(input_dir / VENUES), read(decisions_path)
    log.info("Input: %d working events, %d excluded, %d venues, %d decisions",
             len(events), len(excluded), len(venues), len(decisions))

    # Checks on the decisions file before anything is applied.
    missing_cols = {"event_id", "action", "reason", "duplicate_of_event_id"} - set(decisions.columns)
    if missing_cols:
        raise ValueError(f"Decisions file is missing columns: {sorted(missing_cols)}")
    bad_actions = set(decisions["action"]) - {"EXCLUDE", "KEEP"}
    if bad_actions:
        raise ValueError(f"Unknown actions: {bad_actions}")
    if decisions["event_id"].duplicated().any():
        raise ValueError(f"Duplicate decision IDs: {sorted(decisions.loc[decisions['event_id'].duplicated(), 'event_id'])}")
    not_found = set(decisions["event_id"]) - set(events["event_id"])
    if not_found:
        raise ValueError(f"{len(not_found)} decision IDs are not in {EVENTS}: {sorted(not_found)[:10]}")
    exclude = decisions[decisions["action"] == "EXCLUDE"]
    if decisions["reason"].isna().any():
        raise ValueError("Some decisions have no reason")
    if len(exclude) != EXPECTED_EXCLUDE:
        raise ValueError(f"Expected {EXPECTED_EXCLUDE} EXCLUDE decisions, found {len(exclude)}")

    # Every listing an excluded one duplicates must stay in working_events.
    refs = exclude["duplicate_of_event_id"].dropna().str.split(r"\s*\|\s*").explode()
    kept_ids = set(events["event_id"]) - set(exclude["event_id"])
    bad_refs = set(refs) - kept_ids
    if bad_refs:
        raise ValueError(f"{len(bad_refs)} duplicate_of_event_id values are not kept events: {sorted(bad_refs)[:10]}")
    log.info("EXCLUDE without duplicate_of_event_id: %d (%s)", exclude["duplicate_of_event_id"].isna().sum(),
             exclude.loc[exclude["duplicate_of_event_id"].isna(), "reason"].value_counts().to_dict())

    # Move EXCLUDE rows, in the excluded file's own column layout.
    is_excluded = events["event_id"].isin(exclude["event_id"])
    moved = events[is_excluded].merge(exclude[["event_id", "reason"]], on="event_id")
    moved["metro_area_geoid"] = moved["venue_id"].map(venues.set_index("venue_id")["metro_area_geoid"])
    moved = moved.rename(columns={"reason": "exclusion_reason"})[list(excluded.columns)]
    new_events = events[~is_excluded]
    new_excluded = pd.concat([excluded, moved], ignore_index=True).sort_values(["exclusion_reason", "event_id"])
    log.info("Moved by reason: %s", moved["exclusion_reason"].value_counts().to_dict())

    # Drop venues with no remaining events, so every venue keeps at least one event.
    has_events = venues["venue_id"].isin(new_events["venue_id"])
    new_venues = venues[has_events]
    log.info("Venues dropped (no remaining events): %d", int((~has_events).sum()))
    for _, v in venues[~has_events].iterrows():
        log.info("  dropped venue %s  %s", v["venue_id"], v["venue_name"])
    return new_events, new_excluded, new_venues, decisions, len(events), len(excluded), len(venues)


def check(new_events, new_excluded, new_venues, decisions, n_events, n_excluded, n_venues):
    """Log the post-run checks. Returns a list of problems."""
    problems = []
    n_exclude = int((decisions["action"] == "EXCLUDE").sum())
    for label, got, want in [(EVENTS, len(new_events), n_events - n_exclude),
                             (EXCLUDED, len(new_excluded), n_excluded + n_exclude)]:
        log.info("%s rows: %d (expected %d)", label, got, want)
        if got != want:
            problems.append(f"{label}: {got} rows, expected {want}")
    overlap = set(new_events["event_id"]) & set(new_excluded["event_id"])
    log.info("Event IDs in both files: %d", len(overlap))
    if overlap:
        problems.append(f"{len(overlap)} event IDs in both files")
    for label, df in [(EVENTS, new_events), (EXCLUDED, new_excluded)]:
        if df["event_id"].duplicated().any():
            problems.append(f"duplicate event IDs in {label}")
    keep_missing = set(decisions.loc[decisions["action"] == "KEEP", "event_id"]) - set(new_events["event_id"])
    log.info("KEEP IDs missing from %s: %d", EVENTS, len(keep_missing))
    if keep_missing:
        problems.append(f"KEEP IDs missing: {sorted(keep_missing)}")
    if new_excluded["metro_area_geoid"].isna().any():
        problems.append("excluded rows with no metro_area_geoid")
    log.info("%s rows: %d (%d before)", VENUES, len(new_venues), n_venues)
    empty = int((~new_venues["venue_id"].isin(new_events["venue_id"])).sum())
    missing_venue = int((~new_events["venue_id"].isin(new_venues["venue_id"])).sum())
    log.info("Venues with no event: %d | events whose venue is missing: %d", empty, missing_venue)
    if empty or missing_venue:
        problems.append(f"{empty} venues with no event, {missing_venue} events with a missing venue")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input-dir", type=Path, required=True, help="Folder with the six working CSVs")
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS, help="Decisions CSV")
    parser.add_argument("--output-dir", type=Path, help="Defaults to <input-dir>/working_dedup_v2")
    args = parser.parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = (args.output_dir or input_dir / "working_dedup_v2").resolve()
    if output_dir == input_dir:
        sys.exit("Output folder must differ from the input folder; input files are never overwritten.")
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True,
                        handlers=[logging.FileHandler(output_dir / "apply_dedup_decisions.log", mode="w"),
                                  logging.StreamHandler(sys.stdout)])
    log.info("Input folder: %s | decisions: %s | output folder: %s", input_dir, args.decisions, output_dir)

    results = apply(input_dir, args.decisions)
    new_events, new_excluded, new_venues = results[:3]
    new_events.to_csv(output_dir / EVENTS, index=False)
    new_excluded.to_csv(output_dir / EXCLUDED, index=False)
    new_venues.to_csv(output_dir / VENUES, index=False)
    for name in PASS_THROUGH:
        shutil.copyfile(input_dir / name, output_dir / name)
    for name in [EVENTS, EXCLUDED, VENUES, *PASS_THROUGH]:
        df = read(output_dir / name)
        log.info("Wrote %s: %d rows, %d columns", name, len(df), len(df.columns))

    problems = check(*results)
    log.info("Problems: %s", problems or "none")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
