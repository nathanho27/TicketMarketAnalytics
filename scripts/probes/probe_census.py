"""Exploratory probe: can our Ticketmaster venues be matched to Census areas?

No Census API key needed:
  1. Census Geocoder (geocoding.geo.census.gov) turns each venue's lat/lon
     into state, county, tract, ZCTA, place and metro-area codes.
  2. ACS 5-year 2020-2024 table files (population B01003, median household
     income B19013) give values for those areas.
  3. County Business Patterns 2023 county and ZIP files give live-event
     industry establishment counts (NAICS 711310, 7113, 711211).

Bulk files must already be in data/raw/census/ (downloaded from www2.census.gov):
    acsdt5y2024-b01003.dat, acsdt5y2024-b19013.dat, cbp23co.zip, zbp23detail.zip
Writes:
    data/raw/census/geocoder_<run_stamp>.json        untouched geocoder responses
    data/processed/census_probe_<run_stamp>.csv      one row per venue
Not part of the pipeline. Run from the project root:
    .venv/bin/python scripts/probes/probe_census.py
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

CENSUS_DIR = config.RAW_DIR / "census"
GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
USER_AGENT = "TicketMarketAnalytics-class-project/0.1 (github.com/nathanho27/TicketMarketAnalytics)"
MIN_INTERVAL = 0.5
# CBP pads codes shorter than 6 digits with "/" (e.g. 4-digit 7113 is "7113//").
LIVE_EVENT_NAICS = {"711310": "venues_with_facilities", "7113//": "all_promoters", "711211": "sports_teams"}
# ACS special values: the estimate or margin could not be computed.
ACS_MISSING = {-666666666, -999999999, -888888888, -222222222, -555555555}

# GEO_ID prefixes in the ACS table files.
ACS_PREFIX = {"tract": "1400000US", "county": "0500000US", "zcta": "860Z200US",
              "place": "1600000US", "msa": "310M700US"}
GEOCODER_LAYER = {"state": "States", "county": "Counties", "tract": "Census Tracts",
                  "zcta": "2020 Census ZIP Code Tabulation Areas",
                  "place": "Incorporated Places", "msa": "Metropolitan Statistical Areas"}


def load_venues():
    csv = sorted(config.PROCESSED_DIR.glob("ticketmaster_events_*.csv"))[-1]
    df = pd.read_csv(csv, dtype={"venue_postal_code": str})
    events = df.groupby("venue_id").size().rename("event_count")
    venues = df.drop_duplicates("venue_id")[[
        "venue_id", "venue_name", "venue_city", "venue_state", "venue_postal_code",
        "venue_latitude", "venue_longitude", "primary_search_city"]].set_index("venue_id")
    return venues.join(events).reset_index()


def geocode(session, lat, lon):
    params = {"x": lon, "y": lat, "benchmark": "Public_AR_Current",
              "vintage": "Current_Current", "layers": "all", "format": "json"}
    resp = session.get(GEOCODER_URL, params=params, timeout=60)
    return resp.status_code, resp.json() if resp.ok else {"error_body": resp.text[:500]}


def geography_fields(body):
    geos = (body.get("result") or {}).get("geographies") or {}
    out = {}
    for key, layer in GEOCODER_LAYER.items():
        hit = (geos.get(layer) or [{}])[0]
        out[f"{key}_geoid"] = hit.get("GEOID")
        out[f"{key}_name"] = hit.get("NAME")
    out["state_abbr"] = (geos.get("States") or [{}])[0].get("STUSAB")
    return out


def load_acs(table, column):
    """{GEO_ID: estimate} from an ACS table file; special 'not available' codes become None."""
    df = pd.read_csv(CENSUS_DIR / f"acsdt5y2024-{table}.dat", sep="|", dtype={"GEO_ID": str})
    values = df.set_index("GEO_ID")[column]
    return {g: (None if v in ACS_MISSING else v) for g, v in values.items()}


def load_cbp_county():
    """County establishment counts for the live-event NAICS codes, with employment-noise flags."""
    df = pd.read_csv(CENSUS_DIR / "cbp23co.zip", dtype=str)
    df = df[df["naics"].isin(LIVE_EVENT_NAICS)]
    df["county_geoid"] = df["fipstate"] + df["fipscty"]
    return df.set_index(["county_geoid", "naics"])[["est", "emp", "emp_nf"]]


def load_zbp():
    df = pd.read_csv(CENSUS_DIR / "zbp23detail.zip", dtype=str)
    df = df[df["naics"].isin(LIVE_EVENT_NAICS)]
    return df.set_index(["zip", "naics"])["est"]


def main():
    venues = load_venues()
    run_stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    raw, rows = [], []
    for i, v in venues.iterrows():
        time.sleep(MIN_INTERVAL)
        status, body = geocode(session, v["venue_latitude"], v["venue_longitude"])
        raw.append({"venue_id": v["venue_id"], "lat": v["venue_latitude"], "lon": v["venue_longitude"],
                    "http_status": status, "response": body})
        rows.append({**v.to_dict(), "geocoder_status": status, **geography_fields(body)})
        print(f"{i + 1:3d}/{len(venues)} HTTP {status} {v['venue_name']}")
    (CENSUS_DIR / f"geocoder_{run_stamp}.json").write_text(json.dumps(raw, indent=1))
    df = pd.DataFrame(rows)

    population = load_acs("b01003", "B01003_E001")
    income = load_acs("b19013", "B19013_E001")
    for level, prefix in ACS_PREFIX.items():
        ids = prefix + df[f"{level}_geoid"].fillna("")
        df[f"{level}_population"] = ids.map(population)
        df[f"{level}_median_hh_income"] = ids.map(income)

    cbp, zbp = load_cbp_county(), load_zbp()
    for code, label in LIVE_EVENT_NAICS.items():
        df[f"county_est_{label}"] = [cbp["est"].get((g, code)) for g in df["county_geoid"]]
        df[f"county_emp_flag_{label}"] = [cbp["emp_nf"].get((g, code)) for g in df["county_geoid"]]
        df[f"zip_est_{label}"] = [zbp.get((z, code)) for z in df["venue_postal_code"]]

    out = config.PROCESSED_DIR / f"census_probe_{run_stamp}.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} venues to {out.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
