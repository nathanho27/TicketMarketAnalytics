"""Convert saved raw Ticketmaster responses into flat CSV files.

Reads a raw run written by collect_ticketmaster.py (a folder with one file
per city) or the single pilot file, and writes one row per Ticketmaster
event ID:
    data/processed/ticketmaster_events_<run_stamp>.csv     kept events
    data/processed/ticketmaster_excluded_<run_stamp>.csv   removed rows + reason
    logs/convert_<run_stamp>.log                           counts and quality flags

Every column comes from a field confirmed in the 2026-11-02 test responses.
Missing values stay empty; nothing is filled in or estimated.

Prices: Ticketmaster's priceRanges are stored as "listed price ranges". They
are NOT verified face value. Ticketmaster does not document whether fees are
included (see docs/ticketmaster_pricing_investigation.md).

Lists (several performers, genres, promoters...) are joined into one cell
with " | ". Performer columns line up: the 2nd name goes with the 2nd ID,
the 2nd genre, and so on (blank where a performer has no value).

The event date window comes from the raw data itself, so the pilot file and
the full run each convert with their own window.

Run from the project root (defaults to the newest raw Ticketmaster run folder):
    .venv/bin/python scripts/convert_to_csv.py
    .venv/bin/python scripts/convert_to_csv.py data/raw/ticketmaster/<run_stamp>
    .venv/bin/python scripts/convert_to_csv.py data/raw/ticketmaster/<pilot file>.json
"""
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

import config

log = logging.getLogger("convert")

# Ticketmaster classification sub-types that are not concerts or games.
# In the 2026-11-10 data "Museum" and "Tour" are only used for museum and
# arena tours (e.g. "The Sports Museum Tour", "TD Garden Arena Tour").
NON_EVENT_SUBTYPES = {"Sightseeing/Facility", "Museum", "Tour"}

# Event names that are clearly not a ticket to a concert or game:
# (exclusion reason, pattern, segments it applies to or None for all).
NON_EVENT_NAMES = [
    ("addon_or_multiday_pass", re.compile(
        r"\bparking\b|not a (concert|game) ticket|no ticket included|vip upgrade"
        r"|\badd[- ]?on\b|\bupgrade\b|\bvoucher\b|\b\d+[- ]day pass\b", re.IGNORECASE), None),
    # Facility tours. Not applied to Music: concert tours are often called "... Arena Tour".
    ("facility_tour", re.compile(
        r"\b(stadium|arena|ballpark|museum|facility|backstage|behind[- ]the[- ]scenes|guided)\s+tours?\b",
        re.IGNORECASE), {"Sports", "Miscellaneous", "Undefined", None}),
    ("skating_session", re.compile(r"\bskat(e|ing)\b", re.IGNORECASE), None),
]

# Borderline: admission to an attraction (e.g. "Belmont Park - General Admission").
# Kept, but flagged "review_attraction_admission" for a human decision.
REVIEW_NAME = re.compile(r"\badmission\b", re.IGNORECASE)

# Ticketmaster uses this date when an on-sale date is unknown.
PLACEHOLDER_DATE_PREFIX = "1900-01-01"

SEP = " | "


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def dig(obj, *path):
    """Safely read a nested value: dig(e, "dates", "start", "localDate"). None if missing."""
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list) and isinstance(key, int) and len(obj) > key:
            obj = obj[key]
        else:
            return None
    return obj


def join(values):
    """Join values into one cell, skipping blanks and repeats. Use for sets of labels."""
    out = []
    for v in values:
        if v not in (None, "") and v not in out:
            out.append(v)
    return SEP.join(str(v) for v in out) or None


def join_aligned(values):
    """Join values one-per-item, keeping blanks so positions line up across columns."""
    values = list(values)
    if not values or all(v in (None, "") for v in values):
        return None
    return SEP.join("" if v is None else str(v) for v in values)


def ticketing_platform(url):
    """'www.ticketweb.com/...' -> 'ticketweb.com'. Shows which Ticketmaster platform sells it."""
    host = urlparse(url or "").netloc
    return host.removeprefix("www.") or None


# ---------------------------------------------------------------------------
# Column groups: each function returns a dict of columns for one event
# ---------------------------------------------------------------------------

def event_fields(event):
    dates = event.get("dates") or {}
    return {
        "event_id": event.get("id"),
        "event_name": (event.get("name") or "").strip(),
        "event_url": event.get("url"),
        "status": dig(dates, "status", "code"),
        "local_date": dig(dates, "start", "localDate"),
        "local_time": dig(dates, "start", "localTime"),
        "start_datetime_utc": dig(dates, "start", "dateTime"),
        "event_timezone": dates.get("timezone"),
        "date_tba": dig(dates, "start", "dateTBA"),
        "time_tba": dig(dates, "start", "timeTBA"),
        "no_specific_time": dig(dates, "start", "noSpecificTime"),
        "span_multiple_days": dates.get("spanMultipleDays"),
        "end_local_date": dig(dates, "end", "localDate"),
        "end_local_time": dig(dates, "end", "localTime"),
        "doors_local_time": dig(event, "doorsTimes", "localTime"),
        "initial_start_local_date": dig(dates, "initialStartDate", "localDate"),
    }


def classification_fields(event):
    """Primary classification in its own columns, plus every classification joined."""
    classes = event.get("classifications") or []
    primary = next((c for c in classes if c.get("primary")), classes[0] if classes else {})
    return {
        "segment": dig(primary, "segment", "name"),
        "segment_id": dig(primary, "segment", "id"),
        "genre": dig(primary, "genre", "name"),
        "genre_id": dig(primary, "genre", "id"),
        "subgenre": dig(primary, "subGenre", "name"),
        "subgenre_id": dig(primary, "subGenre", "id"),
        "class_type": dig(primary, "type", "name"),
        "class_subtype": dig(primary, "subType", "name"),
        "family_event": primary.get("family"),
        "classification_count": len(classes),
        "all_segments": join(dig(c, "segment", "name") for c in classes),
        "all_genres": join(dig(c, "genre", "name") for c in classes),
        "all_subgenres": join(dig(c, "subGenre", "name") for c in classes),
    }


def venue_fields(event):
    venue = dig(event, "_embedded", "venues", 0) or {}
    return {
        "venue_id": venue.get("id"),
        "venue_name": venue.get("name"),
        "venue_url": venue.get("url"),
        "venue_address": dig(venue, "address", "line1"),
        "venue_city": dig(venue, "city", "name"),
        "venue_state": dig(venue, "state", "stateCode"),
        "venue_postal_code": venue.get("postalCode"),
        "venue_country": dig(venue, "country", "countryCode"),
        "venue_latitude": dig(venue, "location", "latitude"),
        "venue_longitude": dig(venue, "location", "longitude"),
        "venue_timezone": venue.get("timezone"),
        "tm_market_ids": join(m.get("id") for m in venue.get("markets") or []),
        "tm_market_names": join(m.get("name") for m in venue.get("markets") or []),
        "dma_ids": join(d.get("id") for d in venue.get("dmas") or []),
        "venue_upcoming_events": dig(venue, "upcomingEvents", "_total"),
    }


def attraction_fields(event):
    """Every performer (Ticketmaster 'attraction'), in the order Ticketmaster lists them."""
    atts = dig(event, "_embedded", "attractions") or []

    def first_link(a, kind, key):
        return dig(a, "externalLinks", kind, 0, key)

    def primary_class(a, level):
        classes = a.get("classifications") or []
        c = next((c for c in classes if c.get("primary")), classes[0] if classes else {})
        return dig(c, level, "name")

    return {
        "attraction_count": len(atts),
        "attraction_ids": join_aligned(a.get("id") for a in atts),
        "attraction_names": join_aligned(a.get("name") for a in atts),
        "attraction_segments": join_aligned(primary_class(a, "segment") for a in atts),
        "attraction_genres": join_aligned(primary_class(a, "genre") for a in atts),
        "attraction_upcoming_events": join_aligned(dig(a, "upcomingEvents", "_total") for a in atts),
        "attraction_musicbrainz_ids": join_aligned(first_link(a, "musicbrainz", "id") for a in atts),
        "attraction_wiki_urls": join_aligned(first_link(a, "wiki", "url") for a in atts),
        "attraction_spotify_urls": join_aligned(first_link(a, "spotify", "url") for a in atts),
    }


def promoter_fields(event):
    promoters = event.get("promoters") or []
    return {
        "promoter_id": dig(event, "promoter", "id"),
        "promoter_name": dig(event, "promoter", "name"),
        "promoter_count": len(promoters),
        "all_promoter_ids": join_aligned(p.get("id") for p in promoters),
        "all_promoter_names": join_aligned(p.get("name") for p in promoters),
    }


def price_fields(event):
    """Ticketmaster listed price range (not verified face value).

    reported_price_*  exactly what Ticketmaster returned, including $0-$0.
    listed_price_*    the values to use for analysis; blank when there is no
                      range or the range is $0-$0 (a paid show reported as $0
                      is not a real price, so it is never treated as free).
    """
    ranges = event.get("priceRanges") or []
    if not ranges:
        return {"price_range_count": 0,
                "reported_price_min": None, "reported_price_max": None,
                "listed_price_min": None, "listed_price_max": None,
                "listed_price_currency": None, "listed_price_type": None,
                "has_listed_price": False, "price_issue": "no_price_range"}

    # Prefer the "standard" range when there is more than one.
    chosen = next((r for r in ranges if r.get("type") == "standard"), ranges[0])
    usable = (chosen.get("max") or 0) > 0
    return {
        "price_range_count": len(ranges),
        "reported_price_min": chosen.get("min"),
        "reported_price_max": chosen.get("max"),
        "listed_price_min": chosen.get("min") if usable else None,
        "listed_price_max": chosen.get("max") if usable else None,
        "listed_price_currency": chosen.get("currency"),
        "listed_price_type": chosen.get("type"),
        "has_listed_price": usable,
        "price_issue": None if usable else "zero_price_range",
    }


def sales_fields(event):
    reported_start = dig(event, "sales", "public", "startDateTime")
    presales = dig(event, "sales", "presales") or []
    presale_starts = sorted(p["startDateTime"] for p in presales if p.get("startDateTime"))
    return {
        "public_sale_start_reported": reported_start,
        "public_sale_start": None if (reported_start or "").startswith(PLACEHOLDER_DATE_PREFIX) else reported_start,
        "public_sale_end": dig(event, "sales", "public", "endDateTime"),
        "presale_count": len(presales),
        "presale_names": join(p.get("name") for p in presales),
        "first_presale_start": presale_starts[0] if presale_starts else None,
    }


def ticketing_fields(event):
    products = event.get("products") or []
    return {
        "ticketing_platform": ticketing_platform(event.get("url")),
        "all_inclusive_pricing": dig(event, "ticketing", "allInclusivePricing", "enabled"),
        "safe_tix_enabled": dig(event, "ticketing", "safeTix", "enabled"),
        "has_seatmap": bool(dig(event, "seatmap", "staticUrl")),
        "age_restriction_enforced": dig(event, "ageRestrictions", "legalAgeEnforced"),
        "ticket_limit_info": dig(event, "ticketLimit", "info"),
        "addon_product_count": len(products),
        "addon_product_types": join(sorted({p.get("type") for p in products if p.get("type")})),
        "addon_product_names": join(p.get("name") for p in products),
    }


def ticketmaster_row(event, collected_at):
    """Flatten one Ticketmaster event into a dict of CSV columns."""
    return {
        "source": "ticketmaster",
        "collected_at": collected_at,
        **event_fields(event),
        **classification_fields(event),
        **venue_fields(event),
        **attraction_fields(event),
        **promoter_fields(event),
        **price_fields(event),
        **sales_fields(event),
        **ticketing_fields(event),
    }


# ---------------------------------------------------------------------------
# Reading the raw file, merging duplicates, flags and exclusions
# ---------------------------------------------------------------------------

def collect_rows(raw):
    """One row per event ID, with every city/segment search that returned it.

    An event can be returned by more than one city search when search circles
    overlap. Instead of dropping the repeat, its cities are listed in
    search_cities (closest city first) and the row is flagged.
    """
    rows, hits = {}, {}
    for city_key, city in raw["cities"].items():
        collected_at = city.get("collected_at", raw["collected_at"])
        for request in city["requests"]:
            body = request.get("response") or {}
            for event in body.get("_embedded", {}).get("events", []):
                hits.setdefault(event["id"], []).append(
                    (event.get("distance"), city_key, request["segment"]))
                rows.setdefault(event["id"], ticketmaster_row(event, collected_at))

    for event_id, row in rows.items():
        found_by = sorted(hits[event_id], key=lambda h: (h[0] is None, h[0]))
        row["primary_search_city"] = found_by[0][1]
        row["distance_miles"] = found_by[0][0]
        row["search_cities"] = join(city for _, city, _ in found_by)
        row["search_segments"] = join(seg for _, _, seg in found_by)
        row["search_city_count"] = len({city for _, city, _ in found_by})
        row["search_hit_count"] = len(found_by)
    return list(rows.values())


def quality_flags(row):
    """Short labels for missing or suspicious information, joined with ' | '."""
    flags = []
    if row["price_issue"] == "zero_price_range":
        flags.append("zero_price_range")
    if (row["public_sale_start_reported"] or "").startswith(PLACEHOLDER_DATE_PREFIX):
        flags.append("placeholder_onsale_date")
    if row["attraction_count"] == 0:
        flags.append("no_performer")
    if not row["promoter_id"]:
        flags.append("no_promoter")
    if not row["event_timezone"]:
        flags.append("no_event_timezone")
    if not row["start_datetime_utc"]:
        flags.append("no_start_time")
    if not row["venue_address"]:
        flags.append("no_venue_address")
    expected_states = {s for c in row["search_cities"].split(SEP)
                       for s in config.CITIES.get(c, {}).get("states", [])}
    if expected_states and row["venue_state"] not in expected_states:
        flags.append("venue_state_outside_search_area")
    if row["venue_country"] and row["venue_country"] != "US":
        flags.append("non_us_venue")
    if REVIEW_NAME.search(row["event_name"]):
        flags.append("review_attraction_admission")
    if row["search_city_count"] > 1:
        flags.append("multiple_search_cities")
    if row["search_hit_count"] > row["search_city_count"]:
        flags.append("repeated_in_searches")
    return SEP.join(flags) or None


def exclusion_reason(row, event_window):
    """Why a row is not a real event listing, or None to keep it."""
    if row["class_subtype"] in NON_EVENT_SUBTYPES:
        return f"non_event_subtype:{row['class_subtype']}"
    for reason, pattern, segments in NON_EVENT_NAMES:
        if (segments is None or row["segment"] in segments) and pattern.search(row["event_name"]):
            return f"non_event_name:{reason}"
    start, end = event_window
    if not (start <= (row["local_date"] or "") <= end):
        return "outside_date_window"
    return None


def setup_logging(run_stamp):
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = config.LOG_DIR / f"convert_{run_stamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )


def load_raw(raw_path):
    """Read a run folder (one file per city) or a single raw file.

    Returns (raw, run_stamp) where raw has the same shape for both:
    {"collected_at", "event_window", "cities": {city_key: {..., "requests": [...]}}}.
    """
    if raw_path.is_dir():
        files = sorted(raw_path.glob("ticketmaster_*.json"))
        if not files:
            sys.exit(f"No ticketmaster_*.json files in {raw_path}")
        parts = [json.loads(f.read_text()) for f in files]
        raw = {"collected_at": min(p["collected_at"] for p in parts),
               "event_window": parts[0]["event_window"],
               "cities": {k: v for p in parts for k, v in p["cities"].items()}}
        return raw, raw_path.name
    return json.loads(raw_path.read_text()), raw_path.stem.removeprefix("ticketmaster_")


def convert_ticketmaster(raw_path):
    raw_path = Path(raw_path)
    raw, run_stamp = load_raw(raw_path)
    setup_logging(run_stamp)

    rows = collect_rows(raw)
    for row in rows:
        row["quality_flags"] = quality_flags(row)
        row["exclusion_reason"] = exclusion_reason(row, raw["event_window"])
    df = pd.DataFrame(rows)

    # Search columns go right after the collection timestamp for readability.
    search_cols = ["primary_search_city", "search_cities", "search_segments",
                   "search_city_count", "search_hit_count", "distance_miles"]
    cols = ["source", "collected_at"] + search_cols + [c for c in df.columns
                                                       if c not in search_cols + ["source", "collected_at"]]
    df = df[cols]

    if not df["event_id"].is_unique:
        raise ValueError("event_id is not unique after merging; check collect_rows()")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    kept = df[df["exclusion_reason"].isna()].drop(columns="exclusion_reason")
    excluded = df[df["exclusion_reason"].notna()]
    kept_path = config.PROCESSED_DIR / f"ticketmaster_events_{run_stamp}.csv"
    excluded_path = config.PROCESSED_DIR / f"ticketmaster_excluded_{run_stamp}.csv"
    kept.to_csv(kept_path, index=False)
    excluded.to_csv(excluded_path, index=False)

    log.info("Read %s (%d search areas): %d unique event IDs", raw_path.name, len(raw["cities"]), len(df))
    log.info("Events found by more than one search area: %d", int((df["search_city_count"] > 1).sum()))
    log.info("Kept %d -> %s", len(kept), kept_path.relative_to(config.PROJECT_ROOT))
    log.info("Excluded %d -> %s", len(excluded), excluded_path.relative_to(config.PROJECT_ROOT))
    for reason, n in excluded["exclusion_reason"].value_counts().items():
        log.info("  excluded %3d %s", n, reason)

    flag_counts = Counter(f for flags in kept["quality_flags"].dropna() for f in flags.split(SEP))
    log.info("Quality flags on kept events:")
    for flag, n in flag_counts.most_common():
        log.info("  %3d %s", n, flag)
    return kept_path


def latest_raw(source):
    """Newest run folder in data/raw/<source>/, or the newest single file if there is none."""
    folder = config.RAW_DIR / source
    runs = sorted(p for p in folder.iterdir() if p.is_dir()) if folder.exists() else []
    if runs:
        return runs[-1]
    files = sorted(folder.glob(f"{source}_*.json"))
    if not files:
        sys.exit(f"No raw {source} data in {folder}")
    return files[-1]


if __name__ == "__main__":
    convert_ticketmaster(sys.argv[1] if len(sys.argv) > 1 else latest_raw("ticketmaster"))
