# Resale Price Source Options (researched 2026-11-02)

SeatGeek's public API has no prices or listings, so it can't be our resale source.
This compares the alternatives we found. Facts come from each provider's own
pages, which are linked. "Realistic by Dec 9" is our judgment, not something
the providers state.

## Summary

| Source | Official API | Resale prices | History | Approval needed | Realistic by Dec 9 | Storage / academic use |
|---|---|---|---|---|---|---|
| **SeatData.io** | Yes (REST + Python SDK) | Yes: per-event **get-in (min), average, median** listing price, plus per-zone; individual sales | **Yes**: stats time series per event; sales since Feb 2021 | **No**, self-serve signup | **Yes** | License explicitly permits academic research with attribution; perpetual retention of data you downloaded |
| StubHub | Yes (Catalog, Inventory, Sales APIs) | Catalog `Event` has **`min_ticket_price`** only | No: current value only, so you'd have to poll daily | Yes: email `affiliates@stubhub.com` (Partnerize affiliate) or `api.support@stubhub.com` (sellers); they say they're handling "high volumes of requests" | Unlikely | Affiliate terms only; nothing on research |
| SeatGeek | Yes (Platform API) | No (per your finding) | n/a | Portal login; access questions go to `tech-architecture@seatgeek.com` | n/a | API Terms forbid users who "systematically download and/or store" API content |
| Ticket Evolution | Yes (v9, signed requests) | Yes, broker inventory | Current only | Yes: only white-label affiliates, partners or brokers | No | Commercial reseller terms |
| TickPick | No public API found | — | — | — | No | — |
| Vivid Seats | No public API found (affiliate links only) | — | — | Affiliate approval | No | — |
| TicketNetwork | Inventory feed / "Mercury Web Services" for affiliates | Inventory for resale | Not documented publicly | Yes, affiliate networks | No | Affiliate terms |
| Ticketmaster Inventory Status | Yes | All-in min/max of *primary* available inventory (plus a resale *status*) | Current only, hourly | Yes: authorized clients only | Uncertain | Ticketmaster ToS limits storage |
| Scraped datasets (Rebrowser, Apify scrapers) | Not official | Yes | Some | Purchase | Possible | **Avoid**: built by scraping sites whose terms forbid it |

## SeatData.io in detail

**What it is.** A commercial data service that records listings and sales on two
resale marketplaces. Every event has a StubHub ID (`sh_event_id`) and a Vivid
Seats ID (`vs_event_id`), and sales rows carry `source = sh` or `vs`.

**Endpoints that matter for us** (from the API reference):
- `GET /v1/events/search`: free. Event metadata with normalized venue, lat/lng
  and performer. Use it to find events and their IDs.
- `GET /v1/events/{event_id}/stats`: paid, **1 pull per event**. Returns the
  event's **whole snapshot history** (filterable by `start_date`/`end_date`).
  Each snapshot has `total_listings_active`, `avg_price`, `median_price`,
  `get_in` (lowest price), `get_in_qty2plus`, and the same per zone. Re-asking
  for an event costs nothing unless a new snapshot exists. The dataset page
  says snapshots are "currently recorded three times a day".
- `GET /v1/events/{event_id}/sales`: individual sales (price, quantity,
  source, timestamp).

**Why it changes our plan.** Each stats request returns the full time series,
so we may not need our own daily resale collection from Nov 3 to Dec 7. We
could pull the history for each matched event in one batch near the end. That
would also cover the days that have already passed.

**Pricing** (from seatdata.io/pricing):
- Pay-as-you-go: $0.04 per request, no monthly fee.
- API tiers:
  - Lite: $19/mo for 750 requests.
  - Growth: $149/mo for 8,000.
  - Scale: $399/mo for 33,000.
- The web portal Basic plan ($19/mo, 3-day free trial) lists "College students
  or professors". That plan covers the web portal, not the API.

**Rough cost estimate (our assumption).** The 2-city, 5-day test had 336
Ticketmaster events. Scaling to 10 cities over Nov 3 – Jan 31 could mean on the
order of 25,000–30,000 events. That's too many to pull for every event on a
student budget. SeatData will also track only events with resale activity,
which is far fewer. Searching is free, so we can measure coverage first. A
project limited to sports plus large concerts, or a sample, could fit within
750–8,000 pulls.

**License** (seatdata.io/data-license, updated Jan 1, 2026):
- Permitted: "Academic research (subject to attribution requirements)", and
  publishing reports with aggregated data or insights.
- Attribution for academic work: "SeatData.io. Event Ticket Market Data.
  https://seatdata.io".
- Retention: data obtained during a subscription may be kept and used
  "perpetually".
- Prohibited: redistributing raw data, including "Sharing Data files, exports,
  or downloads with third parties" and "Publishing Raw Data on websites,
  databases, or platforms accessible to others".

  For us this means: never commit SeatData files to GitHub (`data/` is already
  git-ignored), and ask SeatData whether a two-person student team can share
  one account's data. Aggregated tables and charts in the final report are fine.

**Caveats to state in the report.**
- The data is "observational" and provided "AS IS". SeatData warns that missing
  sale prices may be filled with a listing's last known price.
- Listing prices aren't confirmed as fee-inclusive. In sales data, StubHub rows
  have `all_in_price = null`, while Vivid Seats rows have one "when shown".
  We'd need to check which basis `avg_price`/`median_price` use.
- SeatData collects by observing the marketplaces; it is not a StubHub or
  Vivid Seats partner feed. Say so in the methodology section.

## Sources

- SeatGeek API Terms: https://seatgeek.com/api-terms · Developer portal: https://developer.seatgeek.com/
- StubHub developer announcement: https://developer.stubhub.com/blog/2022/05/31/migrating-to-new-api · Catalog API: https://developer.stubhub.com/api-reference/catalog/
- Ticket Evolution access: https://ticketevolution.atlassian.net/wiki/spaces/API/pages/342229112
- SeatData: https://seatdata.io/pricing/ · https://docs.seatdata.io/docs/api/getting-started/ · https://docs.seatdata.io/docs/api/reference/v1/getEventStats/ · https://docs.seatdata.io/docs/sales-data-collection-methodology/ · https://seatdata.io/data-license/
- Vivid Seats affiliate listing: https://www.flexoffers.com/affiliate-programs/vivid-seats-affiliate-program/
- TicketNetwork affiliate listing: https://www.travelpayouts.com/en/offers/ticketnetwork-affiliate-program
- Rebrowser datasets: https://github.com/rebrowser/stubhub-dataset
- Ticketmaster Inventory Status: https://developer.ticketmaster.com/products-and-docs/apis/inventory-status/
