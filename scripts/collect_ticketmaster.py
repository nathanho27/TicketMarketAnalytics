"""Full Ticketmaster collection: Discovery API events for every city in config.CITIES.

For each city, each segment (Music, Sports) and each 7-day window of the
event period, it pages through all results and saves the responses,
unmodified, to one raw file per city:
    data/raw/ticketmaster/<run_stamp>/ticketmaster_<city>.json
    data/raw/ticketmaster/<run_stamp>/manifest.json   (counts and failures)
Nothing is parsed into rows here; that is convert_to_csv.py's job.

Completeness check: Ticketmaster reports totalElements for every search. The
manifest records it next to the number of events actually received, so an
incomplete search is visible. A window that reaches the 1,000-result cap is
split into smaller windows automatically.

Run from the project root (uses about 700 of the 5,000 daily requests):
    .venv/bin/python scripts/collect_ticketmaster.py
"""
import json
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

import config
from api_client import PoliteClient, log, redact, setup_logging

TICKETMASTER_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
# Ticketmaster allows 5 requests/second and 5,000/day, and will not return
# results past the 1,000th (page * size must stay under 1,000).
TICKETMASTER_PAGE_SIZE = 200
TICKETMASTER_MAX_RESULTS = 1000
TICKETMASTER_MIN_INTERVAL = 0.25


def geohash(lat, lon, precision=9):
    """Encode a latitude/longitude as a geohash (Ticketmaster's geoPoint)."""
    alphabet = "0123456789bcdefghjkmnpqrstuvwxyz"
    lat_range, lon_range = [-90.0, 90.0], [-180.0, 180.0]
    bits, use_lon = [], True
    while len(bits) < precision * 5:
        rng, value = (lon_range, lon) if use_lon else (lat_range, lat)
        mid = (rng[0] + rng[1]) / 2
        if value >= mid:
            bits.append(1)
            rng[0] = mid
        else:
            bits.append(0)
            rng[1] = mid
        use_lon = not use_lon
    return "".join(
        alphabet[int("".join(map(str, bits[i:i + 5])), 2)]
        for i in range(0, len(bits), 5)
    )


def search_window(client, api_key, city, segment_name, segment_id, start, end):
    """Every page of one search. Splits the window in half if it hits the result cap.

    Returns (request_records, window_summaries).
    """
    records, page, received, total = [], 0, 0, None
    while True:
        params = {
            "apikey": api_key,
            "geoPoint": geohash(city["lat"], city["lon"]),
            "radius": config.RADIUS_MILES,
            "unit": "miles",
            "countryCode": config.COUNTRY_CODE,
            "segmentId": segment_id,
            "localStartDateTime": f"{start}T00:00:00,{end}T23:59:59",
            "sort": "date,asc",
            "size": TICKETMASTER_PAGE_SIZE,
            "page": page,
        }
        status, body = client.get(TICKETMASTER_URL, params, quiet=True)
        records.append({
            "segment": segment_name,
            "window": [str(start), str(end)],
            "params": redact(params),
            "http_status": status,
            "requested_at": datetime.now().isoformat(timespec="seconds"),
            "response": body,
        })
        if status != 200 or body is None:
            break

        page_info = body.get("page", {})
        total = page_info.get("totalElements", 0)
        if total >= TICKETMASTER_MAX_RESULTS and start < end:
            # Too many results to page through: split and search each half instead.
            mid = start + (end - start) // 2
            log.info("%s %s %s..%s has %d results; splitting window", city["name"],
                     segment_name, start, end, total)
            left_recs, left_sum = search_window(client, api_key, city, segment_name, segment_id, start, mid)
            right_recs, right_sum = search_window(client, api_key, city, segment_name, segment_id,
                                                  mid + timedelta(days=1), end)
            return records + left_recs + right_recs, left_sum + right_sum

        received += len(body.get("_embedded", {}).get("events", []))
        page += 1
        if page >= page_info.get("totalPages", 0) or page * TICKETMASTER_PAGE_SIZE >= TICKETMASTER_MAX_RESULTS:
            break

    summary = {"segment": segment_name, "window": [str(start), str(end)], "total_elements": total,
               "events_received": received,
               "complete": status == 200 and total is not None and received >= total,
               "failed_requests": sum(r["http_status"] != 200 for r in records)}
    if not summary["complete"]:
        log.warning("INCOMPLETE %s %s %s..%s: received %d of %s (HTTP %s)", city["name"],
                    segment_name, start, end, received, total, status)
    return records, [summary]


def collect_city(client, api_key, city):
    records, summaries = [], []
    for segment_name, segment_id in config.TICKETMASTER_SEGMENTS.items():
        for start, end in config.date_windows(config.EVENT_START_DATE, config.EVENT_END_DATE):
            recs, sums = search_window(client, api_key, city, segment_name, segment_id, start, end)
            records += recs
            summaries += sums
    received = sum(s["events_received"] for s in summaries)
    log.info("%s: %d requests, %d events received, %d incomplete windows, daily quota left: %s",
             city["name"], len(records), received, sum(not s["complete"] for s in summaries),
             client.last_headers.get("Rate-Limit-Available"))
    return records, summaries


def main():
    load_dotenv(config.PROJECT_ROOT / ".env")
    api_key = os.environ["TICKETMASTER_API_KEY"].strip()
    run_stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    setup_logging(f"collect_ticketmaster_{run_stamp}")
    out_dir = config.RAW_DIR / "ticketmaster" / run_stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    log.info("Ticketmaster collection %s: %d cities, events %s to %s, radius %d mi, country %s",
             run_stamp, len(config.CITIES), config.EVENT_START_DATE, config.EVENT_END_DATE,
             config.RADIUS_MILES, config.COUNTRY_CODE)

    client = PoliteClient("Ticketmaster", TICKETMASTER_MIN_INTERVAL, timeout=30)
    manifest = {"run_stamp": run_stamp, "started_at": datetime.now().isoformat(timespec="seconds"),
                "event_window": [str(config.EVENT_START_DATE), str(config.EVENT_END_DATE)],
                "radius_miles": config.RADIUS_MILES, "country_code": config.COUNTRY_CODE,
                "segments": config.TICKETMASTER_SEGMENTS, "cities": {}}

    for key, city in config.CITIES.items():
        collected_at = datetime.now().isoformat(timespec="seconds")
        records, summaries = collect_city(client, api_key, city)
        payload = {
            "source": "ticketmaster",
            "run_stamp": run_stamp,
            "collected_at": collected_at,
            "radius_miles": config.RADIUS_MILES,
            "event_window": manifest["event_window"],
            "cities": {key: {**city, "collected_at": collected_at, "requests": records}},
        }
        (out_dir / f"ticketmaster_{key}.json").write_text(json.dumps(payload))
        manifest["cities"][key] = {
            "requests": len(records),
            "events_received": sum(s["events_received"] for s in summaries),
            "incomplete_windows": [s for s in summaries if not s["complete"]],
            "windows": summaries,
        }

    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    manifest["total_requests"] = sum(c["requests"] for c in manifest["cities"].values())
    manifest["total_events_received"] = sum(c["events_received"] for c in manifest["cities"].values())
    manifest["incomplete_window_count"] = sum(len(c["incomplete_windows"]) for c in manifest["cities"].values())
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    log.info("Done: %d requests, %d events received (before de-duplication), %d incomplete windows",
             manifest["total_requests"], manifest["total_events_received"], manifest["incomplete_window_count"])
    log.info("Raw files in %s", out_dir.relative_to(config.PROJECT_ROOT))


if __name__ == "__main__":
    main()
