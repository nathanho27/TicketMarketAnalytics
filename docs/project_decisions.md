# Project Decisions

Decisions made by Nathan and Nick for the BAX-421 final project, recorded
as stated. Reasons are paraphrased from what Nathan said when the decision
was made. This is a reference record, not report text.

## 2026-11-11: Working dataset scope

Decided by Nathan and Nick, relayed by Nathan during the scope review. It
applies to collection run `2026-11-10_222442`. It is implemented by
`scripts/build_working_dataset.py` (output folder
`data/processed/working_2026-11-10_222442/`, log
`logs/build_working_2026-11-10_222442.log`). The original raw and processed
files are unchanged.

### Project direction

- Focus: differences in live-event activity across major U.S. metropolitan
  markets, from the perspective of someone analyzing the entertainment
  industry.
- Event volume is the primary measure. Variety is looked at through distinct
  event names and genre mix.
- Census demographics and CBP industry data provide context for differences.
  They are not presented as causes.
- Pricing was dropped as a focus: listed-price coverage is too uneven across
  markets and event categories for meaningful comparisons.

### Markets

| Decision | Reason given |
|---|---|
| Use 24 Census metro areas for demographic comparisons | Chosen over the 25-mile search areas and counties |
| Assign each event to the metro of its venue, not to the city search that found it | Avoids double counting and uses actual venue location |
| Combine Dallas and Fort Worth into one market (Dallas-Fort Worth) | They share the same metro area |
| Keep San Francisco-Oakland and San Jose separate | To distinguish the SF/Oakland market from the South Bay |
| Exclude the 69 events outside the 24 metros (Santa Cruz 49, Bremerton 17, Boulder 3) | Outside the market definition; the original data is preserved |
| Use short market labels and keep the official Census metro names for reference | Recognizable labels; official names in `market_labels.csv` |

### Census and industry data

| Decision | Reason given |
|---|---|
| Use ACS 1-year 2025 (population, median household income) at metro level | More recent, covers all 24 markets, simpler |
| Keep ACS 5-year 2020–2024 and the search-area coverage calculations for documentation only | Not needed in the final database |
| Keep CBP 2023 as a central part of the project | Local industry activity is central to the market comparison |
| CBP codes kept: 711310, 711320, 7112 | Distinct categories that do not overlap |
| CBP codes dropped: 7113, 711211 | Avoid overlapping categories |
| Use 7112 (spectator sports) instead of 711211 (teams) | Ticketmaster Sports includes more than team sports |
| Keep El Paso's unpublished 711320 value as missing, not zero | Census does not publish cells with fewer than 3 establishments |
| Keep CBP `employees` and `employees_noise_flag` with `establishments` | Decided on 2026-11-11 |

### Events

| Decision | Reason given |
|---|---|
| Keep event ID, name, URL, status, local date, local start time | Core event information; URL kept for traceability |
| Keep cancelled and rescheduled events with their status | Filtering depends on the analysis |
| Keep Music and Sports | To compare their differences across markets |
| Keep segment and primary genre, with Ticketmaster IDs | Enough detail for market comparisons; IDs for traceability |
| Keep placeholder genres (Other, Undefined, Miscellaneous) as labels | Do not delete events; interpret with care |
| Keep subgenre for Sports only, using Ticketmaster's original values | Distinguishes professional, college and minor league for basketball, hockey and football; no new classification created |
| Drop Music subgenres | Too noisy |
| Keep `ticketing_platform` | Context about where listings came from |
| Keep the 15 Belmont Park general-admission racing days | Scheduled live sporting events |
| Exclude "Brushstrokes & Ballads VIP Admission" and "T-Mobile General Admission + F1 Afterparty Ticket Package" | Not standalone live events |
| Exclude "Zumba® Master Class led by Zumba® Jammer Carlos Henriquez…" (event `rZ7HnEZ1AfuN70`, labeled Sports, no genre) | A fitness class rather than a spectator sporting event |
| Exclude 85 ticket-package listings (`ticket_package_duplicate`): 59 "Official Ticket + Hotel Packages/Deals", 20 "Wizards VIP Packages", 4 PBR multi-day packages, 1 Hondo Rodeo Fest 3-day package, 1 "T-Mobile Grandstands + F1 Afterparty Ticket Package" | The project measures live-event activity, not ticket products. Each package duplicates a regular listing of the same event at the same venue on the same date. |
| Keep "Gretchen Wilson \| Official Rio Ticket + Hotel Packages" (event `1kC8vPbgGACEYs1`, 2026-11-13, Penn & Teller Theater at Rio Las Vegas) | It is the only listing of that concert in the raw, processed and excluded data, so excluding it would remove a unique live event |

Event fields dropped from the working scope:
- **Search and collection fields:** kept for documentation only.
- **Time detail:** UTC times, event timezone, end and doors times, TBA flags,
  original dates of rescheduled events.
- **Classification extras:** `class_type`/`class_subtype`, `family_event`,
  extra classifications.
- **Performers:** they did not add enough value for the complexity, with
  uneven missingness across platforms.
- **Promoters:** not central to the project.
- **Pricing, on-sale dates, presales, and other ticketing and add-on fields:**
  not central to the market analysis.

### Venues

| Decision | Reason given |
|---|---|
| Use the geocoded venue information | Sufficient for the analysis |
| Keep only the metro area ID as venue geography | County, tract and city IDs not needed |
| Drop venue timezone | Local dates and times are used |
| Drop Ticketmaster markets, DMA IDs and upcoming-event counts | Not needed |

## Resulting working dataset (verified 2026-11-11)

| File | Rows | Columns |
|---|---|---|
| `working_events.csv` | 11,286 | 13 |
| `working_venues.csv` | 1,012 | 9 |
| `working_acs1_2025_metros.csv` | 24 | 8 |
| `working_cbp2023_metros.csv` | 72 | 8 |
| `market_labels.csv` | 24 | 3 |
| `working_excluded_events.csv` | 157 | 5 |

Event counts:
- Music 8,981, Sports 2,296, Miscellaneous 6, Undefined 3.
- Excluded: 85 `ticket_package_duplicate`, 69 `outside_24_metros`, 2
  `non_event_admission`, 1 `non_event_fitness_class`.
- Markets most affected by the package exclusion: Las Vegas 1,049 → 1,008,
  Washington 491 → 471, Phoenix 438 → 422. No venue lost all its events.
- Working events plus excluded events equal the 11,443 events in the
  processed source, with no overlap.

Checks run by the build script:
- **Duplicates:** none on event ID, venue ID, metro ID, or metro + NAICS code.
- **References:**
  - every event's venue is in the venues file;
  - every venue's metro is in the market labels;
  - every market has ACS data;
  - every CBP row's metro is in the labels.
- **Venues with no event:** none.

Blank values (all expected):
- **Events:**
  - `local_time` 279 (time TBA or no specific time);
  - `genre`/`genre_id` 9 (the 6 Miscellaneous and 3 Undefined segment
    events; blank in the Ticketmaster data);
  - `subgenre` 8,994 (all 8,990 non-Sports events, plus 4 Sports events with
    no subgenre).
- **Venues:** `venue_address` 18.
- **ACS:**
  - `population_moe` 18 (controlled estimates with no margin of error,
    explained in `population_note`);
  - no income notes.
- **CBP:** El Paso 711320 has blank `establishments`, `employees` and
  `employees_noise_flag`, with `published = False`.

## 2026-11-11: Duplicate-listing cleanup

Decided by Nathan and Nick, relayed by Nick. Background: after the scope
build, 146 groups of working events shared venue, date and start time. Most
were the same event sold as separate listings (suites, half-price and premium
seating tiers, multi-night passes). The 55 events that share a URL are
recurring shows, not duplicates, and are not affected.

Each decision is recorded per event in `docs/dedup_decisions.csv` (columns
`event_id`, `action`, `reason`, `duplicate_of_event_id`, `note`; 185 rows:
167 EXCLUDE, 18 KEEP). `duplicate_of_event_id` names the listing that stays;
for multi-night passes it lists the individual nights, joined with ` | `.

Applied by `scripts/apply_dedup_decisions.py`, which runs **after**
`scripts/build_working_dataset.py`. It reads the six working CSVs and writes a
new copy of all six to `<input folder>/working_dedup_v2/` (with
`apply_dedup_decisions.log`). The input files are not changed. Nick's run
used `--input-dir "../processed copy"`.

### Reason codes

| Action | Reason code | Rows | Meaning (from the decision notes) |
|---|---|---|---|
| EXCLUDE | `ticket_tier_duplicate` | 76 | Seating or price tier of an event that also has a regular listing |
| EXCLUDE | `multi_event_pass` | 36 | Pass covering nights that are also listed individually |
| EXCLUDE | `f1_zone_listing` | 40 | Las Vegas Grand Prix seating/hospitality zone or multi-day package; each race day is represented by one kept GA listing |
| EXCLUDE | `same_headliner_duplicate` | 9 | Same show listed again (e.g. support act first, "MOVED TO" wording) |
| EXCLUDE | `exact_duplicate` | 2 | Identical listing twice (the onsale copy is kept over a cancelled copy) |
| EXCLUDE | `non_event_listing` | 4 | 3 open-mic sign-up sheets and 1 Ticketmaster test listing |
| KEEP | `kept_copy` | 11 | The copy kept for a duplicated show |
| KEEP | `f1_race_day_kept` | 3 | The single listing kept for each Grand Prix race day (Nov 19, 20, 21, all at Flamingo Zone) |
| KEEP | `tier_no_base` | 2 | Tier listing kept because no regular listing exists |
| KEEP | `pass_no_base` | 2 | Pass kept because no individual-day listings exist |

Excluded events go to `working_excluded_events.csv` with the reason code as
`exclusion_reason` and `metro_area_geoid` taken from the venue.

### Venues removed

Six Las Vegas Grand Prix venues had no events left, so the script drops them
from `working_venues.csv`. This keeps the build's rule that every venue has
at least one event.

| Venue ID | Venue | Events before |
|---|---|---|
| `KovZ917AY9R` | East Harmon Zone | 12 |
| `KovZ917AY9y` | Koval Zone by Heineken | 7 |
| `KovZ917AY9V` | T-Mobile Zone at Sphere | 7 |
| `KovZ917AVhX` | Grand Prix Plaza Zone | 7 |
| `KovZ917AY9T` | The Performance Zone | 4 |
| `KovZ917AIHV` | FORMULA 1 HEINEKEN LAS VEGAS GRAND PRIX | 2 |

Las Vegas keeps 62 venues (68 before), including Flamingo Zone, and 944
events (1,008 before).

**Excluded events can reference venues that are not in the venues file.**
110 of the 324 excluded rows do: 41 point to the six removed venues, and 69
(`outside_24_metros`, from the scope build) point to venues outside the 24
metros, which were never in the working venues file.

### Resulting dataset (`working_dedup_v2/`, verified 2026-11-11)

| File | Rows | Columns | Change |
|---|---|---|---|
| `working_events.csv` | 11,119 | 13 | 11,286 − 167 |
| `working_excluded_events.csv` | 324 | 5 | 157 + 167 |
| `working_venues.csv` | 1,006 | 9 | 1,012 − 6 |
| `working_acs1_2025_metros.csv` | 24 | 8 | unchanged (copied) |
| `working_cbp2023_metros.csv` | 72 | 8 | unchanged (copied) |
| `market_labels.csv` | 24 | 3 | unchanged (copied) |

Checks (script log plus a separate check by Nick's session):
- no event ID in both the events and excluded files, and no duplicate IDs;
- all 167 EXCLUDE IDs were in the original working events, and all 18 KEEP
  IDs are still there;
- the events file is the original minus exactly the 167, rows otherwise
  unchanged; the original 157 excluded rows are preserved;
- every venue has at least one event, and every event's venue exists;
- the remaining venue rows and the three copied files are identical to the
  input, and the input files' checksums are unchanged.

## 2026-11-18: Cross-listed event cleanup (second pass)

Decided by Nathan and Nick (rule proposed in Nathan's session, five manual
cases decided by Nathan, approved by Nick on 2026-11-18). Background: after
the first pass, 230 pairs of working events had the same date, start time and
a matching name but **different venue IDs**. Most were the same show sold on
two platforms (ticketmaster.com plus TicketWeb, AXS and others), each under
its own venue ID. No event appeared under more than two IDs.

Classification of the 230 pairs:
- 213 likely duplicates;
- 12 clearly separate events (different rooms or acts), left alone;
- 5 manual cases, decided by Nathan:
  - Alexandra Kay, Colour Revolt: duplicates;
  - Dwight Yoakam, Crankdat: **probable** duplicates (the room differs);
  - Boy Golden (The Basement vs The Basement East): unresolved, since the
    venues are different.

Decisions are recorded per event in `docs/dedup_decisions_pass2.csv` (same
five columns as `docs/dedup_decisions.csv`, no Ticketmaster fields; 221 rows:
215 EXCLUDE, 6 KEEP).

### Retention rule

For each duplicate pair, the first step that applies decides which copy is
kept. Ticketing platform is never used, because ticketmaster.com copies more
often had placeholder genres.

1. **Statuses differ:** no decision; both copies kept and flagged.
2. **Genre quality:** keep the copy with a real genre (not blank, "Other",
   "Undefined" or "Miscellaneous"). Decided 88 pairs.
3. **Venue completeness:** keep the copy whose venue has an address. Decided 6.
4. **Venue consolidation:** keep the copy at the venue ID with more events.
   Decided 112. This is a consistent retention rule only; it makes **no claim**
   that the larger venue ID's genre is more accurate.
5. **Tie-break:** alphabetically first event ID. Decided 9.

### Reason codes

| Action | Reason code | Rows | Meaning |
|---|---|---|---|
| EXCLUDE | `cross_listed_duplicate` | 213 | Same event under another venue ID (211 likely, plus Alexandra Kay and Colour Revolt confirmed in manual review) |
| EXCLUDE | `cross_listed_probable_duplicate` | 2 | Dwight Yoakam and Crankdat: probable duplicates, room differs |
| KEEP | `unresolved_status_conflict` | 4 | The War And Treaty and Dee Dee Bridgewater: both copies kept because their statuses differ |
| KEEP | `unresolved_manual_review` | 2 | Boy Golden: both copies kept pending manual review |

### How it was applied

`scripts/apply_dedup_decisions.py` was run a second time on the first pass's
output. The hard-coded check of 167 EXCLUDE rows became an option,
`--expected-exclude` (default still 167). No other logic changed.

```bash
.venv/bin/python scripts/apply_dedup_decisions.py \
    --input-dir data/processed/working_2026-11-10_222442/working_dedup_v2 \
    --decisions docs/dedup_decisions_pass2.csv --expected-exclude 215 \
    --output-dir data/processed/working_2026-11-10_222442/working_dedup_v3
```

`working_dedup_v2/` is unchanged (checksums verified before and after).

### Venues removed

37 venue IDs had no events left and were dropped. 25 have a kept counterpart
with the same name. 12 have a differently named counterpart; for 4 of these
the name suggests a room or space within the same complex:
- Ikeda Theatre → Mesa Arts Center;
- Resorts World Las Vegas Event Center → The Theatre at Resorts World;
- Williams Center → Williams Center Black Box;
- PETCO Park → Gallagher Square at Petco Park.

The full list is in `working_dedup_v3/apply_dedup_decisions.log`.

### Resulting dataset (`working_dedup_v3/`, verified 2026-11-18)

| File | Rows | Columns | Change |
|---|---|---|---|
| `working_events.csv` | 10,904 | 13 | 11,119 − 215 |
| `working_excluded_events.csv` | 539 | 5 | 324 + 215 |
| `working_venues.csv` | 969 | 9 | 1,006 − 37 |
| `working_acs1_2025_metros.csv` | 24 | 8 | unchanged (copied) |
| `working_cbp2023_metros.csv` | 72 | 8 | unchanged (copied) |
| `market_labels.csv` | 24 | 3 | unchanged (copied) |

Events by segment: Music 8,689, Sports 2,206, Miscellaneous 6, Undefined 3.
Most removals by market: New York 57, San Diego 23, Nashville 19, Chicago 19,
Phoenix 17, Las Vegas 14.

Checks (script log, "Problems: none", plus a separate check in Nathan's
session):
- no duplicate event IDs, and no event ID in both the events and excluded files;
- events + excluded = 11,443, the source event count;
- the events file is the input minus exactly the 215, rows otherwise unchanged;
- all 6 KEEP IDs are still in the events file;
- every event's venue exists, every venue has at least one event, and every
  venue's metro is one of the 24 markets;
- the remaining venue rows and the three copied files are identical to the input.

171 of the 539 excluded rows reference venues that are not in the venues file
(the 110 from the first pass, plus excluded copies whose venue ID was dropped).

### Limitations

- **Genre disagreements (70 pairs):** both copies had a real but different
  genre. The kept genre comes from the retention rule, not from a judgment of
  accuracy. Most common pairs:
  - Blues / Jazz: 24;
  - Alternative / Rock: 14;
  - Classical / Jazz: 7;
  - Metal / Rock: 5;
  - Latin / World: 3;
  - Classical / Rock: 3.

  Genre-mix results carry this uncertainty.
- **Placeholder genres:** 3 kept copies have a placeholder genre (both copies
  had one). Placeholder or blank genres overall went from 1,825 to 1,734.
- **Probable duplicates:** 2 removals (Dwight Yoakam, Crankdat) are probable,
  not certain.
- **Unresolved pairs:** 3 pairs keep both copies (two status conflicts and
  Boy Golden), so each may be counted twice.
- **Support acts:** 5 kept event names omit a support act that appears in the
  removed copy's name.
- **Remaining duplicate venue IDs:** some physical venues still have more than
  one venue ID where no event was cross-listed. The room-versus-venue question
  (separate IDs for rooms in one building) is not resolved.
- **Tier listings:** 33 event names match a tier, VIP or presale pattern
  ("VIP Tickets", "Club Seating", "Premium Seating", "VIP Tailgate",
  "Presale") and remain. Examples:
  - Washington Capitals VIP Tickets;
  - Paramount Theatre Club Seating;
  - UCLA Premium Seating;
  - Colts VIP Tailgate.
- **ZIP codes:** 3 venue ZIP codes have stray spaces (`' 32210'`, `'90731 '`,
  `'07506 '`).
- **Venue text:** leading or trailing spaces appear in 12 venue names,
  18 addresses and 2 cities.

## 2026-11-19: Genre exclusion

Decided by Nathan and Nick, relayed by Nick. The 9 events in
`working_dedup_v3` with a blank `genre_id` are excluded: 6 in Ticketmaster's
Miscellaneous segment and 3 in Undefined. Their `genre` is blank too, and no
other event lacks a `genre_id`. As a result, only the **Music** and **Sports**
segments remain, so the team's SEGMENT table will have 2 rows.

Decisions are recorded per event in `docs/genre_exclusion_decisions.csv`
(same five columns as the other decision files; 9 rows, all EXCLUDE,
reason `missing_genre_id`, no `duplicate_of_event_id`). The file was
generated from `working_dedup_v3/working_events.csv` (every row with a blank
`genre_id`), not typed by hand.

| Event ID | Segment | Date | Venue |
|---|---|---|---|
| `rZ7HnEZ1Af-UFK` | Miscellaneous | 2026-11-17 | The MET Church |
| `rZ7HnEZ1Af-UuN` | Miscellaneous | 2026-11-18 | CityChurch |
| `rZ7HnEZ1AfuU-0` | Miscellaneous | 2026-11-27 | Crescent Ballroom |
| `rZ7HnEZ1Af8aC7` | Miscellaneous | 2026-12-08 | Belly Up |
| `rZ7HnEZ1Af8Pjf` | Miscellaneous | 2026-12-31 | Valley Bar |
| `rZ7HnEZ1Af8zj7` | Miscellaneous | 2027-01-01 | THE ROOF + THE ROOM |
| `rZ7HnEZ1Af-pPN` | Undefined | 2026-11-15 | Brick and Mortar Music Hall |
| `rZ7HnEZ1A4Z88K` | Undefined | 2026-11-24 | Hollywood Improv (The Lab) |
| `rZ7HnEZ1Af8fr7` | Undefined | 2027-01-10 | Berlin |

By market: Phoenix 2, New York 2, Los Angeles 1, Houston 1, San Antonio 1,
San Francisco-Oakland 1, San Diego 1.

### How it was applied

`scripts/apply_dedup_decisions.py`, run a third time, on the second pass's
output (no script change). Nick's run:

```bash
python3 scripts/apply_dedup_decisions.py \
    --input-dir '../processed copy/working_dedup_v3' \
    --decisions docs/genre_exclusion_decisions.csv --expected-exclude 9 \
    --output-dir '../processed copy/working_dedup_v4'
```

`working_dedup_v3/` and the decisions file are unchanged (checksums verified
before and after).

### Venues removed

4 venues had no events left and were dropped:

| Venue ID | Venue |
|---|---|
| `rZ7HnEZ173bbP` | CityChurch |
| `rZ7HnEZ178sjP` | Hollywood Improv (The Lab) |
| `rZ7HnEZ17f7Gg` | THE ROOF + THE ROOM |
| `rZ7HnEZ17fxF4` | The MET Church |

The other 5 venues of excluded events keep other events.

### Resulting dataset (`working_dedup_v4/`, verified 2026-11-19)

| File | Rows | Columns | Change |
|---|---|---|---|
| `working_events.csv` | 10,895 | 13 | 10,904 − 9 |
| `working_excluded_events.csv` | 548 | 5 | 539 + 9 |
| `working_venues.csv` | 965 | 9 | 969 − 4 |
| `working_acs1_2025_metros.csv` | 24 | 8 | unchanged (copied) |
| `working_cbp2023_metros.csv` | 72 | 8 | unchanged (copied) |
| `market_labels.csv` | 24 | 3 | unchanged (copied) |

Events by segment: Music 8,689, Sports 2,206 (one `segment_id` each).

Checks (script log, "Problems: none", plus a separate check in Nick's
session):
- no duplicate event or venue IDs, and no event ID in both the events and
  excluded files;
- events + excluded = 11,443, the source event count;
- the events file is the input minus exactly the 9, rows otherwise unchanged;
  all 539 earlier excluded rows are preserved;
- every event's venue exists, and every venue has at least one event;
- every remaining event has a `genre_id` and a `genre`;
- the remaining venue rows and the three copied files are identical to the input.

175 of the 548 excluded rows reference venues that are not in the venues file
(the 171 from earlier passes, plus the 4 events at the dropped venues).

## 2026-11-19: Approved ERD design

Designed and approved by Nathan and Nick for Phase 2. Recorded verbatim as
supplied by Nick; this is a record of the team's own work.

- **Notation:** crow's-foot.
- **Built in:** Lucidchart, by Nathan and Nick.
- **Data source:** `working_dedup_v4`.

### Tables

1. **METRO_AREA**
   - PK: metro_area_geoid
   - Attributes: census_metro_name, market_label
2. **VENUE**
   - PK: venue_id
   - FK: metro_area_geoid → METRO_AREA
   - Attributes: venue_name, venue_address, venue_city, venue_state,
     venue_postal_code, venue_latitude, venue_longitude
3. **EVENT**
   - PK: event_id
   - FKs: venue_id → VENUE, genre_id → GENRE
   - Attributes: event_name, event_url, status, local_date, local_time,
     subgenre, ticketing_platform
   - segment_id, segment, and genre are not stored in EVENT.
4. **SEGMENT**
   - PK: segment_id
   - Attributes: segment (2 rows: Music, Sports)
5. **GENRE**
   - PK: genre_id
   - FK: segment_id → SEGMENT
   - Attributes: genre
6. **METRO_DEMOGRAPHICS**
   - PK and FK: metro_area_geoid → METRO_AREA
   - Attributes: population, population_moe, population_note,
     median_household_income, median_household_income_moe,
     median_household_income_note
   - geo_name not stored.
7. **INDUSTRY**
   - PK: naics_code
   - Attributes: naics_label
8. **METRO_INDUSTRY**
   - Composite PK: (metro_area_geoid, naics_code), both also FKs to
     METRO_AREA and INDUSTRY
   - Attributes: establishments, employees, employees_noise_flag, published,
     note

### Relationships and participation rules

1. METRO_AREA to VENUE: one-to-many. One metro can have zero or many venues.
   Every venue must belong to exactly one metro.
2. VENUE to EVENT: one-to-many. One venue can have zero or many events. Every
   event must belong to exactly one venue.
3. SEGMENT to GENRE: one-to-many. One segment can have zero or many genres.
   Every genre must belong to exactly one segment.
4. GENRE to EVENT: one-to-many. One genre can have zero or many events. Every
   event must belong to exactly one genre after excluding the nine events with
   missing genres.
5. METRO_AREA to METRO_DEMOGRAPHICS: one-to-one. One metro can have zero or
   one demographics record. Every demographics record must belong to exactly
   one metro.
6. METRO_AREA to METRO_INDUSTRY: one-to-many. One metro can have zero or many
   metro-industry records. Every metro-industry record must belong to exactly
   one metro.
7. INDUSTRY to METRO_INDUSTRY: one-to-many. One industry can have zero or many
   metro-industry records. Every metro-industry record must belong to exactly
   one industry.

## 2026-11-20: ERD revisions

Revisions by Nathan and Nick to the "2026-11-19: Approved ERD design" above,
recorded as supplied by Nick. The 2026-11-19 section is kept unchanged.

- **Renamed:** METRO_DEMOGRAPHICS → METRO_DEMOGRAPHIC (lecture: entity names
  are singular).
- **Dropped from METRO_DEMOGRAPHIC** (source `working_acs1_2025_metros.csv`):
  - geo_name: duplicate of census_metro_name in METRO_AREA (data redundancy);
  - population_moe, population_note, median_household_income_moe,
    median_household_income_note.
  - Final: metro_area_geoid (PK, FK), population, median_household_income.
- **Dropped from METRO_INDUSTRY** (source `working_cbp2023_metros.csv`): note,
  employees_noise_flag, published.
  - Final: metro_area_geoid (PK, FK), naics_code (PK, FK), establishments,
    employees.
- **Columns kept in the CSVs that are not stored in the table of the same
  file:**
  - `working_cbp2023_metros.csv` keeps naics_label because it is the source
    for the INDUSTRY table.
  - `working_events.csv` keeps segment_id, segment and genre because they
    are the source for the SEGMENT and GENRE tables.
- **Model now has 36 attributes.**
- **Relationship names:**
  - METRO_AREA contains VENUE;
  - VENUE hosts EVENT;
  - SEGMENT contains GENRE;
  - GENRE classifies EVENT;
  - METRO_AREA reports METRO_DEMOGRAPHIC;
  - METRO_AREA supports METRO_INDUSTRY;
  - INDUSTRY categorizes METRO_INDUSTRY.
- **Required (bold):** all PKs and FKs, plus segment, genre, event_name,
  local_date, status, venue_name, census_metro_name, naics_label,
  population, median_household_income. All other attributes are optional
  (plain).
- **Line style:** solid = identifying (3), dashed = non-identifying (4).
- **Diagram:** built in draw.io and exported to PDF from draw.io.

### Columns removed from the working CSVs (`working_dedup_v5/`, verified 2026-11-21)

The 8 dropped columns were also removed from the working CSVs by the new
`scripts/drop_erd_unused_columns.py`, run by Nick on 2026-11-21:

```bash
python3 scripts/drop_erd_unused_columns.py \
    --input-dir '../processed copy/working_dedup_v4' \
    --output-dir '../processed copy/working_dedup_v5'
```

- Reads everything as text and keeps all rows and the order of the remaining
  columns. The other 4 files are copied byte for byte.
- Stops with an error if any of the 8 columns is missing, and never writes
  to its input folder.
- Writes `drop_erd_unused_columns.log` in the output folder. The run ended
  with "Problems: none".

Verification results:

| File | v4 | v5 |
|---|---|---|
| `working_acs1_2025_metros.csv` | 24 rows, 8 columns | 24 rows, 3 columns: metro_area_geoid, population, median_household_income |
| `working_cbp2023_metros.csv` | 72 rows, 8 columns | 72 rows, 5 columns: metro_area_geoid, naics_code, naics_label, establishments, employees |
| `working_events.csv` | 10,895 rows | byte-identical |
| `working_venues.csv` | 965 rows | byte-identical |
| `working_excluded_events.csv` | 548 rows | byte-identical |
| `market_labels.csv` | 24 rows | byte-identical |

- Every remaining ACS and CBP value is identical to v4. The dropped columns
  are gone, and the remaining columns keep their order.
- GEOIDs keep their leading zeros (all 5 characters).
- geo_name was identical to census_metro_name in `market_labels.csv` for
  all 24 metros, so dropping it loses no information.
- The El Paso 711320 CBP row (metro 21340) is still present, with blank
  establishments and employees. It is the only CBP row with blanks.
- On Nick's machine, `Archive`, `working_dedup_v2`, `working_dedup_v3` and
  `working_dedup_v4` are unchanged (27 files; SHA-256 checksums match before
  and after). The original source CSVs are only on Nathan's machine and
  were not read by the script.

## Open items

- **Business questions:** not yet written. To be added here verbatim by
  Nathan and Nick, with the date approved.
- **Data issues noted but not used:**
  - 98 events have an on-sale date of `9999-12-31` (Ticketmaster's
    "unknown" value), and 2 have 2009 on-sale dates. On-sale dates are not
    in the working scope.
  - Some Ticketmaster market names are malformed in the raw data (e.g.
    `' DC and Maryland"'`). Markets are not in the working scope.
- **Import note:** 62 working event names contain double quotes. This
  matters for the MySQL import.
