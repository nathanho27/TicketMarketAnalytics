# Ticketmaster Pricing Investigation (2026-11-02)

Why do so many Ticketmaster events lack `priceRanges`, is there another public
source of face value, and what should `priceRanges` be called?

Sources: our raw file `data/raw/ticketmaster/ticketmaster_2026-11-02_203943.json`
(347 events, LA + NYC, Nov 6–10) and the Ticketmaster Developer Portal pages
listed at the end. No extra API requests were made.

## 1. Why events with `allInclusivePricing` have no `priceRanges`

**What the raw data shows.** The sample splits cleanly into two groups:

| | Has `ticketing.allInclusivePricing` (184) | No `ticketing` field (163) |
|---|---|---|
| `priceRanges` present | **0** | **160** |
| Event URL host | ticketmaster.com 175, ticketweb.com 8, atgtickets.com 1 | **ticketweb.com 162**, universe.com 1 |
| Event ID prefix | `vv`, `Z7`, `k7`, `G5`, … | `rZ` (162 of 163) |
| `seatmap`, `products`, `ticketLimit`, `outlets` | present on many | never present |
| `allInclusivePricing.enabled` | true 175, **false 9** | n/a |

The 9 events with `enabled: false` also have no price range. So it isn't the
all-in setting itself that removes prices. The field marks events on
Ticketmaster's **main ticketing platform**, and in our sample none of those
events carries `priceRanges`. Nearly every priced event comes from **TicketWeb**,
Ticketmaster's self-service platform for small venues. That's why the priced
events are almost all jazz clubs and small rooms, and why every arena, stadium,
sports and Live Nation event is unpriced.

**What the documentation says.**
- The Partner API's *All In Price* section says: "Effective May 12, 2025 … In the
  Discovery, Top Picks, and Availability APIs, the allInclusivePricing field is
  set to true for all events in all U.S. states." This follows the FTC rule
  requiring total ticket prices, including mandatory fees, to be shown up front.
- **No public page says that `priceRanges` is removed for these events.** The
  Discovery API reference describes `priceRanges` only as "Price ranges of this
  event". The Discovery release notes URL returns a 404.
- Our data doesn't fully match the documented rule. 9 U.S. events have the flag
  set to false, and the 163 TicketWeb events have no flag at all.

**Conclusion.** Main-platform Ticketmaster events don't return `priceRanges`
in our sample. A likely explanation, which we can't confirm from documentation,
is that Ticketmaster stopped publishing static price ranges once U.S. prices had
to be shown all-in. Ticketmaster now provides prices only through APIs that
reflect live, fee-inclusive inventory (below). Treat this as a hypothesis, not
a documented fact.

## 2. Other documented endpoints with pricing

| API | Pricing it documents | Access | Useful for us? |
|---|---|---|---|
| **Discovery API** (what we use) | `priceRanges` (min/max/currency/type), undefined beyond that | Open: any registered key | Already collected |
| **Inventory Status API** | Min/max price of *currently available* primary inventory; "all-in price per ticket, with some exclusions" (some taxes/order fees); refreshed at most hourly; max capped at $2,000 (`listingsExtendBeyondMax`). Supports Ticketmaster, TMR, TicketWeb sources, US included. Takes universal event IDs. | "Access is provided to authorized clients only." Request via `devportalinquiry@ticketmaster.com` | **Best fit**, if Ticketmaster grants access |
| **Top Picks API** | Seat-level offers with `faceValue`, fee `charges`, and `totalPrice` (= face value + fees under all-in pricing) | Key "provided … from Ticketmaster" for Open Inventory affiliate partners; sorting by face value only for "select apikeys" | Unlikely to be granted; per-seat, not per-event |
| **Partner API** (Availability, Reserve) | `faceValue` plus a separate breakdown of fees and taxes | "Not an open API. It is restricted to companies with … official distribution relationships." | No |
| **Commerce API** (Event Offers) | Listed in the portal navigation | Both doc URLs return 404; FAQ says Partner Commerce API "is typically restricted to a select few business partners" | No |
| **Discovery Feed** | Same content as Discovery, plus a `SOURCE` field | "For our approved partners" | No pricing gain |
| **International Discovery API** (Event Prices) | Has a prices endpoint | Non-U.S. markets; being merged into Discovery | No (U.S. study) |

The only publicly documented route to prices for main-platform events is the
**Inventory Status API**, and it requires Ticketmaster's approval. Even with
access, it reports the price range of tickets **still available** when we ask,
including fees. That is not the original face value.

## 3. Is `priceRanges` "face value"?

No, not without qualification.

- Ticketmaster defines face value narrowly, in the Partner API fee table: "The
  established price or base ticket price". Face-value tax, facility fees and
  service fees are listed as separate charges.
- The Discovery API never says whether `priceRanges` includes fees, whether it
  covers sold-out tiers, or when it was last updated.
- In our data, only 4 of 145 usable minimum prices are whole-dollar amounts
  (e.g. $18.80, $38.10, $62.15, $30.25). Base prices are usually round numbers,
  so these look like fees are included. That's an inference, not confirmed.
- 15 events report $0–$0 on paid shows. 68% report min = max, so it's a single
  price rather than a range.

**Suggested label:** "Ticketmaster listed price range (min/max, USD)", noting
that fee inclusion is undocumented and probably includes fees for TicketWeb
events. Avoid calling it "face value" in the report unless a source documents
that.

## 4. Other things to know

- **Terms of Use:** developers may not "cache or store any Event Content other
  than for reasonable periods in order to provide the service you are
  providing." A semester project that archives daily snapshots should probably
  confirm with the instructor that this is acceptable academic use. This is not
  legal advice.
- **Resale events in Discovery:** by default Discovery returns events from all
  sources, including Ticketmaster Resale (TMR). Our sample showed no resale
  sources (hosts were ticketmaster.com, ticketweb.com, universe.com and
  atgtickets.com). Keep checking this in later collections.
- Scraping ticketmaster.com for prices is not a documented option and would
  conflict with the Terms of Use.

## Pages consulted

- Discovery API v2: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
- Getting Started: https://developer.ticketmaster.com/products-and-docs/apis/getting-started/
- Inventory Status API: https://developer.ticketmaster.com/products-and-docs/apis/inventory-status/
- Top Picks API: https://developer.ticketmaster.com/products-and-docs/apis/top-picks/
- Partner API (All In Price, Fees and Taxes): https://developer.ticketmaster.com/products-and-docs/apis/partner/
- FAQ: https://developer.ticketmaster.com/support/faq/
- General Terms of Use: https://developer.ticketmaster.com/support/terms-of-use/
- 404s: `/apis/commerce/`, `/apis/commerce/v2/internal/`, `/apis/inventory-status/v2/`, `/apis/discovery-api/v2/release-notes/`
