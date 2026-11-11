"""Exploratory probe (2026-11-02): does the Discovery API return Ticketmaster Resale (tmr) events?

Result: yes, but with no prices and no resale-specific fields. The music and
sports ones are the same events (same IDs) as our normal collection. Kept for
the record; not part of the pipeline.

Uses the same client and geohash as collect_ticketmaster.py, but
adds source=tmr. Two kinds of requests:
  1. Area search: each test city, the whole test window, all categories.
  2. Attraction search: a few performers whose upcomingEvents count tmr
     events in the 2026-11-02 sample, with no location filter, to see
     whether tmr events exist for them anywhere.

Writes data/raw/ticketmaster_tmr/ticketmaster_tmr_<run_stamp>.json.
Run from the project root:
    .venv/bin/python scripts/probes/probe_tmr.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Let this script import modules from the scripts/ folder.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import config
from api_client import PoliteClient, log, redact, setup_logging
from collect_ticketmaster import (
    TICKETMASTER_MIN_INTERVAL, TICKETMASTER_PAGE_SIZE, TICKETMASTER_URL, geohash,
)


def save_raw(source, run_stamp, collected_at, cities_payload):
    """Write the probe's untouched responses to data/raw/<source>/<source>_<run_stamp>.json."""
    out_dir = config.RAW_DIR / source
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{source}_{run_stamp}.json"
    path.write_text(json.dumps({
        "source": source,
        "collected_at": collected_at,
        "radius_miles": config.RADIUS_MILES,
        "event_window": [str(config.TEST_START_DATE), str(config.TEST_END_DATE)],
        "cities": cities_payload,
    }, indent=2))
    log.info("Saved raw %s responses to %s", source, path.relative_to(config.PROJECT_ROOT))
    return path

# Performers in our sample whose upcomingEvents list tmr events
# (name, Ticketmaster attraction id), looked up from the raw file at runtime.
PROBE_ATTRACTIONS = ["Foy Vance", "Don Omar", "Karina Rykman"]


def fetch_all(client, params, label):
    """Page through one search. Returns (request_records, events)."""
    records, events, page = [], [], 0
    while True:
        params = {**params, "size": TICKETMASTER_PAGE_SIZE, "page": page}
        status, body = client.get(TICKETMASTER_URL, params)
        records.append({
            "probe": label,
            "params": redact(params),
            "http_status": status,
            "requested_at": datetime.now().isoformat(timespec="seconds"),
            "response": body,
        })
        if status != 200 or body is None:
            break
        events += body.get("_embedded", {}).get("events", [])
        page += 1
        if page >= body.get("page", {}).get("totalPages", 0) or page * TICKETMASTER_PAGE_SIZE >= 1000:
            break
    log.info("tmr probe %s: %d events", label, len(events))
    return records, events


def attraction_ids_from_sample():
    """Find the attraction ids for PROBE_ATTRACTIONS in the newest raw Ticketmaster file."""
    import json
    raw = json.loads(sorted((config.RAW_DIR / "ticketmaster").glob("ticketmaster_*.json"))[-1].read_text())
    ids = {}
    for city in raw["cities"].values():
        for req in city["requests"]:
            for e in (req["response"] or {}).get("_embedded", {}).get("events", []):
                for a in e.get("_embedded", {}).get("attractions", []):
                    if a.get("name") in PROBE_ATTRACTIONS:
                        ids[a["name"]] = a["id"]
    return ids


def main():
    load_dotenv(config.PROJECT_ROOT / ".env")
    now = datetime.now()
    run_stamp = now.strftime("%Y-%m-%d_%H%M%S")
    setup_logging(f"tmr_probe_{run_stamp}")
    api_key = os.environ["TICKETMASTER_API_KEY"]
    client = PoliteClient("Ticketmaster", TICKETMASTER_MIN_INTERVAL)
    window = f"{config.TEST_START_DATE}T00:00:00,{config.TEST_END_DATE}T23:59:59"

    payload = {}
    for key, city in config.TEST_CITIES.items():
        records, _ = fetch_all(client, {
            "apikey": api_key,
            "source": "tmr",
            "geoPoint": geohash(city["lat"], city["lon"]),
            "radius": config.RADIUS_MILES,
            "unit": "miles",
            "localStartDateTime": window,
            "sort": "date,asc",
        }, f"area:{key}")
        payload[key] = {**city, "requests": records}

    records = []
    for name, attraction_id in attraction_ids_from_sample().items():
        recs, _ = fetch_all(client, {
            "apikey": api_key,
            "source": "tmr",
            "attractionId": attraction_id,
            "sort": "date,asc",
        }, f"attraction:{name}")
        records += recs
    payload["attraction_probes"] = {"name": "Attraction probes (no location filter)", "requests": records}

    save_raw("ticketmaster_tmr", run_stamp, now.isoformat(timespec="seconds"), payload)


if __name__ == "__main__":
    main()
