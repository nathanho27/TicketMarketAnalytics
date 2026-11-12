"""Build the reduced working dataset from the processed CSVs of one collection run.

Applies the scope decisions Nathan and Nick made on 2026-11-11 (recorded in
docs/project_decisions.md). It only reads the existing processed CSVs and
writes new files; no raw or processed file is changed.

Scope applied:
  - Markets: 24 Census metro areas (Dallas and Fort Worth share one metro).
    Each event belongs to the metro of its venue (from venues_geocoded).
  - Events outside the 24 metros are excluded (outside_24_metros).
  - Listings that are not standalone live events are excluded: an art-museum
    reception and an F1 afterparty ticket package (non_event_admission), and
    a Zumba fitness class (non_event_fitness_class). The 15 Belmont Park
    racing days are kept.
  - Ticket packages (hotel, VIP and multi-day bundles) that duplicate a
    regular listing of the same event are excluded (ticket_package_duplicate).
    One package is kept because it is the only listing of its concert.
  - Event columns kept: ID, name, URL, status, local date and time, segment
    and genre (names and IDs), subgenre for Sports only, venue ID, ticketing
    platform. Subgenre is blank for all non-Sports events.
  - Venue columns kept: Ticketmaster venue name/address/coordinates and the
    geocoded metro area ID.
  - Census: ACS 2025 1-year and CBP 2023 (NAICS 711310, 711320, 7112), metro
    level only, for the 24 metros. Missing and unpublished values stay blank.

Writes to data/processed/working_<run_stamp>/:
    working_events.csv, working_venues.csv, working_acs1_2025_metros.csv,
    working_cbp2023_metros.csv, market_labels.csv, working_excluded_events.csv
and a log to logs/build_working_<run_stamp>.log.

Run from the project root (defaults to run 2026-11-10_222442):
    .venv/bin/python scripts/build_working_dataset.py
    .venv/bin/python scripts/build_working_dataset.py <run_stamp>
"""
import sys

import pandas as pd

import config
from api_client import log, setup_logging

DEFAULT_RUN = "2026-11-10_222442"

# The 24 markets: Census metro area (CBSA) code -> short label chosen by the team.
MARKET_LABELS = {
    "12420": "Austin",               # Austin-Round Rock-San Marcos, TX
    "14460": "Boston",               # Boston-Cambridge-Newton, MA-NH
    "16740": "Charlotte",            # Charlotte-Concord-Gastonia, NC-SC
    "16980": "Chicago",              # Chicago-Naperville-Elgin, IL-IN
    "18140": "Columbus",             # Columbus, OH
    "19100": "Dallas-Fort Worth",    # Dallas-Fort Worth-Arlington, TX
    "19740": "Denver",               # Denver-Aurora-Centennial, CO
    "21340": "El Paso",              # El Paso, TX
    "26420": "Houston",              # Houston-Pasadena-The Woodlands, TX
    "26900": "Indianapolis",         # Indianapolis-Carmel-Greenwood, IN
    "27260": "Jacksonville",         # Jacksonville, FL
    "29820": "Las Vegas",            # Las Vegas-Henderson-North Las Vegas, NV
    "31080": "Los Angeles",          # Los Angeles-Long Beach-Anaheim, CA
    "34980": "Nashville",            # Nashville-Davidson--Murfreesboro--Franklin, TN
    "35620": "New York",             # New York-Newark-Jersey City, NY-NJ
    "36420": "Oklahoma City",        # Oklahoma City, OK
    "37980": "Philadelphia",         # Philadelphia-Camden-Wilmington, PA-NJ-DE-MD
    "38060": "Phoenix",              # Phoenix-Mesa-Chandler, AZ
    "41700": "San Antonio",          # San Antonio-New Braunfels, TX
    "41740": "San Diego",            # San Diego-Chula Vista-Carlsbad, CA
    "41860": "San Francisco-Oakland",  # San Francisco-Oakland-Fremont, CA
    "41940": "San Jose",             # San Jose-Sunnyvale-Santa Clara, CA
    "42660": "Seattle",              # Seattle-Tacoma-Bellevue, WA
    "47900": "Washington",           # Washington-Arlington-Alexandria, DC-VA-MD-WV
}

# Listings excluded as not standalone live events (decided 2026-11-11):
# event ID -> (event name, exclusion reason).
NON_EVENT_LISTINGS = {
    "G5dIZ_4lmq7Db": ("Brushstrokes & Ballads VIP Admission", "non_event_admission"),  # art-museum reception
    "1kAYvP70GA2yo-g": ("T-MOBILE GENERAL ADMISSION + F1 AFTERPARTY TICKET PACKAGE", "non_event_admission"),
    "rZ7HnEZ1AfuN70": ("Zumba® Master Class led by Zumba® Jammer Carlos Henriquez with live beats by DJ Dani Acosta",
                       "non_event_fitness_class"),
}

# Ticket packages: listing names containing "package(s)" or "hotel deals" (decided 2026-11-11).
# Each duplicates a regular listing of the same event at the same venue and date.
TICKET_PACKAGE_NAME = r"packages?\b|hotel deals"
EXPECTED_TICKET_PACKAGES = 85
# Package listings kept because no regular listing of the event exists.
KEEP_PACKAGE_LISTINGS = {
    "1kC8vPbgGACEYs1": "Gretchen Wilson | Official Rio Ticket + Hotel Packages",  # only listing of the 2026-11-13 concert
}

CBP_CODES = ["711310", "711320", "7112"]

EVENT_COLUMNS = ["event_id", "event_name", "event_url", "status", "local_date", "local_time",
                 "segment_id", "segment", "genre_id", "genre", "subgenre", "venue_id", "ticketing_platform"]
VENUE_COLUMNS = ["venue_id", "venue_name", "venue_address", "venue_city", "venue_state",
                 "venue_postal_code", "venue_latitude", "venue_longitude", "metro_area_geoid"]
ACS_COLUMNS = ["metro_area_geoid", "geo_name", "population", "population_moe", "population_note",
               "median_household_income", "median_household_income_moe", "median_household_income_note"]
CBP_COLUMNS = ["metro_area_geoid", "naics_code", "naics_label", "establishments", "employees",
               "employees_noise_flag", "published", "note"]


def read(name, run):
    """Read a processed CSV as text so IDs keep their leading zeros."""
    return pd.read_csv(config.PROCESSED_DIR / f"{name}_{run}.csv", dtype=str, keep_default_na=False, na_values=[""])


def build(run):
    events, venues = read("ticketmaster_events", run), read("venues_geocoded", run)
    acs1, cbp = read("census_acs1_2025", run), read("census_cbp2023", run)
    log.info("Input: %d events, %d venues, %d ACS 1-year rows, %d CBP rows", len(events), len(venues), len(acs1), len(cbp))

    # Each event belongs to its venue's metro area.
    metro_of = venues.set_index("venue_id")["metro_area_geoid"]
    events["metro_area_geoid"] = events["venue_id"].map(metro_of)

    outside = ~events["metro_area_geoid"].isin(MARKET_LABELS)
    non_event = events["event_id"].isin(NON_EVENT_LISTINGS) & ~outside
    package = (events["event_name"].str.contains(TICKET_PACKAGE_NAME, case=False, regex=True)
               & ~events["event_id"].isin(KEEP_PACKAGE_LISTINGS) & ~outside & ~non_event)
    reasons = {event_id: reason for event_id, (_, reason) in NON_EVENT_LISTINGS.items()}
    excluded = pd.concat([
        events[outside].assign(exclusion_reason="outside_24_metros"),
        events[non_event].assign(exclusion_reason=lambda d: d["event_id"].map(reasons)),
        events[package].assign(exclusion_reason="ticket_package_duplicate"),
    ])[["event_id", "event_name", "venue_id", "metro_area_geoid", "exclusion_reason"]]
    found = set(events.loc[non_event, "event_id"])
    if found != set(NON_EVENT_LISTINGS):
        raise ValueError(f"Expected non-event IDs not all found: missing {set(NON_EVENT_LISTINGS) - found}")
    if int(package.sum()) != EXPECTED_TICKET_PACKAGES:
        raise ValueError(f"Expected {EXPECTED_TICKET_PACKAGES} ticket packages, matched {int(package.sum())}")

    kept = events[~outside & ~non_event & ~package].copy()
    kept.loc[kept["segment"] != "Sports", "subgenre"] = None  # subgenre is kept for Sports only
    working_events = kept[EVENT_COLUMNS]

    working_venues = venues[venues["venue_id"].isin(working_events["venue_id"])][VENUE_COLUMNS]

    labels = pd.DataFrame({"metro_area_geoid": list(MARKET_LABELS), "market_label": list(MARKET_LABELS.values())})
    acs_metro = acs1[(acs1["geo_level"] == "metro_micro_area") & acs1["geoid"].isin(MARKET_LABELS)]
    acs_metro = acs_metro.rename(columns={"geoid": "metro_area_geoid"})[ACS_COLUMNS]
    labels = labels.merge(acs_metro[["metro_area_geoid", "geo_name"]], on="metro_area_geoid", how="left")
    labels = labels.rename(columns={"geo_name": "census_metro_name"})[["metro_area_geoid", "census_metro_name", "market_label"]]

    cbp_metro = cbp[(cbp["geo_level"] == "metro_micro_area") & cbp["geoid"].isin(MARKET_LABELS)
                    & cbp["naics_code"].isin(CBP_CODES)]
    cbp_metro = cbp_metro.rename(columns={"geoid": "metro_area_geoid"})[CBP_COLUMNS]

    return {
        "working_events.csv": working_events.sort_values(["local_date", "event_id"]),
        "working_venues.csv": working_venues.sort_values("venue_id"),
        "working_acs1_2025_metros.csv": acs_metro.sort_values("metro_area_geoid"),
        "working_cbp2023_metros.csv": cbp_metro.sort_values(["metro_area_geoid", "naics_code"]),
        "market_labels.csv": labels.sort_values("metro_area_geoid"),
        "working_excluded_events.csv": excluded.sort_values(["exclusion_reason", "event_id"]),
    }


def check(files):
    """Log reference, uniqueness and blank-value checks. Returns a list of problems."""
    problems = []
    ev, ve = files["working_events.csv"], files["working_venues.csv"]
    ml, acs, cbp = files["market_labels.csv"], files["working_acs1_2025_metros.csv"], files["working_cbp2023_metros.csv"]

    for name, df, key in [("events", ev, ["event_id"]), ("venues", ve, ["venue_id"]), ("market labels", ml, ["metro_area_geoid"]),
                          ("ACS", acs, ["metro_area_geoid"]), ("CBP", cbp, ["metro_area_geoid", "naics_code"])]:
        dupes = int(df.duplicated(key).sum())
        log.info("Duplicate %s on %s: %d", name, "+".join(key), dupes)
        if dupes:
            problems.append(f"{dupes} duplicate {name} on {key}")

    checks = [
        ("event venue_id found in venues", ev["venue_id"].isin(ve["venue_id"])),
        ("venue metro found in market labels", ve["metro_area_geoid"].isin(ml["metro_area_geoid"])),
        ("market label metro found in ACS", ml["metro_area_geoid"].isin(acs["metro_area_geoid"])),
        ("CBP metro found in market labels", cbp["metro_area_geoid"].isin(ml["metro_area_geoid"])),
    ]
    for label, ok in checks:
        log.info("%s: %d of %d", label, int(ok.sum()), len(ok))
        if not ok.all():
            problems.append(f"{label}: {int((~ok).sum())} not found")
    unused = set(ve["venue_id"]) - set(ev["venue_id"])
    log.info("Venues with no event: %d", len(unused))
    log.info("CBP rows per metro: %s", sorted(cbp.groupby("metro_area_geoid").size().unique().tolist()))

    for name, df in files.items():
        blanks = df.isna().sum()
        blanks = blanks[blanks > 0]
        log.info("Blank values in %s: %s", name, blanks.to_dict() or "none")
    return problems


def main(run):
    setup_logging(f"build_working_{run}")
    log.info("Building working dataset from run %s", run)
    files = build(run)
    out_dir = config.PROCESSED_DIR / f"working_{run}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in files.items():
        df.to_csv(out_dir / name, index=False)
        log.info("Wrote %s: %d rows, %d columns", name, len(df), len(df.columns))

    ev = files["working_events.csv"]
    log.info("Events by segment: %s", ev["segment"].value_counts(dropna=False).to_dict())
    log.info("Excluded by reason: %s", files["working_excluded_events.csv"]["exclusion_reason"].value_counts().to_dict())
    problems = check(files)
    log.info("Problems: %s", problems or "none")
    log.info("Output folder: %s", out_dir.relative_to(config.PROJECT_ROOT))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RUN)
