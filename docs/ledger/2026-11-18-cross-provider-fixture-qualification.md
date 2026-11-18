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
- The manifest always sets `market_probe_authorized=false`; a human review and separate market-request decision remain necessary.

## Audit evidence

Each provider manifest records request start, local retrieval time, HTTP status, response size/hash and available quota/rate-limit headers. No key, authorization header, request URL or raw response body is logged. The reconciliation manifest records event/fixture counts, match-status counts and exact candidate IDs.

## Explicit non-goals

No odds markets, historical odds, retries, pagination, bulk collection, database writes, recurring schedule, model features, CLV, value betting, production prediction endpoint, public odds display or Android integration are enabled.


## Verification update — 2026-11-18

- PR #47 merged the strict event-to-fixture matcher; PR #48 merged the cross-provider catalogue qualification workflow.
- The Odds API catalogue workflow run [#44220418309](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44220418309) completed successfully on main. It returned HTTP 200, `AUTHENTICATED_SOCCER_CATALOGUE_AVAILABLE`, and 46 active soccer sport keys.
- The same run recorded `quota_last_cost=0`, `quota_used=229`, and `quota_remaining=271`. The existing account is authenticated; no key was exposed and no odds credits were spent.
- User confirmed authorization to use the existing Odds API account as needed for this project. This does not override provider terms, the current account balance, source timestamp requirements, or the no-commercial-use restriction recorded in the source approval.
- PR #48 CI run [#44222974563](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44222974563) passed: 209 backend tests, Ruff, and Android debug build.
- The cross-provider workflow is merged but has not yet been dispatched. It is limited to one selected competition, the next 30 days, one Odds API event-catalogue request (zero odds credits), and one 5Dollar scheduled-fixture request. It performs no pagination, retries, odds-market request, or database write.
- No market probe is authorized by the workflow itself: `market_probe_authorized=false`. A single exact unique match only creates a candidate for the next bounded market-probe step.
