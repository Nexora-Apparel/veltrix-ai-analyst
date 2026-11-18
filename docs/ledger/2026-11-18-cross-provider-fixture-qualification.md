# Cross-Provider Fixture Catalogue Qualification

**Date:** 2026-11-18  
**Status:** IMPLEMENTED AS MANUAL DRY-RUN; NOT DISPATCHED  
**Providers:** The Odds API v4 (event metadata) + 5DollarFootballAPI Community (scheduled fixture metadata)

## Purpose

Prepare one exact fixture identity comparison before any The Odds API odds-market request. The comparison uses The Odds API's quota-free event endpoint and one 5Dollar league-fixture request. It does not retrieve bookmaker prices.

## Request budget

For one selected competition over a bounded 30-day upcoming window:
- The Odds API: exactly one `GET /v4/sports/{sport_key}/events` request. Provider documentation says this endpoint does not consume odds usage credits.
- 5DollarFootballAPI: exactly one `GET /v1/leagues/{id}/fixtures?start_time=now&end_time=now+30d&status=scheduled&per_page=100&page=1` request.
- Retries: zero.
- Pagination: zero. If the 5Dollar response says `has_more=true`, the catalogue is marked incomplete and cannot qualify a market probe.
- Odds markets: zero.
- Database writes: zero.

The 5Dollar request uses only the exact seven competition IDs already approved in `FIVEDOLLAR_COMMUNITY_APPROVAL`. The event request uses the corresponding seven sport keys covered by `THE_ODDS_API_SOCCER_APPROVAL`.

## Reconciliation rules

- Preserve each provider's fixture/event ID separately.
- Require exact home-to-home and away-to-away identity after Unicode accent, case and punctuation normalization.
- No alias guessing or reversed home/away matching.
- Require kickoff difference within five minutes.
- Reject duplicate candidates and ambiguous matches.
- Require both catalogues to be complete.
- Produce `market_probe_candidate=true` only if exactly one unique exact match exists and both catalogues are complete.
- The user has explicitly authorized use of the existing Odds API account for this project. The manifest sets `market_probe_authorized=true` only when both catalogues are complete and exactly one unique exact match exists. The workflow then performs exactly one event-specific `h2h` request in one region (UK), with an expected maximum cost of one credit. No other market or region is requested.

## Audit evidence

Each provider manifest records request start, local retrieval time, HTTP status, response size/hash and available quota/rate-limit headers. No key, authorization header, request URL or raw response body is logged. The reconciliation manifest records event/fixture counts, match-status counts and exact candidate IDs.

## Explicit non-goals

No odds markets, historical odds, retries, pagination, bulk collection, database writes, recurring schedule, model features, CLV, value betting, production prediction endpoint, public odds display or Android integration are enabled.


## Bounded h2h market probe

- The event-specific endpoint is called only after one exact unique match across complete catalogues.
- One market (`h2h`) and one region (`uk`) are specified. Official v4 documentation states usage cost is one credit per returned market per region; maximum expected cost is one credit, and an empty response may cost zero.
- The parser requires event ID, sport key, home/away orientation and kickoff to match the selected canonical fixture. It retains only timestamped market-level quotes and complete HOME/DRAW/AWAY bookmaker sets; incomplete or untimestamped quotes are excluded.
- No retries, pagination, history request, DB write or recurring schedule is performed.
- The response manifest records request/retrieval timestamps, response hash/size, provider date header and quota headers. The API key and raw response are never logged.
- The observation remains research-only. `last_update` alone does not establish PIT admissibility; source publication/availability and system receipt evidence must still satisfy the feature admission contract.
