"""Exploratory probe: can Ticketmaster performers be matched to Last.fm artists?

Takes a small sample of performers from the newest raw Ticketmaster file and
calls Last.fm artist.getInfo once per performer:
  - by MusicBrainz ID when Ticketmaster lists one (exact identifier match),
  - otherwise by name with autocorrect on (needs checking).

Each result gets a match_method and review flags. Matching names are never
assumed to be the same artist: name-only matches are labelled as such.

Needs LASTFM_API_KEY in .env (free: https://www.last.fm/api/account/create).
Not part of the pipeline. Writes:
    data/raw/lastfm/lastfm_probe_<run_stamp>.json   untouched responses
    data/processed/lastfm_probe_<run_stamp>.csv     one row per performer
Run from the project root:
    .venv/bin/python scripts/probes/probe_lastfm.py
"""
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

LASTFM_URL = "https://ws.audioscrobbler.com/2.0/"
# Last.fm asks for an identifiable User-Agent and warns against several calls per second.
USER_AGENT = "TicketMarketAnalytics-class-project/0.1 (github.com/nathanho27/TicketMarketAnalytics)"
MIN_INTERVAL = 1.0
SAMPLE_WITH_MBID = 30
SAMPLE_WITHOUT_MBID = 30
LOW_LISTENERS = 1000


def normalize(name):
    """Lowercase, '&' -> 'and', drop punctuation and a leading 'the'."""
    name = (name or "").lower().replace("&", "and")
    name = re.sub(r"[^a-z0-9 ]", "", name).strip()
    return re.sub(r"^the ", "", name)


def sample_performers():
    """Unique performers on kept Music events, split by whether they have a MusicBrainz ID."""
    raw = json.loads(sorted((config.RAW_DIR / "ticketmaster").glob("ticketmaster_*.json"))[-1].read_text())
    kept = set(pd.read_csv(sorted(config.PROCESSED_DIR.glob("ticketmaster_events_*.csv"))[-1])["event_id"])
    performers = {}
    for city_key, city in raw["cities"].items():
        for req in city["requests"]:
            for e in (req["response"] or {}).get("_embedded", {}).get("events", []):
                if e["id"] not in kept or e["classifications"][0]["segment"]["name"] != "Music":
                    continue
                for a in e.get("_embedded", {}).get("attractions", []):
                    if a.get("name"):
                        links = a.get("externalLinks", {})
                        performers.setdefault(a["id"], {
                            "tm_attraction_id": a["id"],
                            "tm_name": a["name"],
                            "tm_mbid": (links.get("musicbrainz") or [{}])[0].get("id"),
                            "tm_lastfm_url": (links.get("lastfm") or [{}])[0].get("url"),
                            "tm_genre": (a.get("classifications") or [{}])[0].get("genre", {}).get("name"),
                            "city": city_key,
                        })
    rng = random.Random(42)
    with_mbid = [p for p in performers.values() if p["tm_mbid"]]
    without = [p for p in performers.values() if not p["tm_mbid"]]
    return (rng.sample(with_mbid, min(SAMPLE_WITH_MBID, len(with_mbid)))
            + rng.sample(without, min(SAMPLE_WITHOUT_MBID, len(without))))


def get_info(session, api_key, performer):
    params = {"method": "artist.getinfo", "api_key": api_key, "format": "json"}
    if performer["tm_mbid"]:
        params["mbid"] = performer["tm_mbid"]
    else:
        params.update({"artist": performer["tm_name"], "autocorrect": 1})
    resp = session.get(LASTFM_URL, params=params, timeout=30)
    try:
        body = resp.json()
    except ValueError:
        body = {"non_json_body": resp.text[:500]}
    safe = {k: v for k, v in params.items() if k != "api_key"}
    return resp.status_code, safe, body


def assess(p, status, body):
    """Turn one response into a result row with match method and review flags."""
    artist = body.get("artist") if isinstance(body, dict) else None
    row = {**p, "http_status": status, "lastfm_error": body.get("error") if isinstance(body, dict) else None}
    if not artist:
        return {**row, "match_method": "unmatched", "review_flags": "not_found"}

    tags = [t["name"] for t in (artist.get("tags") or {}).get("tag", [])]
    listeners = int(artist.get("stats", {}).get("listeners") or 0)
    row.update({
        "lastfm_name": artist.get("name"),
        "lastfm_mbid": artist.get("mbid") or None,
        "lastfm_url": artist.get("url"),
        "lastfm_listeners": listeners,
        "lastfm_playcount": int(artist.get("stats", {}).get("playcount") or 0),
        "lastfm_tags": " | ".join(tags),
    })
    flags = []
    same_name = normalize(artist.get("name")) == normalize(p["tm_name"])
    if p["tm_mbid"]:
        method = "mbid"
        if not same_name:
            flags.append("name_differs_from_ticketmaster")
    else:
        method = "name_exact" if same_name else "name_autocorrected"
        if not artist.get("mbid"):
            flags.append("no_mbid_on_lastfm")  # Last.fm may merge different artists sharing a name
    if len(normalize(p["tm_name"])) <= 3:
        flags.append("very_short_name")
    if listeners < LOW_LISTENERS:
        flags.append(f"under_{LOW_LISTENERS}_listeners")
    if p["tm_lastfm_url"] and p["tm_lastfm_url"].rstrip("/").lower().replace("%20", "+") \
            != (artist.get("url") or "").rstrip("/").lower():
        flags.append("lastfm_url_differs_from_ticketmaster_link")
    return {**row, "match_method": method, "review_flags": " | ".join(flags) or None}


def main():
    load_dotenv(config.PROJECT_ROOT / ".env")
    api_key = os.getenv("LASTFM_API_KEY")
    if not api_key:
        sys.exit("LASTFM_API_KEY is not set in .env")

    performers = sample_performers()
    run_stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    records, rows = [], []
    for i, p in enumerate(performers, 1):
        time.sleep(MIN_INTERVAL)
        status, params, body = get_info(session, api_key, p)
        records.append({"performer": p, "params": params, "http_status": status,
                        "requested_at": datetime.now().isoformat(timespec="seconds"), "response": body})
        rows.append(assess(p, status, body))
        print(f"{i:3d}/{len(performers)} HTTP {status} {p['tm_name']!r} -> {rows[-1]['match_method']}")

    raw_dir = config.RAW_DIR / "lastfm"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"lastfm_probe_{run_stamp}.json").write_text(json.dumps(records, indent=2))
    out = config.PROCESSED_DIR / f"lastfm_probe_{run_stamp}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Saved {len(rows)} rows to {out.relative_to(config.PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
