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

## 2026-11-21: Final ERD check

Final check of the ERD by Nathan and Nick, recorded as supplied by Nick.
Facts verified against `../processed copy/working_dedup_v5` on 2026-11-21.
The approved eight-table design is unchanged.

- **market_label: optional → required.** market_label has 24 unique,
  nonblank values in `market_labels.csv`, so it is a candidate key alongside
  census_metro_name. Required attributes are now the 2026-11-20 list plus
  market_label.
- **ZIP and city (no change):** in `working_venues.csv`, 10 ZIP codes map to
  more than one venue_city as written, and 9 after trimming whitespace.
  ZIP 89109 has both "Las Vegas" and "Las Vegas " (trailing space). The 9
  remaining ZIPs and their city names:

  | ZIP | City names |
  |---|---|
  | 02035 | Foxboro / Foxborough |
  | 02134 | Allston / Boston |
  | 10036 | New York / New York City |
  | 11003 | Belmont Park / Elmont |
  | 11367 | Flushing / Queens |
  | 11378 | Maspeth / Queens |
  | 37115 | Madison / Nashville |
  | 85253 | Paradise Valley / Scottsdale |
  | 90028 | Hollywood / Los Angeles |

  Most are neighborhood or borough naming variants, so ZIP does not
  determine city in this data. Address fields stay together in VENUE.
  - **For the Phase 3 import:** two venue_city values have a trailing
    space, "Las Vegas " (ZIP 89109) and "Brooklyn " (ZIP 11216). Only "Las
    Vegas " affects the ZIP count, because ZIP 11216 has no other city name.
- **event_url (no change):** 10,869 distinct values across 10,895 events. 4
  URLs are shared by 30 events (groups of 2, 2, 2 and 24), each group with
  the same event name on different dates. event_url is not a key.
- **Diagram:** the legend and data sources box were removed to match the
  professor's ERD examples. Source years (2025 ACS, 2023 CBP) remain
  documented in `docs/data_sources.md` and this file.

## 2026-11-27: Phase 3 build decisions

Decisions for building and loading the MySQL database. The ERD design above
is final and is not revisited here. Each decision was reviewed one at a time
(options and a recommendation, then approval). Approved by Nathan; Nick to
confirm.

### Decision 1: database name and character set

- **Decision:** the database is named `ticket_market_analytics`, with
  character set `utf8mb4` written explicitly in `CREATE DATABASE`.
- **Approved:** Nathan, 2026-11-27.
- **Options considered for the name:** `TicketMarketAnalytics`,
  `ticketmarketanalytics`, `ticket_market_analytics`.
- **Reason (from the options reviewed):**
  - lowercase snake_case behaves the same on any server, whether or not it
    treats names as case-sensitive, and matches the snake_case column
    names;
  - none of the 6 existing databases on this server uses the name;
  - `utf8mb4` is needed because 268 event names and 3 venue names in
    `working_dedup_v5` contain non-ASCII characters; it is written
    explicitly so a shared `.sql` file also works on a server whose default
    differs.

### Decision 2: collation for the Ticketmaster ID columns

- **Decision:** the four Ticketmaster ID columns use the case-sensitive
  collation `utf8mb4_bin`. Every other text column keeps the database default
  (`utf8mb4_0900_ai_ci`).
- **Approved:** Nathan, 2026-11-27 (Option A below).
- **Options considered:**
  - **A (chosen):** `utf8mb4_bin` on the four ID columns only;
  - B: make the whole database case-sensitive;
  - C: leave the default (not workable, see the test results).
- **Reason (from the options reviewed):**
  - the server default `utf8mb4_0900_ai_ci` ignores letter case, but some
    Ticketmaster IDs differ from another ID only in case. In
    `working_dedup_v5`: 6 of 41 `genre_id` values (3 pairs, e.g.
    `KnvZfZ7vAde` Basketball and `KnvZfZ7vAdE` Football), 18 of 965
    `venue_id` values (9 pairs) and 565 of 10,895 `event_id` values (280
    groups); `segment_id` has none;
  - the problem is specific to IDs, so only IDs get the stricter rule and
    normal text behavior is unchanged;
  - `utf8mb4_bin` works on every MySQL version (`utf8mb4_0900_bin` and
    `utf8mb4_0900_as_cs` need 8.0.17 or later), and the IDs contain only
    letters, digits, `-` and `_`, with no spaces.
- **Columns and matching rule.** Both sides of every foreign key must use the
  same character set and collation. MySQL rejects a mismatch with error
  3780 (see the test results).

  | Column | Role | Collation |
  |---|---|---|
  | `segment.segment_id` | PK | `utf8mb4_bin` |
  | `genre.genre_id` | PK | `utf8mb4_bin` |
  | `genre.segment_id` | FK to `segment.segment_id` | `utf8mb4_bin` |
  | `venue.venue_id` | PK | `utf8mb4_bin` |
  | `event.event_id` | PK | `utf8mb4_bin` |
  | `event.venue_id` | FK to `venue.venue_id` | `utf8mb4_bin` |
  | `event.genre_id` | FK to `genre.genre_id` | `utf8mb4_bin` |

  The non-Ticketmaster keys `metro_area_geoid` and `naics_code` contain only
  digits and keep the database default on both sides of their foreign keys.
  Any staging table used for loading must declare the same collation on
  the four ID columns. (Table names are the lowercase names settled in
  Decision 3.)
- **Effect on analysis:** with the default collation,
  `COUNT(DISTINCT event_name)` merges names that differ only in case or
  accents (6,984 distinct names, against 7,030 under exact comparison).
  Event-variety results should state which comparison was used;
  `COUNT(DISTINCT BINARY event_name)` gives exact counts.
- **Test results:** recorded in `docs/database_build_log.md`
  ("Collation test on a throwaway server"). That test did not touch the
  project database.

### Decision 3: column types, lengths, NULL rules and table names

- **Decision:** the types, lengths and NULL rules in the table below, with
  lowercase snake_case table names. Latitude and longitude types are settled
  in Decision 4.
- **Approved:** Nathan, 2026-11-27.
- **Reason (from the options reviewed):**
  - NULL rules follow the finalized ERD exactly: required (bold) attributes
    are `NOT NULL`, optional (plain) attributes allow NULL. Checked against
    the ERD file: 36 columns, 24 required, 0 differences (the diagram file
    was read with `market_label` made required, as recorded in "2026-11-21:
    Final ERD check");
  - lengths are the longest value in `working_dedup_v5` plus headroom; no
    `TEXT` types are needed;
  - `CHAR` where the length never varies (`genre_id` 11, `segment_id` 18,
    `metro_area_geoid` 5, `venue_state` 2, ZIP 5), `VARCHAR` where it does
    (`event_id` 13–21, `venue_id` 10–13, `naics_code` 4 or 6);
  - `status` is `VARCHAR(12)`: it matches the ERD, and `ENUM` or `CHECK`
    constraints would add rules the ERD does not show;
  - whole-number measures (`population`, income, establishments,
    employees) are `INT`: every source value is a whole number (stored as
    e.g. `2620945.0`) and the ranges fit easily;
  - primary keys are the source IDs (no auto-numbering), as in the ERD;
  - table names are lowercase snake_case, consistent with Decision 1 and the
    column names. Each table is the ERD entity of the same name in lowercase
    (e.g. `metro_area` for METRO_AREA).
- **Alternatives considered:** keeping uppercase table names to match the ERD
  exactly; `ENUM` for `status`.

| Table | Column | Type | NULL? | Evidence in `working_dedup_v5` |
|---|---|---|---|---|
| `segment` | `segment_id` (PK) | `CHAR(18)` | no | always 18 characters |
| | `segment` | `VARCHAR(20)` | no | max 6 |
| `genre` | `genre_id` (PK) | `CHAR(11)` | no | always 11 |
| | `segment_id` (FK) | `CHAR(18)` | no | |
| | `genre` | `VARCHAR(30)` | no | max 18 |
| `event` | `event_id` (PK) | `VARCHAR(25)` | no | 13–21 |
| | `venue_id` (FK) | `VARCHAR(15)` | no | |
| | `genre_id` (FK) | `CHAR(11)` | no | |
| | `event_name` | `VARCHAR(400)` | no | max 347 |
| | `event_url` | `VARCHAR(255)` | yes | max 224 |
| | `status` | `VARCHAR(12)` | no | max 11, 4 values |
| | `local_date` | `DATE` | no | 2026-11-12 to 2027-01-31 |
| | `local_time` | `TIME` | yes | 245 blank |
| | `subgenre` | `VARCHAR(30)` | yes | max 18; 8,693 blank |
| | `ticketing_platform` | `VARCHAR(40)` | yes | max 29 |
| `venue` | `venue_id` (PK) | `VARCHAR(15)` | no | 10–13 |
| | `metro_area_geoid` (FK) | `CHAR(5)` | no | always 5 digits |
| | `venue_name` | `VARCHAR(80)` | no | max 64 |
| | `venue_address` | `VARCHAR(60)` | yes | max 41; 16 blank |
| | `venue_city` | `VARCHAR(40)` | yes | max 17 |
| | `venue_state` | `CHAR(2)` | yes | always 2 |
| | `venue_postal_code` | `CHAR(5)` | yes | always 5 digits after trimming |
| | `venue_latitude`, `venue_longitude` | `DECIMAL(18,15)` (Decision 4) | yes | up to 15 and 14 decimals |
| `metro_area` | `metro_area_geoid` (PK) | `CHAR(5)` | no | |
| | `census_metro_name` | `VARCHAR(80)` | no, **UNIQUE** | max 57 |
| | `market_label` | `VARCHAR(30)` | no, **UNIQUE** | max 21 |
| `metro_demographic` | `metro_area_geoid` (PK, FK) | `CHAR(5)` | no | |
| | `population` | `INT` | no | 880,884 to 20,112,448 |
| | `median_household_income` | `INT` | no | 61,596 to 166,364 |
| `industry` | `naics_code` (PK) | `VARCHAR(6)` | no | 4 or 6 digits |
| | `naics_label` | `VARCHAR(100)` | no | max 75 |
| `metro_industry` | `metro_area_geoid` (PK, FK) | `CHAR(5)` | no | |
| | `naics_code` (PK, FK) | `VARCHAR(6)` | no | |
| | `establishments` | `INT` | yes | 7 to 452; 1 blank (El Paso) |
| | `employees` | `INT` | yes | 40 to 20,964; 1 blank (El Paso) |

- **UNIQUE constraints on `metro_area`.** The ERD records `market_label` and
  `census_metro_name` as candidate keys alongside the primary key
  `metro_area_geoid` ("2026-11-21: Final ERD check" and the Oral Defense
  Study Points in `CLAUDE.md`). A candidate key must be unique and non-null,
  so both columns get `UNIQUE` and `NOT NULL` in the database. Checked in the
  data: 24 rows, 24 distinct values and 0 blanks for each, and still 24
  distinct values under the case- and accent-insensitive default collation,
  so the constraint cannot reject the load. Other columns that happen to be
  unique (`genre.genre`, `segment.segment`, `industry.naics_label`) are not
  declared candidate keys in the ERD decisions, so they get no `UNIQUE`
  constraint.
- **ZIP codes and `CHAR(5)`.** 3 ZIP codes in the file have stray spaces. A
  test showed that loading them untrimmed into `CHAR(5)` with `LOAD DATA
  LOCAL` truncates `' 32210'` to `' 3221'` with a warning rather than an
  error (see the build log). The ZIP codes therefore have to be trimmed
  while loading (Decision 6).
- **Data dictionary tool.** `scripts/extract_data_dictionary.py` now also
  reports each text column's collation, so the data dictionary shows the
  `utf8mb4_bin` ID columns (Nathan approved the change, 2026-11-27).

### Decision 4: latitude and longitude type

- **Decision:** `venue_latitude` and `venue_longitude` are `DECIMAL(18,15)`
  and stay nullable, as specified in the ERD.
- **Approved:** Nathan, 2026-11-27.
- **Options considered:** `DECIMAL(10,7)`, `DECIMAL(18,15)`, `DOUBLE`/`FLOAT`.
- **Reason (as stated by Nathan):** preserve the original coordinate values
  and avoid unnecessary rounding warnings.
- **Supporting facts** (`working_dedup_v5`, tested on a throwaway server; see
  the build log):
  - no coordinate has more than 15 decimals (latitude) or 14 (longitude), so
    `DECIMAL(18,15)` holds every value exactly, with room for 3 whole digits;
  - `DECIMAL(10,7)` would round 102 latitudes and 92 longitudes (by at most
    about 0.56 cm) and show 194 warnings on every load, which could hide a
    real warning;
  - `DECIMAL(18,15)` loaded all 965 rows with 0 warnings and values identical
    to the file, so the imported coordinates do not differ from the source;
  - no analysis theme uses coordinates, so precision has no effect on the
    business questions.

### Decision 5: filling the derived tables with staging tables

- **Decision:** `segment`, `genre` and `industry` are filled from staging
  tables. Each source CSV is loaded as-is into a staging table, checked, and
  then copied into the final tables with `INSERT ... SELECT`. The same staging
  tables also feed `event`, `venue`, `metro_area`, `metro_demographic` and
  `metro_industry`, so every cleaning step happens in SQL.
- **Approved:** Nathan, 2026-11-27.
- **Rules set by Nathan:**
  1. the `working_dedup_v5` CSVs stay unchanged (they are only read);
  2. the staging data is validated before it is transferred;
  3. the staging tables are dropped only after all final checks pass.
- **Options considered:** (A, chosen) staging tables; (B) load the large file
  directly into each table and let duplicates be skipped; (C) generate small
  derived CSV files first; (D) type the rows by hand.
- **Reason (from the options reviewed):**
  - it shows the normalization in SQL, which is how the report describes the
    conversion of the dataset into tables;
  - a dependency check can be run before anything is inserted (tested: 0
    violations for `genre_id` to `segment_id` and `genre`, `segment_id` to
    `segment`, and `naics_code` to `naics_label`; 2, 41 and 3 rows with 0
    warnings);
  - option B reached 41 genres but raised 10,854 warnings, which would hide a
    real one, and option C adds a script and derived files to document.
- **Staging design:**
  - tables `stg_event`, `stg_venue`, `stg_market_label`, `stg_acs` and
    `stg_cbp` (`working_excluded_events.csv` is not loaded);
  - every column is `VARCHAR` so blanks and values such as `2620945.0` arrive
    exactly as written; no keys or constraints;
  - the four Ticketmaster ID columns use `utf8mb4_bin` (with the default
    collation `COUNT(DISTINCT genre_id)` was 38 instead of 41);
  - loaded with `LOAD DATA LOCAL INFILE ... CHARACTER SET utf8mb4`.
- **Validation before transfer (all must pass):**
  - row counts equal the source: 10,895 events, 965 venues, 24 market labels,
    24 ACS rows, 72 CBP rows;
  - 0 warnings after each load (`SHOW WARNINGS`);
  - the three dependency checks above return 0 violations;
  - the key columns are unique under case-sensitive comparison (`event_id`,
    `venue_id`, `metro_area_geoid` in each metro file, and `metro_area_geoid`
    with `naics_code` in `stg_cbp`);
  - no blanks in any column that will be `NOT NULL`;
  - every `venue_id` in `stg_event` exists in `stg_venue`, and every
    `metro_area_geoid` in the venue, ACS and CBP files exists in
    `stg_market_label`;
  - the counts of stray spaces and blanks match the expected numbers in
    Decision 6;
  - the ACS values are whole numbers before they are cast (see Decision 6).
- **Transfer order (parents first):** `metro_area`, `segment`, `industry`,
  then `venue`, `genre`, `metro_demographic`, `metro_industry`, then `event`.
- **Final checks before the staging tables are dropped (all must pass):**
  - table row counts are 24, 2, 3, 965, 41, 24, 72 and 10,895;
  - no orphan rows for any foreign key;
  - the number of NULLs in each nullable column matches the staging counts;
  - spot values agree with the source files (e.g. Austin population 2,620,945);
  - the data dictionary extract shows the types, `NOT NULL` rules and
    `utf8mb4_bin` collations from Decisions 2 and 3.
- **Cleanup:** the `stg_` tables are dropped only after those checks pass,
  and the exact `DROP` statements are logged in
  `docs/database_build_log.md`. The finished database has exactly the 8 ERD
  tables.

### Decision 6: cleaning rules applied when copying from staging

- **Decision:** the rules below are applied in the `INSERT ... SELECT`
  statements that copy staging data into the final tables.
- **Approved:** Nathan, 2026-11-27, with one requirement added by Nathan:
  the ACS values are validated as whole numbers before they are cast.
- **Rules:**
  1. **Trim edge whitespace** on the four venue text columns only
     (`venue_name`, `venue_address`, `venue_city`, `venue_postal_code`),
     with `REGEXP_REPLACE(col, '^[[:space:]]+|[[:space:]]+$', '')`. Expected
     values changed: 12 names, 17 addresses, 2 cities, 3 ZIP codes. Plain
     `TRIM()` would change only 11 names: venue `rZ7HnEZ17rfqV` ends in a
     non-breaking space that `TRIM()` does not remove. Every other column has
     no edge whitespace (checked in staging) and is copied unchanged. Event
     names are not altered; 16 contain a non-breaking space inside the name.
  2. **Blank cells become NULL.** Every one of the 12 nullable columns is
     wrapped in `NULLIF(col, '')`: `event_url`, `local_time`, `subgenre`,
     `ticketing_platform`, `venue_address`, `venue_city`, `venue_state`,
     `venue_postal_code`, `venue_latitude`, `venue_longitude`,
     `establishments`, `employees`. Expected NULLs: `local_time` 245,
     `subgenre` 8,693, `venue_address` 16, `establishments` 1 and
     `employees` 1 (El Paso); the other seven nullable columns 0.
  3. **ACS numbers: validate, then cast.** Before the transfer, in
     `stg_acs`: every `population` and `median_household_income` value is
     digits followed by `.0` (expected 24 of 24 for each), none is blank,
     and the largest is below the `INT` limit of 2,147,483,647 (largest is
     20,112,448). Only if that passes, the values are copied with
     `CAST(col AS DECIMAL(12,0))`. The CBP counts (`establishments`,
     `employees`) must be digits only when not blank (71 of 71 each) and are
     copied with `NULLIF(col, '')`.
  4. **Dates and times.** `local_date` (`YYYY-MM-DD` text) goes straight into
     the `DATE` column; `local_time` is `CAST(NULLIF(local_time, '') AS
     TIME)`.
  5. **Load settings.** `LOAD DATA LOCAL INFILE ... CHARACTER SET utf8mb4
     FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY
     '\n' IGNORE 1 LINES`, with the client connected using
     `--default-character-set=utf8mb4`. Tested: 62 names with double quotes,
     558 with commas, 268 with non-ASCII characters and 68 with ` | `
     arrived intact; the longest name is 347 characters.
  6. **Not cleaned (kept as documented limitations):** city spelling
     variants (e.g. Foxboro/Foxborough), venue IDs that stand for the same
     physical venue (explained below), placeholder genres, and the
     non-breaking spaces inside event names.
- **Reason (from the tests on a throwaway server; see the build log):**
  - `TRIM()` leaves one value untrimmed;
  - a blank `local_time` copied into a `TIME` column without `NULLIF` is
    stored as `00:00:00` with no error and no warning (245 events);
  - a blank copied into an `INT` or `DECIMAL` column fails with error 1366;
  - a blank copied into a `VARCHAR` column becomes an empty string, not NULL
    (`COUNT(subgenre)` was 10,895 instead of 2,202);
  - `'2620945.0'` converts to `INT` with 0 warnings; the whole-number check
    makes sure the cast cannot hide a fractional value.
- **Venue IDs that stand for the same physical venue.** `venue_id` is unique
  (965 distinct values), so the key is sound. The limitation is that Ticketmaster
  can give one physical venue more than one venue ID, often one per ticketing
  platform. In `working_dedup_v5`: 126 venue IDs share a name with another ID
  (62 names, 58 of them within one city), 123 share an address and city, and
  259 share exact coordinates (some are different rooms in one building).
  Example: Blue Note Jazz Club, New York has `KovZpZAkJtvA` (1 event,
  ticketmaster.com) and `rZ7HnEZaASU` (140 events, ticketweb.com). Effect:
  counting venue IDs overstates the number of physical venues, and a venue's
  events can be split across IDs. The IDs are not merged: the ERD and the
  cleaning are final. Venue-concentration results should say "venue IDs" and
  state this limitation.

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
