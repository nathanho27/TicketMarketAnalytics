"""Collect Census data for the venues and search areas of one collection run.

Needs CENSUS_API_KEY in .env and data/processed/venues_geocoded_<run_stamp>.csv
(from geocode_venues.py). Collects:

  ACS 2025 1-year (B01003 population, B19013 median household income)
      places, counties, metro/micro areas (areas with 65,000+ people only)
  ACS 2020-2024 5-year (same tables)
      census tracts (every tract in the states we need), ZCTAs, places,
      counties, metro/micro areas
  County Business Patterns 2023 establishment counts for NAICS
      711310 promoters with facilities (venue operators), 711320 promoters
      without facilities, 7113 all promoters, 7112 spectator sports,
      711211 sports teams and clubs; by county, metro/micro area and ZIP code
  Search-area tracts: every 2020 census tract whose internal point is within
      25 miles of a city's search point (Census 2025 Gazetteer file)

Missing and suppressed values are kept as blanks with a note column, never
as zero:
  ACS special codes (e.g. -666666666 "estimate not available") -> blank + note.
  CBP cells with fewer than 3 establishments are not published by Census.
  For the counties, metro areas and ZIPs that matter to us, those cells are
  written as rows with published=False and a blank count ("0-2 establishments").

Writes raw API responses to data/raw/census/<run_stamp>/ and processed CSVs to
data/processed/:
    census_acs1_2025_<run>.csv  census_acs5_2024_<run>.csv
    census_cbp2023_<run>.csv    search_area_tracts_<run>.csv

Run from the project root (defaults to the newest venues_geocoded CSV):
    .venv/bin/python scripts/collect_census.py
"""
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

import config
from api_client import USER_AGENT, PoliteClient, log, redact, setup_logging

API = "https://api.census.gov/data"
REFERENCE_DIR = config.RAW_DIR / "census"
GAZETTEER_TRACTS_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_tracts_national.zip"
# CBP's own employment noise flags (G/H/J) are only in the bulk files; the API's EMP_N is always 0.
CBP_BULK = {"county": "https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip",
            "metro_micro_area": "https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23msa.zip"}

ACS_VARS = "NAME,B01003_001E,B01003_001M,B19013_001E,B19013_001M"
MSA = "metropolitan statistical area/micropolitan statistical area"
CBP_NAICS = {
    "711310": "Promoters of performing arts, sports, and similar events with facilities",
    "711320": "Promoters of performing arts, sports, and similar events without facilities",
    "7113": "Promoters of performing arts, sports, and similar events",
    "7112": "Spectator sports",
    "711211": "Sports teams and clubs",
}

# ACS special values (Census "Notes on ACS API variable types").
ACS_ESTIMATE_CODES = {
    -666666666: "estimate not available (no or too few sample observations)",
    -999999999: "estimate not available (too few sample observations)",
    -888888888: "not applicable",
    -222222222: "estimate not available",
}
ACS_MOE_CODES = {
    -555555555: "no margin of error (controlled estimate)",
    -333333333: "margin of error not available (median in open-ended interval)",
    -222222222: "margin of error not available (too few sample observations)",
    -999999999: "margin of error not available",
    -888888888: "not applicable",
}
INCOME_TOP, INCOME_BOTTOM = 250001, 2499  # ACS codes for "$250,000+" and "$2,499 or less"
STATE_ABBR_TO_FIPS = {
    "AZ": "04", "CA": "06", "CO": "08", "DC": "11", "DE": "10", "FL": "12", "IL": "17", "IN": "18",
    "MA": "25", "MD": "24", "NC": "37", "NJ": "34", "NM": "35", "NV": "32", "NY": "36", "OH": "39",
    "OK": "40", "PA": "42", "SC": "45", "TN": "47", "TX": "48", "VA": "51", "WA": "53",
}


# ---------------------------------------------------------------------------
# API calls (every response is kept for the raw files)
# ---------------------------------------------------------------------------

class CensusAPI:
    def __init__(self, key):
        self.key = key
        self.client = PoliteClient("CensusAPI", 0.2, timeout=180)
        self.records = {}

    def get(self, dataset_label, path, params):
        """GET one Census table. Returns a DataFrame (empty on failure) and keeps the raw response."""
        full = {**params, "key": self.key}
        status, body = self.client.get(f"{API}/{path}", full)
        self.records.setdefault(dataset_label, []).append({
            "path": path, "params": redact(full), "http_status": status,
            "requested_at": datetime.now().isoformat(timespec="seconds"), "response": body})
        if status != 200 or not body:
            log.error("FAILED %s %s %s", dataset_label, path, redact(params))
            return pd.DataFrame()
        header = body[0]
        # Predicate variables (e.g. NAICS2017) can appear twice in the header; keep the first.
        keep = [i for i, h in enumerate(header) if h not in header[:i]]
        return pd.DataFrame([[r[i] for i in keep] for r in body[1:]], columns=[header[i] for i in keep])


# ---------------------------------------------------------------------------
# ACS
# ---------------------------------------------------------------------------

def acs_value(raw, codes):
    """(number_or_None, note_or_None) for one ACS cell."""
    if raw in (None, ""):
        return None, "missing in API response"
    value = float(raw)
    if int(value) in codes:
        return None, codes[int(value)]
    return value, None


def tidy_acs(df, level, geoid_cols, dataset, vintage):
    """Standard ACS columns for one geography level; special codes become blanks + notes."""
    if df.empty:
        return df
    out = pd.DataFrame({
        "dataset": dataset, "vintage": vintage, "geo_level": level,
        "geoid": df[geoid_cols].astype(str).agg("".join, axis=1),
        "geo_name": df["NAME"],
        "state_fips": df["state"] if "state" in df else None,
    })
    for var, name in (("B01003_001", "population"), ("B19013_001", "median_household_income")):
        est = df[f"{var}E"].map(lambda v: acs_value(v, ACS_ESTIMATE_CODES))
        moe = df[f"{var}M"].map(lambda v: acs_value(v, ACS_MOE_CODES))
        out[name] = [v for v, _ in est]
        out[f"{name}_moe"] = [v for v, _ in moe]
        notes = [" ; ".join(n for n in (en, mn) if n) or None for (_, en), (_, mn) in zip(est, moe)]
        if name == "median_household_income":
            notes = [("top-coded: $250,000 or more" if v == INCOME_TOP else
                      "bottom-coded: $2,499 or less" if v == INCOME_BOTTOM else n)
                     for (v, _), n in zip(est, notes)]
        out[f"{name}_note"] = notes
    return out


def collect_acs1(api):
    parts = [
        tidy_acs(api.get("acs1_2025", "2025/acs/acs1", {"get": ACS_VARS, "for": "place:*", "in": "state:*"}),
                 "place", ["state", "place"], "ACS 1-year", "2025"),
        tidy_acs(api.get("acs1_2025", "2025/acs/acs1", {"get": ACS_VARS, "for": "county:*", "in": "state:*"}),
                 "county", ["state", "county"], "ACS 1-year", "2025"),
        tidy_acs(api.get("acs1_2025", "2025/acs/acs1", {"get": ACS_VARS, "for": f"{MSA}:*"}),
                 "metro_micro_area", [MSA], "ACS 1-year", "2025"),
    ]
    return pd.concat(parts, ignore_index=True)


def collect_acs5(api, state_fips):
    parts = []
    for st in sorted(state_fips):
        df = api.get("acs5_2024", "2024/acs/acs5",
                     {"get": ACS_VARS, "for": "tract:*", "in": [f"state:{st}", "county:*"]})
        parts.append(tidy_acs(df, "tract", ["state", "county", "tract"], "ACS 5-year", "2020-2024"))
    zcta = api.get("acs5_2024", "2024/acs/acs5", {"get": ACS_VARS, "for": "zip code tabulation area:*"})
    parts.append(tidy_acs(zcta, "zcta", ["zip code tabulation area"], "ACS 5-year", "2020-2024"))
    parts.append(tidy_acs(api.get("acs5_2024", "2024/acs/acs5", {"get": ACS_VARS, "for": "place:*", "in": "state:*"}),
                          "place", ["state", "place"], "ACS 5-year", "2020-2024"))
    parts.append(tidy_acs(api.get("acs5_2024", "2024/acs/acs5", {"get": ACS_VARS, "for": "county:*", "in": "state:*"}),
                          "county", ["state", "county"], "ACS 5-year", "2020-2024"))
    parts.append(tidy_acs(api.get("acs5_2024", "2024/acs/acs5", {"get": ACS_VARS, "for": f"{MSA}:*"}),
                          "metro_micro_area", [MSA], "ACS 5-year", "2020-2024"))
    return pd.concat(parts, ignore_index=True)


# ---------------------------------------------------------------------------
# County Business Patterns
# ---------------------------------------------------------------------------

def download(url, path):
    if not path.exists():
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=300)
        resp.raise_for_status()
        path.write_bytes(resp.content)
        log.info("Downloaded %s", path.relative_to(config.PROJECT_ROOT))
    return path


def bulk_noise_flags():
    """{(geo_level, geoid, naics): G/H/J} from the CBP 2023 bulk county and metro files."""
    flags = {}
    for level, url in CBP_BULK.items():
        path = download(url, REFERENCE_DIR / url.rsplit("/", 1)[-1])
        df = pd.read_csv(path, dtype=str)
        df["naics_code"] = df["naics"].str.rstrip("/")
        df = df[df["naics_code"].isin(CBP_NAICS)]
        geoid = (df["fipstate"] + df["fipscty"]) if level == "county" else df["msa"]
        flags.update({(level, g, n): f for g, n, f in zip(geoid, df["naics_code"], df["emp_nf"])})
    return flags


def collect_cbp(api, venues, circle_counties):
    geos = {"county": ("county:*", "state:*", ["state", "county"]),
            "metro_micro_area": (f"{MSA}:*", None, [MSA]),
            "zip": ("zip code:*", None, ["zip code"])}
    parts = []
    for code in CBP_NAICS:
        for level, (for_, in_, id_cols) in geos.items():
            params = {"get": "NAME,NAICS2017,ESTAB,EMP", "NAICS2017": code, "for": for_}
            if in_:
                params["in"] = in_
            df = api.get("cbp_2023", "2023/cbp", params)
            if df.empty:
                continue
            parts.append(pd.DataFrame({
                "dataset": "County Business Patterns", "vintage": "2023", "geo_level": level,
                "geoid": df[id_cols].astype(str).agg("".join, axis=1), "geo_name": df["NAME"],
                "naics_code": code, "naics_label": CBP_NAICS[code],
                "establishments": pd.to_numeric(df["ESTAB"]),
                # ZIP-level CBP has establishment counts only; the API's EMP there is a placeholder 0.
                "employees": pd.to_numeric(df["EMP"]) if level != "zip" else None,
                "published": True, "note": None,
            }))
    cbp = pd.concat(parts, ignore_index=True)

    noise = bulk_noise_flags()
    cbp["employees_noise_flag"] = [noise.get((l, g, n)) for l, g, n in zip(cbp.geo_level, cbp.geoid, cbp.naics_code)]
    cbp.loc[cbp.geo_level == "zip", "note"] = "ZIP-level CBP publishes establishment counts only"

    # Explicit "not published" rows for the geographies tied to our venues and search areas.
    wanted = {
        "county": set(venues["county_geoid"].dropna()) | circle_counties,
        "metro_micro_area": set(venues["metro_area_geoid"].dropna()) | set(venues["micro_area_geoid"].dropna()),
        "zip": set(venues["venue_postal_code"].dropna().str[:5]) | set(venues["zcta_geoid"].dropna()),
    }
    published = set(zip(cbp.geo_level, cbp.geoid, cbp.naics_code))
    missing = [{"dataset": "County Business Patterns", "vintage": "2023", "geo_level": level, "geoid": g,
                "geo_name": None, "naics_code": code, "naics_label": CBP_NAICS[code],
                "establishments": None, "employees": None, "published": False,
                "note": "not published: fewer than 3 establishments (0-2)", "employees_noise_flag": None}
               for level, ids in wanted.items() for g in sorted(ids) for code in CBP_NAICS
               if (level, g, code) not in published]
    return pd.concat([cbp, pd.DataFrame(missing)], ignore_index=True)


# ---------------------------------------------------------------------------
# Search-area tracts
# ---------------------------------------------------------------------------

def search_area_tracts():
    """Tracts whose internal point is within RADIUS_MILES of each city's search point."""
    path = download(GAZETTEER_TRACTS_URL, REFERENCE_DIR / "2025_Gaz_tracts_national.zip")
    g = pd.read_csv(path, sep="|", dtype={"GEOID": str})
    g.columns = [c.strip() for c in g.columns]
    rows = []
    lat, lon = np.radians(g["INTPTLAT"].to_numpy()), np.radians(g["INTPTLONG"].to_numpy())
    for key, city in config.CITIES.items():
        # Great-circle (haversine) distance in miles from the city's search point.
        lat0, lon0 = math.radians(city["lat"]), math.radians(city["lon"])
        h = np.sin((lat - lat0) / 2) ** 2 + math.cos(lat0) * np.cos(lat) * np.sin((lon - lon0) / 2) ** 2
        dist = pd.Series(3958.8 * 2 * np.arcsin(np.sqrt(h)), index=g.index)
        inside = g[dist <= config.RADIUS_MILES]
        rows.append(pd.DataFrame({
            "search_city": key, "tract_geoid": inside["GEOID"], "county_geoid": inside["GEOID"].str[:5],
            "state_fips": inside["GEOID"].str[:2], "state_abbr": inside["USPS"],
            "internal_point_lat": inside["INTPTLAT"], "internal_point_lon": inside["INTPTLONG"],
            "distance_miles": dist[inside.index].round(2), "land_area_sqmi": inside["ALAND_SQMI"]}))
    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------------------

def main(venues_csv):
    venues_csv = Path(venues_csv)
    run_stamp = venues_csv.stem.removeprefix("venues_geocoded_")
    setup_logging(f"census_{run_stamp}")
    load_dotenv(config.PROJECT_ROOT / ".env")
    api = CensusAPI(os.environ["CENSUS_API_KEY"].strip())
    raw_dir = config.RAW_DIR / "census" / run_stamp
    raw_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now().isoformat(timespec="seconds")

    venues = pd.read_csv(venues_csv, dtype=str)
    tracts = search_area_tracts()
    circle_counties = set(tracts["county_geoid"])
    state_fips = set(tracts["state_fips"]) | set(venues["state_geoid"].dropna())
    log.info("Search-area tracts: %d rows (%d unique tracts, %d counties, %d states)", len(tracts),
             tracts["tract_geoid"].nunique(), len(circle_counties), tracts["state_fips"].nunique())

    acs1 = collect_acs1(api)
    acs5 = collect_acs5(api, state_fips)
    cbp = collect_cbp(api, venues, circle_counties)

    for label, records in api.records.items():
        (raw_dir / f"{label}.json").write_text(json.dumps({
            "source": "Census Data API", "dataset": label, "collected_at": started, "requests": records}))
    out = {f"census_acs1_2025_{run_stamp}.csv": acs1, f"census_acs5_2024_{run_stamp}.csv": acs5,
           f"census_cbp2023_{run_stamp}.csv": cbp, f"search_area_tracts_{run_stamp}.csv": tracts}
    for name, df in out.items():
        df.to_csv(config.PROCESSED_DIR / name, index=False)
        log.info("Saved %s (%d rows)", name, len(df))

    failed = sum(r["http_status"] != 200 for recs in api.records.values() for r in recs)
    log.info("Census API requests: %d, failed: %d", sum(len(r) for r in api.records.values()), failed)
    for label, df in (("ACS 1-year", acs1), ("ACS 5-year", acs5)):
        log.info("%s rows by level: %s", label, df["geo_level"].value_counts().to_dict())
        log.info("%s blank population: %d, blank income: %d", label,
                 int(df["population"].isna().sum()), int(df["median_household_income"].isna().sum()))
    log.info("CBP rows: %d published, %d not published (0-2)",
             int(cbp["published"].sum()), int((~cbp["published"]).sum()))


def latest_venues_csv():
    files = sorted(config.PROCESSED_DIR.glob("venues_geocoded_*.csv"))
    if not files:
        sys.exit("No venues_geocoded CSV; run geocode_venues.py first")
    return files[-1]


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else latest_venues_csv())
