# Data Sources and Collection Notes

Final dataset for the Ticketmaster + Census project: 25 U.S. cities, events
from Nov 12, 2026 to Jan 31, 2027. Run stamp: `2026-11-10_222442` (every
output file name ends with it).

## How to reproduce

From the project folder, with `TICKETMASTER_API_KEY` and `CENSUS_API_KEY` in `.env`:

```bash
.venv/bin/python scripts/collect_ticketmaster.py   # Ticketmaster raw JSON (one file per city)
.venv/bin/python scripts/convert_to_csv.py         # -> ticketmaster_events / _excluded CSVs
.venv/bin/python scripts/geocode_venues.py         # -> venues_geocoded CSV (Census Geocoder)
.venv/bin/python scripts/collect_census.py         # -> ACS, CBP and search-area CSVs
.venv/bin/python scripts/evaluate_collection.py    # data-quality report (changes nothing)
```

Each step reads the newest output of the step before. `config.py` holds the
cities, search points, radius and event window.

## Sources

| Source | What we use | Vintage / date | Access |
|---|---|---|---|
| Ticketmaster Discovery API v2 (`/discovery/v2/events.json`) | Music and Sports events, with venue, performers, classifications, promoters, listed price ranges | Snapshot collected 2026-11-10, 22:24–22:27 (Pacific); events dated 2026-11-12 to 2027-01-31 | Free API key; 5 requests/s, 5,000/day |
| Census Geocoder (`geocoding.geo.census.gov`) | Venue lat/lon → state, county, county subdivision, tract, ZCTA, incorporated place, metro/micro area, metropolitan division, combined statistical area | Benchmark `Public_AR_Current`, vintage `Current_Current`, run 2026-11-10, 22:27–22:34 | Free, no key |
| American Community Survey 1-year (`2025/acs/acs1`) | B01003 total population, B19013 median household income (2025 dollars), with margins of error | 2025 (released Oct 29, 2026) | Census API key |
| American Community Survey 5-year (`2024/acs/acs5`) | Same two tables | 2020–2024 (2024 dollars) | Census API key |
| County Business Patterns (`2023/cbp`) | Establishment counts (and employees where published) for NAICS 711310, 711320, 7113, 7112, 711211 | 2023 (latest; no 2024 release) | Census API key |
| CBP 2023 bulk files (`cbp23co.zip`, `cbp23msa.zip`) | Employment noise flags G/H/J only (the API's `EMP_N` is always 0) | 2023 | Download, no key |
| Census 2025 Gazetteer, tracts (`2025_Gaz_tracts_national.zip`) | Tract internal points and land area, to find tracts inside each 25-mile search circle | 2025 Gazetteer (2020 tract boundaries) | Download, no key |
| Census Vintage 2025 population estimates (`sub-est2025.csv`) | Used once to choose the 25 largest cities | July 1, 2025 estimates | Download, no key |

NAICS codes:
- 711310: promoters of performing arts, sports and similar events **with
  facilities** (mostly venue operators).
- 711320: promoters **without** facilities.
- 7113: all promoters (711310 + 711320).
- 7112: spectator sports.
- 711211: sports teams and clubs.

## The 25 cities and search areas

The 25 largest incorporated places by Census Vintage 2025 estimates. Each is
searched with a **25-mile radius** around its city hall (geocoded with the
Census Geocoder), `countryCode=US`, Music and Sports segments.

Points to know:
- A search area is a circle, **not city limits**. A venue found by "Dallas" may
  be in another city or county. Use the geocoded identifiers in
  `venues_geocoded_*.csv` for real geography.
- **Overlapping circles:** Dallas–Fort Worth (31 mi apart) and San Jose–San
  Francisco (42 mi apart). An event found by both appears **once** in the
  events CSV, with both cities in `search_cities` and the flag
  `multiple_search_cities`.
- Circles cross state lines in New York (NJ), Chicago (IN), Philadelphia (NJ,
  DE), Charlotte (SC), Washington (MD, VA) and El Paso (NM).
- Nashville's search point is 100 James Robertson Pkwy (next to the Metro
  Courthouse). Boston's is 1 City Hall Ave, about 0.3 mi from City Hall Plaza.

## Missing and suppressed values

Nothing is filled in. Blanks always mean "not available", never zero.

- **Ticketmaster prices:** `listed_price_min/max` are blank when there is no
  price range or Ticketmaster reported $0–$0. The original values are kept in
  `reported_price_min/max`.
  - These are **Ticketmaster listed price ranges, not verified face value**.
  - Events without prices are kept.
- **Ticketmaster on-sale dates:** the placeholder `1900-01-01` is blanked in
  `public_sale_start`. The original is kept in `public_sale_start_reported`,
  and the row is flagged.
- **ACS special codes** (e.g. `-666666666`) become blank estimates, with the
  reason in `*_note`.
  - `-555555555` on a margin of error means "controlled estimate, no sampling
    error" (blank MOE).
  - Income `250001` and `2499` are kept and noted as top-coded / bottom-coded.
- **CBP:** since 2017, Census publishes a cell only when it has **3 or more
  establishments**. For our venues' counties, metro areas and ZIPs and the
  search-circle counties, each missing cell is written as a row with
  `published = False` and a blank count (meaning **0–2**, not 0).
  - Parent codes (7113, 7112) can bound some of these by subtraction, but
    Census calls such values unofficial.
  - ZIP-level CBP has establishment counts only (employees blank).
- **Employment noise:** CBP employment has noise added. `employees_noise_flag`
  G = under 2%, H = 2–5%, J = 5% or more. Establishment counts have no noise.

## Limitations

1. **Time mismatch.** Events are Nov 2026 – Jan 2027. ACS 1-year is 2025, ACS
   5-year is 2020–2024 and CBP is 2023. CBP 2024 is delayed: the CBP
   methodology page says Census is revising disclosure methods after a
   Commerce Department order prohibiting noise infusion.
2. **Ticketmaster is not the whole market.** Venues sold through AXS, DICE,
   Eventbrite, See Tickets or box offices are missing. Ticketmaster's share
   varies by city.
3. **Listed prices** exist mostly for TicketWeb (small-venue) events. Main
   ticketmaster.com events, including all sports and arena shows in the pilot,
   have none.
4. **One snapshot.** Events, statuses and prices are as of the collection
   date. Events announced later are missing, and far-future dates are thinner.
5. **Circles vs Census areas.** A 25-mile circle matches no Census boundary.
   `search_area_tracts_*.csv` lists the tracts whose internal point falls in
   each circle (an approximation at the edges). Counties and metro areas
   extend beyond the circles.
6. **Venue location ≠ audience.** Tract/ZCTA values describe the area where a
   venue sits. Tract and ZCTA margins of error can be large.
7. **ACS 1-year** covers only areas with 65,000+ people. Use ACS 5-year for
   tracts and ZCTAs.
8. **ZIP vs ZCTA.** Ticketmaster's ZIP and the geocoded ZCTA can differ
   (special ZIPs, boundaries, bad addresses). CBP ZIP data uses USPS ZIP codes.
9. **CBP industry ≠ venue.** 711310 counts businesses that operate facilities.
   Bars, clubs and restaurants that host music are classified elsewhere, and
   one business can run several venues.
10. **Terms of use.** Ticketmaster limits storing and redistributing its data:
    keep `data/` private (it is git-ignored). Census data is public domain.
    Credit "Data from Ticketmaster Discovery API" and the Census datasets above.

## Collection results (run 2026-11-10_222442)

Totals and completeness:
- **Ticketmaster:**
  - 606 requests, 0 failed, 0 incomplete search windows (every search
    returned all `totalElements`). About 4,300 of the 5,000 daily requests
    were left.
  - 12,114 events received, which is 12,088 unique event IDs. 25 kept events
    were found by both Dallas and Fort Worth. San Jose–San Francisco shared
    none.
  - 11,943 events kept and 145 excluded: 120 venue/stadium tours, plus 25
    VIP-upgrade, parking and multi-day-pass listings.
- **Census Geocoder:** 1,020 of 1,020 venues matched (county, tract, ZCTA
  and metro area 100%; incorporated place 89%).
- **Census API:** 45 requests, 0 failed. The API key does not appear in any
  log or raw file.

Events by status:
- Music: 8,936 onsale, 211 offsale, 157 cancelled, 82 rescheduled.
- Sports: 2,383 onsale, 151 offsale, 7 cancelled, 7 rescheduled.
- 9 events have a primary classification of Miscellaneous/Undefined (found
  by the Music search).

Missing values in the events CSV (as quality flags):

| Flag | Events |
|---|---|
| `no_promoter` | 6,295 |
| `no_event_timezone` (venue timezone still present) | 2,694 |
| `no_performer` | 2,273 |
| `placeholder_onsale_date` | 2,254 |
| `zero_price_range` | 428 |
| `no_start_time` (date only) | 286 |
| `no_venue_address` | 121 |
| `multiple_search_cities` | 25 |
| `venue_state_outside_search_area` | 2 |

Prices:
- Usable listed price: **2,676 of 11,943 events (22%)**.
- All 2,676 are TicketWeb events. None of the 7,750 ticketmaster.com events
  has one.
- Share with a listed price varies a lot: New York 53%, Las Vegas, Austin,
  Oklahoma City and El Paso 0–1%.

Venue geography:
- **Outside city limits:** 117 venues (`outside_incorporated_place`), 58 of
  them in the Las Vegas search area, because the Strip is in unincorporated
  Clark County.
- **ZIP mismatch:** for 117 venues, Ticketmaster's ZIP differs from the
  geocoded ZCTA.
- **State mismatch:** 2 venues are listed by Ticketmaster in a state their
  coordinates are not in:
  - Bull Shooters (listed Phoenix, AZ; located in Manhattan);
  - Corazon del Barrio (listed San Diego, CA; coordinates in Jacksonville,
    FL).

  These are flagged, not corrected.
- **Other ticketing sites:** 267 events link to other sites (AXS, DICE,
  Etix, Universe and others), and some URLs are wrapped in tracking links.
  `ticketing_platform` is the link's host as given.

Census coverage for the venues:
- **ACS 5-year:** income for every venue's county, metro and place; 97% of
  venues' tracts and 98% of ZCTAs.
- **ACS 1-year:** income for 93% of venues' places (smaller places are not in
  1-year data at all).
- **Blank ACS 5-year income:** 8,138 rows across all levels, all marked
  "estimate not available".
- **Coded income:** 821 values are top-coded ($250,000+) and 49 bottom-coded.
- **CBP 2023:** 4,922 published rows and 2,380 "not published (0–2)" rows.
  Not published is common at ZIP level, e.g. 711310 has 255 published vs
  408 not published.

## File inventory

All files are in `data/processed/` and end in `_2026-11-10_222442.csv`.

| File | Rows | One row per | What it represents |
|---|---|---|---|
| `ticketmaster_events` | 11,943 | Ticketmaster event ID | Every kept Music/Sports event, with all search areas that found it |
| `ticketmaster_excluded` | 145 | Ticketmaster event ID | Removed non-event listings, same columns plus `exclusion_reason` |
| `venues_geocoded` | 1,020 | Ticketmaster venue ID | Venue as listed by Ticketmaster plus the Census areas its coordinates fall in |
| `census_acs1_2025` | 2,071 | geography (level + GEOID) | ACS 2025 1-year population and median household income: places, counties, metro/micro areas (65,000+ people) |
| `census_acs5_2024` | 129,646 | geography (level + GEOID) | ACS 2020–2024 5-year, same values: tracts in the 23 states + DC we need, plus all ZCTAs, places, counties and metro/micro areas |
| `census_cbp2023` | 7,302 | geography + NAICS code | CBP 2023 establishments (and employees) for 5 live-event industries, plus "not published" rows for our geographies |
| `search_area_tracts` | 22,088 | search area + tract | Tracts whose internal point is inside each city's 25-mile circle (a tract in two circles appears twice) |

Columns:

- **ticketmaster_events** (91; see `phase1_guide.md` for full descriptions):
  - search: `primary_search_city`, `search_cities`, `search_segments`,
    `search_city_count`, `search_hit_count`, `distance_miles`
  - event and dates: `event_id`, `event_name`, `event_url`, `status`,
    `local_date`, `local_time`, `start_datetime_utc`, `event_timezone`, ...
  - classification: `segment`, `genre`, `subgenre` (+ IDs), `all_segments`,
    `all_genres`, ...
  - venue: `venue_id`, `venue_name`, `venue_address`, `venue_city`,
    `venue_state`, `venue_postal_code`, `venue_latitude`, `venue_longitude`,
    `tm_market_*`, `dma_ids`, ...
  - performers: `attraction_ids`, `attraction_names`, `attraction_genres`,
    `attraction_musicbrainz_ids`, ... (aligned lists joined with " | ")
  - promoters: `promoter_id`, `promoter_name`, `all_promoter_ids`,
    `all_promoter_names`
  - price: `reported_price_min/max`, `listed_price_min/max`,
    `listed_price_currency`, `has_listed_price`, `price_issue`
  - sales and ticketing: `public_sale_start(_reported)`, `presale_*`,
    `ticketing_platform`, `all_inclusive_pricing`, `addon_product_*`, ...
  - `quality_flags`
- **venues_geocoded** (35):
  - from Ticketmaster: `venue_id`, `venue_name`, `venue_address`,
    `venue_city`, `venue_state`, `venue_postal_code`, `venue_country`,
    `venue_latitude`, `venue_longitude`
  - from our data: `event_count`, `search_cities`
  - geocoding: `geocode_method`, `geocode_http_status`
  - Census areas (`*_geoid` and `*_name` for each): `state`, `county`,
    `county_subdivision`, `tract`, `zcta`, `place`, `metro_area`,
    `micro_area`, `metro_division`, `combined_area`
  - `state_abbr`, `geocode_flags`
- **census_acs1_2025 / census_acs5_2024** (12): `dataset`, `vintage`,
  `geo_level` (place, county, metro_micro_area, tract, zcta), `geoid`,
  `geo_name`, `state_fips`, `population`, `population_moe`,
  `population_note`, `median_household_income`,
  `median_household_income_moe`, `median_household_income_note`
- **census_cbp2023** (12): `dataset`, `vintage`, `geo_level` (county,
  metro_micro_area, zip), `geoid`, `geo_name`, `naics_code`, `naics_label`,
  `establishments`, `employees`, `published`, `note`,
  `employees_noise_flag`
- **search_area_tracts** (9): `search_city`, `tract_geoid`, `county_geoid`,
  `state_fips`, `state_abbr`, `internal_point_lat`, `internal_point_lon`,
  `distance_miles`, `land_area_sqmi`

GEOID formats:
- state: 2 digits;
- county: 5 (state + county);
- tract: 11 (state + county + tract);
- place: 7 (state + place);
- ZCTA and ZIP: 5;
- metro/micro area (CBSA): 5;
- combined area: 3.

**Read GEOIDs as text, not numbers, or leading zeros are lost** (e.g.
`dtype=str` in pandas).

Raw data (git-ignored):
- `data/raw/ticketmaster/2026-11-10_222442/`: 25 city files plus
  `manifest.json` (115 MB).
- `data/raw/census/2026-11-10_222442/`: `geocoder_venues.jsonl`,
  `acs1_2025.json`, `acs5_2024.json`, `cbp_2023.json` (20 MB).
- Census reference downloads in `data/raw/census/`: Gazetteer tracts, CBP
  bulk files, and the pilot's ACS table files.
