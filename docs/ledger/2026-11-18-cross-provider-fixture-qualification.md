# Cross-Provider Fixture Catalogue Qualification

**Date:** 2026-11-18  
**Status:** IMPLEMENTED AND MERGED; MANUAL DISPATCH PENDING  
**Providers:** The Odds API v4 (event metadata) + 5DollarFootballAPI Community (scheduled fixture metadata)

## Purpose

Compare one exact upcoming fixture across providers, then conditionally retrieve one event-specific h2h market snapshot if the catalogues are complete and exactly one fixture matches. The event catalogue endpoint is quota-free; the bounded h2h request is capped at one credit.

## Request budget

For one selected competition over a bounded 30-day upcoming window:
- The Odds API: exactly one `GET /v4/sports/{sport_key}/events` request. Provider documentation says this endpoint does not consume odds usage credits.
- 5DollarFootballAPI: exactly one `GET /v1/leagues/{id}/fixtures?start_time=now&end_time=now+30d&status=scheduled&per_page=100&page=1` request.
- Retries: zero.
- Pagination: zero. If the 5Dollar response says `has_more=true`, the catalogue is marked incomplete and cannot qualify a market probe.
- Conditional market request: exactly one event-specific h2h market in one UK region, only after a complete, unique exact match; maximum expected cost one credit.
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

No historical odds, retries, pagination, bulk collection, database writes, recurring schedule, model features, CLV, value betting, production prediction endpoint, public odds display or Android integration are enabled.


## Verification update — 2026-11-18

- PR #47 merged the strict event-to-fixture matcher; PR #48 merged the cross-provider catalogue qualification workflow.
- The Odds API catalogue workflow run [#44220418309](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44220418309) completed successfully on main. It returned HTTP 200, `AUTHENTICATED_SOCCER_CATALOGUE_AVAILABLE`, and 46 active soccer sport keys.
- The same run recorded `quota_last_cost=0`, `quota_used=229`, and `quota_remaining=271`. The existing account is authenticated; no key was exposed and no odds credits were spent.
- User confirmed authorization to use the existing Odds API account as needed for this project. This does not override provider terms, the current account balance, source timestamp requirements, or the no-commercial-use restriction recorded in the source approval.
- PR #48 CI run [#44222974563](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44222974563) passed: 209 backend tests, Ruff, and Android debug build.
- PR #49 merged strict event-specific h2h parsing as `69bd04666996c3d0901105ebdb3d1a45dd3e4522`; CI [#44224263834](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44224263834) passed 214 backend tests, Ruff and Android debug build.
- PR #51 merged the conditional one-credit h2h probe gate as `b1db56bda8bcaa9e82ac0619f1b0dc8227bf6392`; CI [#44224521063](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44224521063) passed 214 backend tests, Ruff and Android debug build.
- The merged manual workflow now uses one selected competition over the next 30 days, one quota-free Odds API event-catalogue request and one 5Dollar scheduled-fixture request. Only if both catalogues are complete and exactly one unique exact fixture match exists does it make one h2h market request in one region. It performs no pagination, retries, history request or database write.
- The workflow has not yet been dispatched. The current observed Odds API balance is 271 credits from run #44220418309; a successful one-market/one-region request is expected to cost at most one credit.


## Bounded h2h market probe

- The event-specific endpoint is called only after one exact unique match across complete catalogues.
- One market (`h2h`) and one region (`uk`) are specified. Official v4 documentation states usage cost is one credit per returned market per region; maximum expected cost is one credit, and an empty response may cost zero.
- The parser requires event ID, sport key, home/away orientation and kickoff to match the selected canonical fixture. It retains only timestamped market-level quotes and complete HOME/DRAW/AWAY bookmaker sets; incomplete or untimestamped quotes are excluded.
- No retries, pagination, history request, DB write or recurring schedule is performed.
- The response manifest records request/retrieval timestamps, response hash/size, provider date header and quota headers. The API key and raw response are never logged.
- The observation remains research-only. `last_update` alone does not establish PIT admissibility; source publication/availability and system receipt evidence must still satisfy the feature admission contract.
