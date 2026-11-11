# Phase 1 Guide: Ticketmaster Test Collection

> **Historical (LA/NYC pilot, Nov 2026).** The final 25-city collection is
> documented in [data_sources.md](data_sources.md). Since the pilot:
> - `collect_test.py` became `collect_ticketmaster.py`;
> - `evaluate_test.py` became `evaluate_collection.py`;
> - the request client moved to `api_client.py`.
>
> The converter and its columns described below are unchanged. The pilot
> still converts with
> `convert_to_csv.py data/raw/ticketmaster/ticketmaster_2026-11-02_203943.json`.

**Project direction (revised 2026-11-02):** compare live-event markets across
the 10 largest U.S. cities using event availability, Ticketmaster listed
prices, venues, genres and promoters. Categories: Music and Sports (Arts &
Theatre may be added later).

Resale pricing was dropped. SeatGeek's public API has no prices, the
Ticketmaster Resale (`tmr`) source returns no prices, and the other resale
sources are paid or partner-only. See
[ticketmaster_pricing_investigation.md](ticketmaster_pricing_investigation.md)
and [resale_source_options.md](resale_source_options.md).

The current test covers Los Angeles and New York City, November 6–10, 2026.

## Setup (once per computer)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env      # then paste your own Ticketmaster key into .env
```

`.env` is in `.gitignore`, so keys never reach GitHub. Each partner keeps their own.

## Running it

Run from the project folder, in this order:

```bash
.venv/bin/python scripts/collect_test.py     # call the API, save raw JSON (uses API quota)
.venv/bin/python scripts/convert_to_csv.py   # raw JSON -> CSV (no API calls)
.venv/bin/python scripts/evaluate_test.py    # print data-quality summary (no API calls)
```

Collection and conversion are separate on purpose. If the converter changes,
re-run it on the saved raw files without calling the API again.

## Folder layout

```
scripts/
  config.py           cities (center, radius, expected states), dates, paths
  collect_test.py     API requests -> data/raw/
  convert_to_csv.py   data/raw/ -> data/processed/
  evaluate_test.py    summary of a processed CSV
  probes/
    probe_tmr.py      one-off Ticketmaster Resale test (not part of the pipeline)
data/raw/ticketmaster/        ticketmaster_<YYYY-MM-DD_HHMMSS>.json  (untouched API responses)
data/raw/ticketmaster_tmr/    resale probe responses
data/processed/               ticketmaster_events_<stamp>.csv, ticketmaster_excluded_<stamp>.csv
logs/                         collect_<stamp>.log, convert_<stamp>.log
```

`data/` and `logs/` are git-ignored.

## How the scripts work

### `config.py`

Shared settings:
- `TEST_CITIES`: each city's center lat/lon and its expected venue `states`
  (used for a quality flag).
- `RADIUS_MILES = 25`.
- The event window `TEST_START_DATE`–`TEST_END_DATE`.
- Ticketmaster segment IDs for Music and Sports.
- `test_dates()` returns each day in the window.

### `collect_test.py`: calling the API

- **`PoliteClient.get(url, params)`** sends every request. It:
  - spaces calls 0.25 s apart, under Ticketmaster's 5/second limit;
  - retries HTTP 429 and 5xx responses up to 3 times;
  - logs every request with the key replaced by `<redacted>`;
  - returns `(status, json)` instead of crashing.
- **`geohash(lat, lon)`** turns a coordinate into the format Ticketmaster's
  `geoPoint` parameter needs.
- **`collect_ticketmaster(...)`** searches each segment × each local day with
  `geoPoint` + `radius` + `localStartDateTime`, paging with `page`/`size=200`.
  One day at a time keeps each search under Ticketmaster's 1,000-result cap.
- **`save_raw(...)`** writes one JSON file per run. Each request is stored
  with its parameters (key redacted), HTTP status, time and the **complete,
  unmodified response**.

### `convert_to_csv.py`: raw JSON to one row per event

The steps, in order:

1. **`collect_rows(raw)`** reads every event from every request and builds
   **one row per Ticketmaster event ID**. If several searches returned the
   same event (for example two cities whose circles overlap), it is not
   dropped:
   - `search_cities` lists every city that found it, closest first;
   - `primary_search_city` / `distance_miles` are the closest city;
   - the row is flagged `multiple_search_cities`.
2. **`ticketmaster_row(event)`** builds the columns from small, single-purpose
   functions:
   - `event_fields`: ID, name, status, dates and times.
   - `classification_fields`: the primary classification, plus **all** of
     them joined.
   - `venue_fields`: venue, location, Ticketmaster market, DMA.
   - `attraction_fields`: **all** performers, with genres and outside IDs.
   - `promoter_fields`: primary promoter plus all promoter IDs and names.
   - `price_fields`: listed price range (see below).
   - `sales_fields`: on-sale dates and presales.
   - `ticketing_fields`: platform, all-in pricing, add-ons.
3. **`quality_flags(row)`** adds short labels for missing or suspicious data.
4. **`exclusion_reason(row)`** removes obvious non-events (stadium tours,
   parking/VIP/add-on names, multi-day passes, anything outside the date
   window). They go to the `excluded` CSV with the reason.
5. It checks that `event_id` is unique, writes the two CSVs, and logs counts
   and flag totals to `logs/convert_<stamp>.log`.

Helpers:
- `dig(obj, ...)` reads nested fields safely and returns blank when a field is
  missing.
- `join(...)` combines a set of labels (no repeats).
- `join_aligned(...)` combines one value per item and keeps blanks, so
  performer columns line up.

### `evaluate_test.py`

Read-only summary. It prints:
- listed-price availability by city, segment, ticketing platform, status and
  all-in flag;
- price statistics;
- quality-flag counts;
- venues outside the expected states;
- coverage of the extra fields.

## About prices

The price columns hold **Ticketmaster listed price ranges** (`priceRanges`).
They are **not verified face value**. Ticketmaster doesn't document whether
fees are included, and most values have non-round cents, which suggests they
are.

| Column | Meaning |
|---|---|
| `reported_price_min`, `reported_price_max` | Exactly what Ticketmaster returned, including `$0–$0` |
| `listed_price_min`, `listed_price_max` | Values to use for analysis. **Blank** when there is no range or the range is `$0–$0` |
| `has_listed_price` | True only when there is a usable (> $0) listed range |
| `price_issue` | `no_price_range`, `zero_price_range`, or blank |
| `listed_price_currency`, `listed_price_type`, `price_range_count` | As reported |

A `$0–$0` range on a paid show is not a free ticket. It's kept in
`reported_price_*` for transparency and excluded from `listed_price_*`.
Missing prices are never filled in.

## CSV columns (91)

Lists are joined with ` | `. Performer columns (`attraction_*`) line up by
position.

| Group | Columns |
|---|---|
| Collection / search | `source`, `collected_at`, `primary_search_city`, `search_cities`, `search_segments`, `search_city_count`, `search_hit_count`, `distance_miles` |
| Event | `event_id`, `event_name`, `event_url`, `status` |
| Dates & times | `local_date`, `local_time`, `start_datetime_utc`, `event_timezone`, `date_tba`, `time_tba`, `no_specific_time`, `span_multiple_days`, `end_local_date`, `end_local_time`, `doors_local_time`, `initial_start_local_date` (set when rescheduled) |
| Classification | `segment`, `segment_id`, `genre`, `genre_id`, `subgenre`, `subgenre_id`, `class_type`, `class_subtype`, `family_event`, `classification_count`, `all_segments`, `all_genres`, `all_subgenres` |
| Venue | `venue_id`, `venue_name`, `venue_url`, `venue_address`, `venue_city`, `venue_state`, `venue_postal_code`, `venue_country`, `venue_latitude`, `venue_longitude`, `venue_timezone`, `tm_market_ids`, `tm_market_names`, `dma_ids`, `venue_upcoming_events` |
| Performers | `attraction_count`, `attraction_ids`, `attraction_names`, `attraction_segments`, `attraction_genres`, `attraction_upcoming_events`, `attraction_musicbrainz_ids`, `attraction_wiki_urls`, `attraction_spotify_urls` |
| Promoters | `promoter_id`, `promoter_name`, `promoter_count`, `all_promoter_ids`, `all_promoter_names` |
| Listed price | see "About prices" above |
| Sales | `public_sale_start_reported`, `public_sale_start` (blank when Ticketmaster's `1900-01-01` placeholder), `public_sale_end`, `presale_count`, `presale_names`, `first_presale_start` |
| Ticketing | `ticketing_platform` (`ticketmaster.com`, `ticketweb.com`, …), `all_inclusive_pricing`, `safe_tix_enabled`, `has_seatmap`, `age_restriction_enforced`, `ticket_limit_info`, `addon_product_count`, `addon_product_types`, `addon_product_names` |
| Quality | `quality_flags` |

Kept in the raw JSON only, not the CSV: long free text (`info`, `pleaseNote`,
seating, parking and box-office details), images and social links.

## Quality flags

| Flag | Meaning | Count (test) |
|---|---|---|
| `no_promoter` | No promoter listed | 211 |
| `no_performer` | No attractions listed | 96 |
| `no_event_timezone` | Event has no `dates.timezone` (the venue timezone is still filled) | 51 |
| `placeholder_onsale_date` | Public on-sale date reported as `1900-01-01`; cleaned date left blank | 45 |
| `zero_price_range` | Price range reported as $0–$0; not usable | 15 |
| `no_venue_address` | Venue has no street address | 6 |
| `venue_state_outside_search_area` | Venue state isn't one of the city's expected states (4 Manhattan venues listed as AZ/CO) | 4 |
| `no_start_time` | No UTC start time (date-only event) | 0 |
| `multiple_search_cities` | Returned by more than one city search | 0 |
| `repeated_in_searches` | Returned more than once within the searches | 0 |

## Phase 1 results (raw run 2026-11-02 20:39, re-converted with the updated converter)

| | LA | NYC | Total |
|---|---|---|---|
| Events returned | 102 | 245 | 347 |
| After non-event filter | 101 | 235 | 336 |
| With any `priceRanges` | 27 | 133 | 160 (48%) |
| With a usable listed price | 26 | 119 | **145 (43%)** |

- All 20 API requests returned HTTP 200. 336 unique event IDs.
- **Listed prices depend on the platform:** 145 of 170 TicketWeb events
  (85%) have one, versus 0 of 164 ticketmaster.com events. That's why no
  sports, arena or Live Nation event has a listed price.
- Usable listed prices: median min $38.10, median max $43.70. 68% are a
  single price (min = max).
- 11 non-events excluded: 10 Yankee Stadium tours and 1 festival 2-day pass.
  Parking and VIP add-ons appear as `addon_product_*` on 61 events, not as
  separate events.
- The updated converter was checked against the first version row by row:
  - same kept and excluded event IDs;
  - `reported_price_*` identical to the old price columns;
  - `listed_price_*` identical wherever a usable price existed.

## Not done yet

- 10-city collection and repeated collection over time.
- Possible Arts & Theatre category (partner decision).
- Optional free context data (BLS admissions CPI, Census, Wikidata venue
  capacity, MusicBrainz).
- Database design. That's the team's job and is intentionally not here.
