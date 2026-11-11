"""Data-quality report for one collection run. Read-only: it changes no files.

Checks, for the run's files in data/processed/ (and the raw manifest):
  Ticketmaster  completeness against totalElements, failed requests, events
                per city, listed-price coverage, quality flags, overlaps
  Venues        how many matched to Census areas, geocoding flags
  Census        blank/suppressed ACS values by level, CBP published vs not,
                and whether each venue's county/tract/ZCTA has Census values

"Listed price" means Ticketmaster priceRanges, not verified face value.

Run from the project root (defaults to the newest run):
    .venv/bin/python scripts/evaluate_collection.py
    .venv/bin/python scripts/evaluate_collection.py <run_stamp>
"""
import json
import sys

import pandas as pd

import config

SEP = " | "
problems = []


def pct(part, whole):
    return f"{part}/{whole} ({part / whole:.0%})" if whole else "0/0"


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def flag_counts(series):
    # regex=False: "|" would otherwise be read as a regular-expression "or".
    return series.dropna().str.split(SEP, regex=False).explode().value_counts()


def check_manifest(run):
    path = config.RAW_DIR / "ticketmaster" / run / "manifest.json"
    if not path.exists():
        print("No manifest (pilot run?); completeness check skipped.")
        return
    m = json.loads(path.read_text())
    print(f"Requests: {m['total_requests']} | events received (before de-duplication): {m['total_events_received']}")
    print(f"Event window: {m['event_window'][0]} to {m['event_window'][1]} | radius {m['radius_miles']} mi | country {m['country_code']}")
    failed = sum(w["failed_requests"] for c in m["cities"].values() for w in c["windows"])
    print(f"Failed requests: {failed} | incomplete search windows: {m['incomplete_window_count']}")
    if failed or m["incomplete_window_count"]:
        problems.append(f"Ticketmaster: {failed} failed requests, {m['incomplete_window_count']} incomplete windows")
        for city, c in m["cities"].items():
            for w in c["incomplete_windows"]:
                print(f"  INCOMPLETE {city} {w['segment']} {w['window']}: {w['events_received']} of {w['total_elements']}")


def check_events(run):
    events = pd.read_csv(config.PROCESSED_DIR / f"ticketmaster_events_{run}.csv", low_memory=False)
    excluded = pd.read_csv(config.PROCESSED_DIR / f"ticketmaster_excluded_{run}.csv", low_memory=False)
    n = len(events)
    print(f"Events kept: {n} | unique event IDs: {events['event_id'].nunique()} | excluded: {len(excluded)}")
    if events["event_id"].nunique() != n:
        problems.append("Ticketmaster: duplicate event IDs in events CSV")
    print("Excluded by reason:", excluded["exclusion_reason"].value_counts().to_dict())
    print(f"Unique venues: {events['venue_id'].nunique()} | date range: {events['local_date'].min()} to {events['local_date'].max()}")
    print(f"Events found by more than one search area: {int((events['search_city_count'] > 1).sum())}")
    print(events.loc[events["search_city_count"] > 1, "search_cities"].value_counts().to_string())

    # Count each event once per search area that found it (overlapping areas both count it).
    per_city = events.assign(city=events["search_cities"].str.split(SEP, regex=False)).explode("city")
    t = per_city.groupby("city").agg(
        events=("event_id", "size"),
        music=("segment", lambda s: int((s == "Music").sum())),
        sports=("segment", lambda s: int((s == "Sports").sum())),
        venues=("venue_id", "nunique"),
        listed_price=("has_listed_price", "sum"),
    )
    t["listed_price_pct"] = (t["listed_price"] / t["events"]).map("{:.0%}".format)
    print("\nPer search area (an event in two overlapping areas counts in both):")
    print(t.sort_values("events", ascending=False).to_string())
    missing = set(config.CITIES) - set(t.index)
    if missing:
        problems.append(f"Ticketmaster: no events for {sorted(missing)}")

    print("\nBy segment and status:")
    print(events.groupby(["segment", "status"], dropna=False).size().to_string())
    print(f"\nWith any priceRanges: {pct(int((events['price_range_count'] > 0).sum()), n)}")
    print(f"With a usable listed price: {pct(int(events['has_listed_price'].sum()), n)}")
    print("Listed price by ticketing platform:")
    print(events.groupby("ticketing_platform").agg(events=("event_id", "size"),
                                                   listed=("has_listed_price", "sum")).to_string())
    print("\nQuality flags (an event can have several):")
    print(flag_counts(events["quality_flags"]).to_string())
    return events


def check_venues(run, events):
    path = config.PROCESSED_DIR / f"venues_geocoded_{run}.csv"
    if not path.exists():
        problems.append("Venues: no venues_geocoded file")
        return None
    v = pd.read_csv(path, dtype=str)
    n = len(v)
    print(f"Venues: {n} (events CSV has {events['venue_id'].nunique()})")
    if n != events["venue_id"].nunique():
        problems.append("Venues: count differs from events CSV")
    for col in ("county", "tract", "zcta", "place", "metro_area", "micro_area"):
        print(f"  matched {col:12s} {pct(int(v[f'{col}_geoid'].notna().sum()), n)}")
    print("Geocoding flags:")
    print(flag_counts(v["geocode_flags"]).to_string())
    failed = int(v["geocode_flags"].fillna("").str.contains("geocode_failed|no_coordinates", regex=True).sum())
    if failed:
        problems.append(f"Venues: {failed} not matched to Census areas")
    return v


def check_census(run, venues):
    for name in ("census_acs1_2025", "census_acs5_2024"):
        path = config.PROCESSED_DIR / f"{name}_{run}.csv"
        if not path.exists():
            problems.append(f"Census: missing {path.name}")
            continue
        df = pd.read_csv(path, dtype={"geoid": str})
        print(f"\n{name}: {len(df)} rows")
        print(df.groupby("geo_level").agg(rows=("geoid", "size"),
                                          blank_population=("population", lambda s: int(s.isna().sum())),
                                          blank_income=("median_household_income", lambda s: int(s.isna().sum()))).to_string())
        if venues is not None:
            for level, col in (("county", "county_geoid"), ("tract", "tract_geoid"), ("zcta", "zcta_geoid"),
                               ("place", "place_geoid"), ("metro_micro_area", "metro_area_geoid")):
                sub = df[df["geo_level"] == level].set_index("geoid")
                if sub.empty:
                    continue
                ids = venues[col].dropna()
                has_income = ids.map(sub["median_household_income"]).notna().sum()
                print(f"  venues whose {level} has income: {pct(int(has_income), len(ids))} (of venues with a {level})")

    path = config.PROCESSED_DIR / f"census_cbp2023_{run}.csv"
    if path.exists():
        cbp = pd.read_csv(path, dtype={"geoid": str, "naics_code": str})
        print(f"\ncensus_cbp2023: {len(cbp)} rows")
        print(cbp.groupby(["geo_level", "naics_code"])["published"].agg(
            published="sum", not_published=lambda s: int((~s).sum())).to_string())
    else:
        problems.append("Census: missing CBP file")

    path = config.PROCESSED_DIR / f"search_area_tracts_{run}.csv"
    if path.exists():
        t = pd.read_csv(path, dtype={"tract_geoid": str})
        print(f"\nsearch_area_tracts: {len(t)} rows, {t['tract_geoid'].nunique()} unique tracts, "
              f"{t['search_city'].nunique()} search areas")


def main(run):
    section(f"Ticketmaster run {run}: completeness")
    check_manifest(run)
    section("Ticketmaster events")
    events = check_events(run)
    section("Venue geocoding")
    venues = check_venues(run, events)
    section("Census data")
    check_census(run, venues)
    section("Problems found")
    print("\n".join(f"- {p}" for p in problems) or "None")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        files = sorted(config.PROCESSED_DIR.glob("ticketmaster_events_*.csv"))
        if not files:
            sys.exit("No processed Ticketmaster CSVs yet; run convert_to_csv.py first")
        main(files[-1].stem.removeprefix("ticketmaster_events_"))
