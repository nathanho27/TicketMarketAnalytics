# Feasibility: Ticketmaster + Last.fm Pivot (2026-11-05)

Proposed direction: analyze live events and artist popularity across the 10
largest U.S. cities using Ticketmaster (events) and Last.fm (artist
popularity).

**Status:**
- No Last.fm requests have been made yet: there is no `LASTFM_API_KEY` in
  `.env`.
- The matching test is written (`scripts/probes/probe_lastfm.py`) and has been
  dry-run without calling the API.
- Counts below come from our existing Ticketmaster test (LA + NYC, Nov 6–10,
  336 events).

## 1. What we already have (no rework needed)

- Working Ticketmaster pipeline:
  - collect → raw JSON;
  - convert → one CSV row per event ID, 91 columns, quality flags;
  - evaluate.
- Performer data already captured per event: Ticketmaster attraction IDs,
  names, genres, and **MusicBrainz IDs**. These are the best keys for
  matching to Last.fm.
- Only a 2-city, 5-day test run exists (2026-11-02). Daily collection never
  started, and **nothing is committed to GitHub yet**.

## 2. Last.fm API: what's free and what's allowed

**Data available for free** (API key only, no payment):

| Method | Gives | Scope |
|---|---|---|
| `artist.getInfo` | `listeners`, `playcount`, `mbid`, `url`, top tags, similar artists, short bio | **Global**, all-time totals |
| `artist.getTopTags` | User-applied tags with counts | Global |
| `artist.search`, `artist.getCorrection` | Candidate names / spelling corrections | — |
| `geo.getTopArtists` | Top artists | **Country only** (e.g., "united states") |
| `geo.getTopTracks` | Top tracks; documents an optional `location` (metro) parameter | Untested; may not work |

**Limits and terms** (last.fm/api/intro, last.fm/api/tos):
- **Academic use:** the terms open with: "If you are planning to use our API for
  commercial or research/academic purposes … please drop us a line prior to
  use" (partners@last.fm). We should email them and tell the TA we did.
- **Non-commercial use only.** Storing is allowed, but total stored Last.fm
  data must stay under a "Reasonable Usage Cap" of **100 MB**. We'd store only
  a few fields per artist, well under that.
- **Credit:** Last.fm must be credited and linked in anything published.
  The data can't be sub-licensed.
- **Rate limit:** no published number. Accounts "may be suspended" for
  "several calls per second". Use about 1 request/second and an identifiable
  User-Agent.

## 3. Artist matching

Matching paths, in order of reliability:

1. **MusicBrainz ID** from Ticketmaster → `artist.getInfo?mbid=…`. An exact
   identifier, but only **106 of 294 music performers (36%)** have one.
2. **Ticketmaster's Last.fm link.** Only 22 performers have one.
3. **Name lookup** (`autocorrect=1`) for the other 188 performers. Not
   reliable on its own:
   - Last.fm keeps **one page per name**, so different artists who share a
     name are merged and their listener counts blended.
   - Short or generic names are risky ("Ten", "EQ", "ARI", "kwn").
   - Ticketmaster has one artist under two IDs (Kenyon Dixon).

Coverage before matching:
- **96 of 320 music events (30%) list no performer at all.** Only the event
  title exists, for example "ESCAPE - Tribute to JOURNEY" or "Betty Bryant
  Birthday Bash Brunch". Parsing titles would invite false matches.
- Only **80 of 320 music events (25%)** have every listed performer carrying a
  MusicBrainz ID.

**The probe** samples 30 performers with a MusicBrainz ID and 30 without. It
labels each result `mbid`, `name_exact`, `name_autocorrected` or `unmatched`,
and flags questionable ones:
- `no_mbid_on_lastfm`, a sign of possibly merged artists;
- `very_short_name`;
- under 1,000 listeners;
- the Last.fm URL differs from Ticketmaster's link.

Name matches are never treated as confirmed.

**Untested assumption:** that Last.fm resolves Ticketmaster's MusicBrainz IDs
cleanly. The probe will show this.

## 4. Data quality for comparing cities

1. **Last.fm popularity is global, not local.** It can't tell you how popular
   an artist is *in* Los Angeles vs New York. Only questions like "do bigger
   markets book more popular artists?" work. Metro-level data doesn't
   reliably exist in the API.
2. **Ticketmaster isn't the whole market.** Venues ticketed by AXS, DICE,
   Eventbrite, See Tickets, or their own box office are missing, and
   Ticketmaster's share varies by city. City differences partly reflect that
   share, not the live-music scene.
3. **Small clubs dominate the counts.** In NYC, 141 of 228 music events are
   TicketWeb listings. Four jazz clubs (Smalls, Mezzrow, Birdland, Blue Note)
   account for 70, with several sets per night. Counting events, not
   performers or venues, would overweight them.
4. **Sports has no popularity metric.** Last.fm covers music only; sports
   "performers" are teams. Artist popularity would apply to Music only.
5. **Last.fm audience bias.** Its users skew toward certain genres and age
   groups (historically rock, indie and electronic). Listener counts are
   all-time totals, not current popularity, and come with no history. Tags
   are user-generated and messy.
6. **Listed prices** still cover only about 43% of events, mostly TicketWeb.
   This is unchanged from Phase 1.
7. **Radius searches.** 25 miles from each city center means different things
   in dense and sprawling cities. Nearby cities could also overlap; the
   converter already flags overlaps.

## 5. Originality check

- **Kaggle:** searching "ticketmaster" returned **no Ticketmaster dataset**.
  Last.fm artist popularity *is* well covered:
  - [Music artists popularity](https://www.kaggle.com/datasets/pieca111/music-artists-popularity)
    (~8 years old, the most used);
  - [last.fm Music Artist Scrobbles](https://www.kaggle.com/datasets/pcbreviglieri/lastfm-music-artist-scrobbles);
  - [Last.fm Global Trends](https://www.kaggle.com/datasets/tiagoadrianunes/last-fm-global-trends) (new).

  We would collect fresh data, not reuse these, but the TA may know them.
- **GitHub, closest overlap:**
  [leomckenna/ticketmaster-data-collection](https://github.com/leomckenna/ticketmaster-data-collection).
  It builds Ticketmaster Discovery music events into normalized relational
  tables in SQLite, with a `schema.sql`, daily snapshots and price-focused
  EDA. **Don't look at its schema while designing ours**, and expect the TA
  to ask how ours differs.
- **Similar research questions:**
  - [yiaktan/Secondhand_Concert_Tickets](https://github.com/yiaktan/Secondhand_Concert_Tickets):
    Ticketmaster + SeatGeek + StubHub + Spotify popularity across the largest
    U.S. markets, with genre, promoter and venue-state analysis. Close to our
    original idea; published on Towards Data Science.
  - [nkane07/event-booking-database](https://github.com/nkane07/event-booking-database):
    a Ticketmaster-*inspired* booking schema with an ERD and normalization
    report. A different domain (transactions), but a coursework-style SQL
    project.
- **Apps combining Ticketmaster with Last.fm or Spotify** (not SQL analyses):
  - [concert-radar](https://github.com/ShawnJoshua03/concert-radar)
    (Ticketmaster + Spotify);
  - MusiCon-React (Ticketmaster + Spotify + Last.fm);
  - [ConcertBuddy](https://github.com/skuill/ConcertBuddy/issues/42), which is
    weighing Last.fm listeners as a popularity signal.
- **Assessment:** the specific combination isn't something we found
  published: a fresh 10-city Ticketmaster snapshot, joined to Last.fm
  popularity and tags by MusicBrainz ID, used to compare markets. The
  Ticketmaster-only part is not original. The Last.fm join and the
  cross-city framing are what make it different.

## 6. Feasibility

- **Volume.** One 10-city snapshot:
  - Ticketmaster: about 1,800 requests (10 cities × 2 segments × ~90 days),
    under the 5,000/day limit.
  - Last.fm: one request per unique performer (likely a few thousand). At
    1/second, that's about an hour.
- **Enough structure for 6+ tables.** The data has many distinct entities and
  many-to-many links (events, performers, venues, promoters, classifications,
  Last.fm tags). Table design is the team's job.
- **Timeline (ERD due Nov 19).** Realistic if the Last.fm key and probe happen
  in the next 1–2 days. The ERD doesn't depend on the full 10-city collection.

## Sources

- Last.fm API: https://www.last.fm/api/intro · https://www.last.fm/api/tos · https://www.last.fm/api/show/artist.getInfo · https://www.last.fm/api/show/geo.getTopArtists · https://www.last.fm/api/show/geo.getTopTracks
- GitHub and Kaggle links are given inline above.
