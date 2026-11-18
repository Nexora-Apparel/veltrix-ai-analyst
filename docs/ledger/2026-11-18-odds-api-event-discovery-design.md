# The Odds API Event Discovery — Zero-Credit Qualification

**Date:** 2026-11-18  
**Status:** IMPLEMENTED AS MANUAL DRY-RUN PROBE; NOT DISPATCHED  
**Credential:** Existing `THE_ODDS_API_KEY` repository secret  
**Odds-credit budget at last verified response:** 271

## Verified provider documentation

The Odds API v4 documentation states that `GET /v4/sports/{sport}/events` returns event IDs, home/away team names and commence times without odds, and does not count against the usage quota. The same documentation states that the live event-odds endpoint is charged by unique markets returned multiplied by regions requested. Official reference: https://the-odds-api.com/liveapi/guides/v4/

This creates a safer next qualification step: retrieve a single competition's event catalogue without spending the remaining odds-market credits, then compare event identity and kickoff against the existing 5Dollar canonical fixture schedule. No odds prices are requested in this stage.

## Implemented controls

- Manual `workflow_dispatch` only; no cron or recurring collection.
- One selected soccer sport key per run, restricted to an explicit allowlist.
- Exactly one HTTP GET to `/v4/sports/{sport}/events`.
- No odds market endpoint, historical endpoint, retry, pagination, fan-out or concurrency.
- No database writes and no model feature activation.
- Captures request start, retrieval time, status, response hash/size and quota headers.
- Normalizes only event ID, sport key, home team, away team and commence time.
- Rejects malformed rows, wrong sport keys, duplicate event IDs, naive timestamps and same-team fixtures.
- Excludes events that are not future fixtures at retrieval time.
- Does not print API keys, request URLs, raw response bodies or authorization headers.
- Uploads a compact artifact with seven-day retention.

## Interpretation boundary

The provider documentation says the events endpoint is quota-free; the workflow still records returned quota headers to verify actual account behavior. Event metadata is not bookmaker pricing and cannot be used as odds, a market benchmark, CLV or a prediction feature.

The next comparison requires a unique exact match to a 5Dollar fixture using normalized home/away identities and kickoff tolerance. Ambiguous team aliases or materially different kickoff times must be rejected for human review. The Odds API event ID must never replace the canonical 5Dollar fixture ID.

## Manual gate

The code is ready for CI and review. A repository owner must manually dispatch the workflow once on a chosen competition to retrieve the event list. No manual step is needed for the code review itself.

## Explicit non-goals

No market request is authorized by this design. No odds ingestion, DB persistence, historical reconstruction, recurring polling, model training, CLV calculation, value betting, public forecast, production prediction endpoint or Android integration is enabled.
