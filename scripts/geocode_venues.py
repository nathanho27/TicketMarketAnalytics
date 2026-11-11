"""Match every Ticketmaster venue to Census geographic identifiers.

Uses the Census Geocoder (no key needed). For each unique venue in a
processed events CSV it sends the venue's latitude/longitude and gets back
the Census areas that contain that point: state, county, county subdivision,
tract, ZIP Code Tabulation Area (ZCTA), incorporated place, metro/micro area
(CBSA), metropolitan division and combined statistical area. A venue
without coordinates is looked up by its street address instead.

A venue is never assigned to a city just because a city's 25-mile search
found it. place_geoid is blank when the venue is outside any incorporated
place.

Writes:
    data/raw/census/<run_stamp>/geocoder_venues.jsonl   one untouched response per line
    data/processed/venues_geocoded_<run_stamp>.csv      one row per venue
    logs/geocode_<run_stamp>.log
The .jsonl is written as it goes: re-running skips venues already geocoded.

Run from the project root (defaults to the newest events CSV):
    .venv/bin/python scripts/geocode_venues.py
    .venv/bin/python scripts/geocode_venues.py data/processed/ticketmaster_events_<run_stamp>.csv
"""
import json
import sys
from pathlib import Path

import pandas as pd

import config
from api_client import PoliteClient, log, setup_logging

COORDINATES_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
ADDRESS_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"
COMMON = {"benchmark": "Public_AR_Current", "vintage": "Current_Current", "layers": "all", "format": "json"}
MIN_INTERVAL = 0.4
SEP = " | "

# Output column prefix -> Census Geocoder layer name.
LAYERS = {
    "state": "States",
    "county": "Counties",
    "county_subdivision": "County Subdivisions",
    "tract": "Census Tracts",
    "zcta": "2020 Census ZIP Code Tabulation Areas",
    "place": "Incorporated Places",
    "metro_area": "Metropolitan Statistical Areas",
    "micro_area": "Micropolitan Statistical Areas",
    "metro_division": "Metropolitan Divisions",
    "combined_area": "Combined Statistical Areas",
}


def load_venues(events_csv):
    """One row per venue_id from the events CSV, with the cities whose searches found it."""
    df = pd.read_csv(events_csv, dtype={"venue_postal_code": str, "venue_id": str})
    first = df.groupby("venue_id").first()
    venues = first[["venue_name", "venue_address", "venue_city", "venue_state", "venue_postal_code",
                    "venue_country", "venue_latitude", "venue_longitude"]].copy()
    venues["event_count"] = df.groupby("venue_id").size()
    venues["search_cities"] = df.groupby("venue_id")["search_cities"].agg(
        lambda s: SEP.join(sorted({c for cell in s.dropna() for c in cell.split(SEP)})))
    return venues.reset_index()


def lookup(client, venue):
    """Return (method, http_status, body) for one venue."""
    if pd.notna(venue["venue_latitude"]) and pd.notna(venue["venue_longitude"]):
        params = {**COMMON, "x": venue["venue_longitude"], "y": venue["venue_latitude"]}
        status, body = client.get(COORDINATES_URL, params, quiet=True)
        return "coordinates", status, body
    parts = [venue["venue_address"], venue["venue_city"], venue["venue_state"], venue["venue_postal_code"]]
    address = ", ".join(str(p) for p in parts if pd.notna(p))
    if not address:
        return "none", None, None
    status, body = client.get(ADDRESS_URL, {**COMMON, "address": address}, quiet=True)
    return "address", status, body


def geographies(body):
    """The geographies object from either endpoint's response, or {}."""
    result = (body or {}).get("result") or {}
    if "geographies" in result:
        return result["geographies"]
    matches = result.get("addressMatches") or []
    return matches[0].get("geographies", {}) if matches else {}


def geo_fields(geos):
    out = {}
    for prefix, layer in LAYERS.items():
        hit = (geos.get(layer) or [{}])[0]
        out[f"{prefix}_geoid"] = hit.get("GEOID")
        out[f"{prefix}_name"] = hit.get("NAME")
    out["state_abbr"] = (geos.get("States") or [{}])[0].get("STUSAB")
    return out


def venue_flags(row):
    # pd.isna, not "not x": a missing value in a DataFrame row is NaN, which is truthy.
    flags = []
    if row["geocode_method"] == "none":
        flags.append("no_coordinates_or_address")
    elif pd.isna(row["county_geoid"]):
        flags.append("geocode_failed")
    else:
        if row["geocode_method"] == "address":
            flags.append("geocoded_from_address")
        if pd.isna(row["place_geoid"]):
            flags.append("outside_incorporated_place")
        if row["state_abbr"] != row["venue_state"]:
            flags.append("state_differs_from_ticketmaster")
        if pd.notna(row["venue_postal_code"]) and row["zcta_geoid"] != str(row["venue_postal_code"])[:5]:
            flags.append("zcta_differs_from_ticketmaster_zip")
        if pd.isna(row["metro_area_geoid"]) and pd.isna(row["micro_area_geoid"]):
            flags.append("outside_metro_micro_area")
    return SEP.join(flags) or None


def main(events_csv):
    events_csv = Path(events_csv)
    run_stamp = events_csv.stem.removeprefix("ticketmaster_events_")
    setup_logging(f"geocode_{run_stamp}")
    raw_dir = config.RAW_DIR / "census" / run_stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "geocoder_venues.jsonl"

    venues = load_venues(events_csv)
    done = {}
    if raw_path.exists():
        for line in raw_path.read_text().splitlines():
            rec = json.loads(line)
            if rec["http_status"] == 200:
                done[rec["venue_id"]] = rec
    log.info("Geocoding %d venues from %s (%d already done)", len(venues), events_csv.name, len(done))

    client = PoliteClient("CensusGeocoder", MIN_INTERVAL, timeout=60)
    with raw_path.open("a") as out:
        for i, venue in venues.iterrows():
            if venue["venue_id"] in done:
                continue
            method, status, body = lookup(client, venue)
            rec = {"venue_id": venue["venue_id"], "method": method, "http_status": status, "response": body}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            done[venue["venue_id"]] = rec
            if status != 200:
                log.warning("Venue %s (%s): HTTP %s", venue["venue_id"], venue["venue_name"], status)
            if (i + 1) % 100 == 0:
                log.info("  %d/%d venues", i + 1, len(venues))

    rows = []
    for _, venue in venues.iterrows():
        rec = done.get(venue["venue_id"], {"method": "none", "http_status": None, "response": None})
        rows.append({**venue.to_dict(), "geocode_method": rec["method"], "geocode_http_status": rec["http_status"],
                     **geo_fields(geographies(rec["response"]))})
    df = pd.DataFrame(rows)
    df["geocode_flags"] = df.apply(venue_flags, axis=1)

    out_csv = config.PROCESSED_DIR / f"venues_geocoded_{run_stamp}.csv"
    df.to_csv(out_csv, index=False)
    flags = df["geocode_flags"].dropna().str.split(SEP, regex=False).explode().value_counts()
    log.info("Matched to a county: %d of %d venues", int(df["county_geoid"].notna().sum()), len(df))
    log.info("Flags:\n%s", flags.to_string() if len(flags) else "none")
    log.info("Saved %s", out_csv.relative_to(config.PROJECT_ROOT))


def latest_events_csv():
    files = sorted(config.PROCESSED_DIR.glob("ticketmaster_events_*.csv"))
    if not files:
        sys.exit("No processed events CSV; run convert_to_csv.py first")
    return files[-1]


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else latest_events_csv())
