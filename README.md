# TicketMarketAnalytics

TicketMarketAnalytics is a graduate SQL database project at UC Davis. It
compares live-event markets across 25 major U.S. cities. The project combines
Ticketmaster event listings with U.S. Census data to look at how event
availability, listed ticket prices, venues, genres and promoter activity
differ between cities, and how they relate to local population, income and
the size of each area's live-event industry.

## Data sources

| Source | What it provides | Year / vintage |
|---|---|---|
| [Ticketmaster Discovery API](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/) | Music and Sports events with venue, performers, classifications, promoters, sale dates, status and listed price ranges | Snapshot collected November 10, 2026 |
| [Census American Community Survey (ACS)](https://www.census.gov/programs-surveys/acs) | Total population and median household income, with margins of error | 2025 1-year (cities, counties, metro areas); 2020–2024 5-year (also census tracts and ZIP Code Tabulation Areas) |
| [Census County Business Patterns (CBP)](https://www.census.gov/programs-surveys/cbp.html) | Establishment counts for live-event industries: venue operators (NAICS 711310), promoters (711320, 7113), spectator sports (7112) and sports teams (711211) | 2023, the latest release |

Venues are matched to Census geography with the
[Census Geocoder](https://geocoding.geo.census.gov/geocoder/). Its locations
also determine which census tracts fall inside each search area. Full source
details are in [docs/data_sources.md](docs/data_sources.md).

## Dataset coverage

- **11,443 events** (9,104 Music, 2,330 Sports, and 9 classified by
  Ticketmaster as Miscellaneous or Undefined), dated **November 12, 2026
  through January 31, 2027**.
- **1,019 venues**, each matched to its state, county, census tract, ZIP Code
  Tabulation Area and metro area. 902 are also inside an incorporated city.
- **25 city search areas**: the 25 largest U.S. cities by Census 2025
  population estimates.
  - Each search area is a 25-mile radius around the city hall.
  - New York has the most events (2,405); El Paso has the fewest (72).
- **645 listings excluded** as non-events: venue and museum tours, skating
  sessions, parking, VIP upgrades and multi-day passes. They are kept in a
  separate file with the reason for each.

## How the data was collected and cleaned

1. **Ticketmaster.** The Discovery API was searched for each city, segment
   (Music, Sports) and week of the event window.
   - Searches were limited to U.S. venues and followed every page of results.
   - A completeness check compares the results received with the total
     Ticketmaster reported. The final run had no failed or incomplete
     searches.
   - Raw responses are saved unchanged.
2. **Conversion.** Raw responses become one row per Ticketmaster event ID.
   - Events found by more than one search area (Dallas and Fort Worth
     overlap) appear once, with every search area listed.
   - Missing values stay blank and are never estimated. Prices are kept
     even when missing.
   - Suspicious or incomplete records get quality flags.
   - Non-event listings move to an excluded file. Borderline attraction
     admissions are kept and flagged for review.
3. **Geocoding.** Each venue's coordinates are sent to the Census Geocoder
   for its Census geographic identifiers. Venues are never assigned to a city
   just because a city's search area found them.
4. **Census.** ACS and CBP tables are retrieved through the Census Data API.
   - ACS special codes become blanks with an explanatory note.
   - CBP cells that Census does not publish (fewer than 3 establishments)
     are kept as "not published (0–2)" rather than zero.
5. **Quality report.** A read-only report checks completeness, duplicates,
   missing values and Census coverage across all outputs.

## Repository structure

```
README.md
requirements.txt          Python dependencies
.env.example              Template for the API keys (copy to .env)
scripts/
  config.py               Cities, search points, radius and event window
  api_client.py           Shared rate-limited API client; keeps keys out of logs
  collect_ticketmaster.py Ticketmaster collection -> data/raw/ticketmaster/
  convert_to_csv.py       Raw Ticketmaster JSON -> event CSVs
  geocode_venues.py       Venue coordinates -> Census geographic identifiers
  collect_census.py       ACS, CBP and search-area tract data
  evaluate_collection.py  Data-quality report (read-only)
  probes/                 Earlier exploratory scripts, not part of the pipeline
docs/
  data_sources.md         Sources, missing values, limitations, file inventory
  phase1_guide.md         Notes from the LA/NYC pilot (column reference)
  ...                     Earlier research notes on data source options
data/                     Local only (raw/ and processed/), not in the repository
logs/                     Local only, not in the repository
```

## Setup

The project was developed with Python 3.14.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Then add your own keys to `.env`:

- `TICKETMASTER_API_KEY`: a free key from the
  [Ticketmaster Developer Portal](https://developer.ticketmaster.com/).
- `CENSUS_API_KEY`: a free key from
  [api.census.gov](https://api.census.gov/data/key_signup.html).

`LASTFM_API_KEY` is only used by an exploratory script in `scripts/probes/`.

`.env` is git-ignored. Never commit it.

## Running the pipeline

Run these from the repository root, in order. Each step reads the newest
output of the step before it.

```bash
.venv/bin/python scripts/collect_ticketmaster.py   # Ticketmaster raw JSON, one file per city
.venv/bin/python scripts/convert_to_csv.py         # ticketmaster_events / ticketmaster_excluded CSVs
.venv/bin/python scripts/geocode_venues.py         # venues_geocoded CSV
.venv/bin/python scripts/collect_census.py         # ACS, CBP and search-area tract CSVs
.venv/bin/python scripts/evaluate_collection.py    # data-quality report (changes no files)
```

What to expect:
- **Ticketmaster collection** uses about 600 of Ticketmaster's 5,000 daily
  requests.
- **Geocoding** takes roughly 7 minutes for about 1,000 venues. If it is
  interrupted, rerunning it continues where it stopped.
- **Census collection** downloads three reference files on first use (the
  Census tract Gazetteer and the CBP county and metro-area bulk files).
- **Run stamp:** every output is named with the run's timestamp; the
  current dataset is `2026-11-10_222442`.
- **Converting an existing run** (e.g. after changing the filter) needs no
  new requests:
  `convert_to_csv.py data/raw/ticketmaster/<run_stamp>`.

The processed files are:

| File | One row per |
|---|---|
| `ticketmaster_events_<run>.csv` | Ticketmaster event |
| `ticketmaster_excluded_<run>.csv` | Excluded non-event listing, with `exclusion_reason` |
| `venues_geocoded_<run>.csv` | Venue, with its Census geographic identifiers |
| `census_acs1_2025_<run>.csv` | Geography in ACS 2025 1-year |
| `census_acs5_2024_<run>.csv` | Geography in ACS 2020–2024 5-year |
| `census_cbp2023_<run>.csv` | Geography and industry code in CBP 2023 |
| `search_area_tracts_<run>.csv` | Census tract inside a city's search area |

Column descriptions are in [docs/data_sources.md](docs/data_sources.md).
Census identifiers have leading zeros and should be read as text.

## Data limitations

- **Missing ticket prices.**
  - Only 23% of events have a usable listed price, and almost all of those
    are TicketWeb (small-venue) events. Main ticketmaster.com events, which
    include sports and arena concerts, return no price range.
  - Prices are Ticketmaster's listed price ranges, not verified face value.
    Ticketmaster does not document whether fees are included.
- **Ticketmaster coverage.**
  - Ticketmaster is not the whole live-event market. Venues ticketed through
    AXS, DICE, Eventbrite, See Tickets or their own box offices are largely
    missing, and Ticketmaster's share varies by city.
  - The data is a single snapshot: events announced after collection are
    not included.
- **Different Census years.** The events are from 2026–2027, but the Census
  data is older:
  - ACS 1-year is 2025 and ACS 5-year covers 2020–2024.
  - County Business Patterns is 2023. Its 2024 release is delayed while the
    Census Bureau revises its disclosure methods.
  - ACS 1-year covers only areas with 65,000 or more people.
- **Search areas are not city limits.**
  - A 25-mile circle matches no Census boundary and can cross county and
    state lines.
  - For example, most Las Vegas venues are outside the city of Las Vegas,
    because the Strip is unincorporated.
- **Other gaps.**
  - Many events have no listed promoter (51%) or performer (20%).
  - Industry codes count businesses, not venues.
  - Tract-level Census values describe where a venue sits, not who attends.

More detail is in [docs/data_sources.md](docs/data_sources.md).

## Data not included

Raw API responses, processed CSVs and logs are not included in this
repository. They are git-ignored and stay local, partly because Ticketmaster's
terms limit storing and redistributing its data. To reproduce the dataset,
run the pipeline with your own API keys. Note that Ticketmaster returns only
upcoming events, so a new run collects a different snapshot.

## Project status

Data collection and cleaning are complete. The cleaned dataset (run
`2026-11-10_222442`) is the working version for the SQL phase of the
project. The next step is designing the relational database, an ERD due
November 19, 2026, and then loading this data into it for analysis.
