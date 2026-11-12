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
