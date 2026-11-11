# Option Assessment: Ticketmaster + U.S. Census (2026-11-05)

Research only. No pipeline changes and no data collected. Census API checks
were limited to the dataset catalog, geography lists and variable lists,
which need no key. Venue figures come from our existing LA/NYC test (336
events, 111 venues).

## 1. What Census data is free

**Access:** the Census Data API is free but **now requires a key**. Unkeyed
data requests redirect to `api.census.gov/data/missing_key.html`. Keys are
free by email signup (api.census.gov/data/key_signup.html). Census data is
U.S. government public domain: no storage limits, attribution only.

| Dataset (latest available) | Useful variables | Geographies relevant to us |
|---|---|---|
| **ACS 5-year 2020–2024** (`2024/acs/acs5`) | Population, median household income, age, race/ethnicity, education, commuting, etc. | Place (city), county, metro area (MSA), **ZIP code tabulation area (ZCTA)**, **census tract**, block group |
| **ACS 1-year 2025** (`2025/acs/acs1`) | Same topics, more current | Place, county, MSA only (areas of 65,000+ people). **No ZCTA or tract** |
| **County Business Patterns 2023** (`2023/cbp`) | Establishments, employees, payroll by industry (NAICS) | County, MSA, **ZIP code**, state |

Release timing:
- ACS 5-year 2021–2025 isn't published yet (`2025/acs/acs5` returns 404).
- CBP 2024 isn't published yet (404).

**Live-event industry codes in CBP** (NAICS 2017, confirmed in the API's
code list):

| Code | Industry |
|---|---|
| 711310 | Promoters of Performing Arts, Sports, and Similar Events **with Facilities** (mostly venues) |
| 711320 | Promoters … without Facilities |
| 7113 | All promoters |
| 7111 | Performing arts companies |
| 711211 | Sports teams and clubs |

## 2. Can it be combined with our Ticketmaster data?

Join keys we already have for every venue:
- ZIP code (`venue_postal_code`, 111/111 venues; 65 distinct ZIPs in LA + NYC);
- latitude/longitude;
- state.

Possible join levels:

| Level | How | Good for | Problems |
|---|---|---|---|
| **City (place)** | Population or income of LA city, NYC | Simple headline numbers | **Doesn't match our search area.** A 25-mile circle is about 1,960 sq mi, far bigger than LA city or NYC and smaller than either metro. NJ, Long Beach, etc. would be counted as events but not as population. Only 10 data points. |
| **Population inside the 25-mile circle** | Add up tracts or ZCTAs whose centroid falls inside the circle. Centroids come from the free Census Gazetteer files. | A denominator that matches our search exactly ("events per 100k residents in the search area") | Centroid inclusion approximates edges. One extra download and a distance calculation. Still only 10 cities. |
| **Metro area (MSA) / county** | Assign each venue to a county (Census Geocoder converts lat/lon to county and tract, free, no key), then join county or MSA data | Standard, defensible geography; CBP and ACS 1-year 2025 both work here | Our circle doesn't cover a whole metro, so per-capita numbers need care |
| **Venue ZIP (ZCTA) or tract** | `venue_postal_code` → ZCTA; or lat/lon → tract | Hundreds of venues, so far more data points than 10 cities | **A venue's neighborhood isn't its audience.** Destination venues sit in commercial ZIPs with few residents (e.g., 10036 Times Square has 45 of our events). ZIP ≠ ZCTA exactly. |

Additional mismatches to state up front:
- **Time:** ACS 5-year covers 2020–2024 and CBP covers 2023, while our
  events are Nov 2026 – Jan 2027.
- **Suppression:** CBP numbers for small industries in small areas are often
  hidden or shown only as ranges.

## 3. Existing projects

- **[rudra-ay/Concert-Ticket-Modeling](https://github.com/rudra-ay/Concert-Ticket-Modeling)**
  (updated **2026-10-27**): Ticketmaster Discovery + **Census ACS metro
  income and population** + Wikidata venue capacity + ListenBrainz
  popularity + BLS CPI + MusicBrainz. It models concert ticket prices. It's
  the closest overlap with *both* of our options (Census and a
  Last.fm-like popularity source). It isn't a SQL/ERD project, but the TA
  could find it.
- **ISMIR 2022 poster**
  ([PDF](https://ismir2022program.ismir.net/static/posters/116.pdf)): a "Live
  Music Event Rate" (music events per 100k people) for 1,139 U.S. cities,
  correlated with socioeconomic indicators. **"Events per capita vs income
  or education across cities" has already been published**, on much larger
  data.
- **Portland State GIS poster**
  ([PDF](https://web.pdx.edu/~jduh/courses/geog492s16/Projects/Perez_GIS2_Poster.pdf)):
  music venues in Portland, NYC and LA mapped against tract-level median age,
  income and diversity. Close to the venue-neighborhood idea.
- **[w-aquis-duke/ticketmaster-global-events](https://github.com/w-aquis-duke/ticketmaster-global-events)**:
  a Duke group project summarizing Ticketmaster music events by state and
  genre (Streamlit, daily snapshots).
- **[leomckenna/ticketmaster-data-collection](https://github.com/leomckenna/ticketmaster-data-collection)**:
  a Ticketmaster events → normalized SQLite schema with daily snapshots (see
  the Last.fm assessment).
- **Melbourne Live Music Census**: venues per resident by city, including
  NYC and LA. A well-known benchmark framing.
- **Kaggle:** searches for "census concerts" and "music venues census"
  returned **nothing relevant**. Census datasets in general are everywhere on
  Kaggle, which is the TA's concern, but we'd pull specific tables fresh from
  the API.

## 4. Would it be meaningful, or just added on?

Census only adds value if the question needs it.

**Weak uses** (likely to read as "added for the sake of it"):
- Events per capita across 10 cities. Already published (ISMIR 2022), only
  10 data points, and confounded by Ticketmaster's market share.
- Correlating city income with listed prices. Only about 43% of events have
  a listed price, almost all small TicketWeb clubs, and there are 10 cities.

**Stronger uses:**
- **Ticketmaster coverage vs the Census-measured industry.** Compare our
  Ticketmaster venue and event counts with CBP establishment counts (711310
  venues, 7113 promoters) by county or metro. This turns our biggest
  limitation (Ticketmaster isn't the whole market) into the research
  question. We found nothing published on this. Caveats: NAICS codes
  classify businesses, not venues; the data is from 2023; some values are
  suppressed.
- **Venue-level context** across hundreds of venues: listed-price
  availability, ticketing platform, and genre mix vs ZCTA/tract income and
  population density. Feasible, but it has to be framed as "the
  neighborhoods where venues sit", not "the audience".

## 5. Feasibility for the Nov 19 ERD

- **Data access:** free key (instant), small downloads (a few hundred
  geographies), no fuzzy matching. Joins use standard codes (FIPS, ZIP).
  Easier and lower-risk than Last.fm.
- **Unknowns:** how many CBP values are suppressed at county/ZIP level for
  711310/7113, and how cleanly ZIPs map to ZCTAs. Both can be checked in
  under an hour once there's a key.
- **Biggest decision needed before the ERD:** which geography is the unit of
  comparison (search circle, county/metro, or venue ZIP/tract). Everything
  else follows from that.

## Sources

- Census API: https://api.census.gov/data/2024/acs/acs5/geography.json · https://api.census.gov/data/2025/acs/acs1/geography.json · https://api.census.gov/data/2023/cbp/geography.json · https://api.census.gov/data/2023/cbp/variables/NAICS2017.json · key signup https://api.census.gov/data/key_signup.html
- Projects: links inline above.
