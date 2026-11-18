# Supplemental Odds Provider Qualification — The Odds API

**Date:** 2026-11-18  
**Status:** CANDIDATE SELECTED FOR BOUNDED QUALIFICATION; NOT ENABLED  
**Primary:** 5DollarFootballAPI Community  
**Candidate:** The Odds API v4  
**Reference integration:** `Nexora-Apparel/veltrix-football`

## 1. Decision

Keep 5DollarFootballAPI as the canonical fixture/results provider and retain its fixture-level odds endpoint as the first source. Qualify The Odds API v4 as a separate supplemental bookmaker-price source because the current Community account's sampled odds-market timestamp coverage is insufficient for the project's strict PIT/CLV goals.

Do not integrate OddsPapi, InferSports, or suspended API-Football as part of this change. Do not replace 5Dollar fixture identity or results with The Odds API event records.

## 2. Evidence from the current VELTRIX AI ANALYST provider

The 2026-11-18 one-request probe verified:
- `GET /v1/fixtures/1194891794/odds` returned HTTP 200.
- Bet365 and 12 market keys were present.
- 1X2 opening prices were present with `opened_at`.
- This was a single fixture snapshot, retrieved after the provider's opening timestamp. It does not establish pre-cutoff availability or broad competition coverage.

The provider qualification record for the Community plan in the reference VELTRIX FOOTBALL repository sampled 77 market blocks across seven competitions; only 7/77 (9.09%) contained a market timestamp. A BTTS odds-history request returned HTTP 403. That older sample is not a substitute for a fresh AI ANALYST measurement, but it is a strong reason not to assume the Community snapshot alone satisfies the project's timestamp-coverage target.

## 3. Reference integration verified in the other repository

Repository: `Nexora-Apparel/veltrix-football`

Relevant source:
- `app/provider_adapters.py`
  - `TheOddsAPIClient`
  - API v4 base URL `https://api.the-odds-api.com/v4`
  - `soccer_sports()`
  - `events_for_sport(sport_key)`
  - `odds_for_sport(sport_key, regions="uk", markets="h2h,totals")`
  - `event_btts(sport_key, event_id, regions="uk")`
  - Reads secret name `THE_ODDS_API_KEY`; never copy or expose its value.
  - Captures quota headers: `x-requests-remaining`, `x-requests-used`, `x-requests-last`.
- `_event_market_summary()` normalizes bookmaker title/key, market key, `last_update`, outcome name, decimal price and optional point/line.
- `app/value_bets_runtime.py` rejects snapshots without aware `fetched_at`, exact kickoff alignment, pre-kickoff retrieval and quote `last_update <= fetched_at`; this is reference logic only and must be independently tested against AI ANALYST contracts.
- `scripts/verify_data_providers.py` performs a quota-free `/v4/sports` credential/market catalogue check and prints only safe status/quota metadata.

Reference project records report successful authentication and live soccer market checks for h2h, totals and event-specific BTTS. Its historical record states the earlier bounded check used three odds credits and had 497 remaining at that time. This is historical evidence, not a statement of current key balance, current pricing, current plan, or current coverage.

## 4. Why this source is a useful candidate

- Adds an independent bookmaker market feed rather than relying on a single Bet365 opening snapshot.
- The v4 live odds response includes bookmaker-specific markets and provider `last_update` timestamps.
- Reference integration already has tested endpoint and response-normalization patterns.
- h2h (1X2), totals, and event-specific BTTS are represented in the existing reference implementation.

The source timestamp `last_update` is provider-reported quote-update time, not proof of when this system received the quote. AI ANALYST must separately record request start and response retrieval time. PIT admission requires actual local `retrieved_at <= prediction_cutoff_at`, plus `last_update <= retrieved_at), exact fixture identity and future kickoff.

## 5. Credentials and repository boundary

The reference repository uses GitHub Actions secret name `THE_ODDS_API_KEY`. GitHub repository secrets are scoped to their repository; the existence of that secret in `veltrix-football` does not make it available to `veltrix-ai-analyst`.

The AI ANALYST repository currently has no code reference to `THE_ODDS_API_KEY`. Never attempt to read, print, copy through logs, or expose the secret value. Before any live request from AI ANALYST, a repository owner must add the intended credential to AI ANALYST's own secret store. If it is the same credential, reuse is subject to its plan, current balance, terms and authorized scope. Do not create a new account or purchase credits.

## 6. Bounded qualification sequence

1. Add a manual-only credential-safe `/v4/sports` probe. It must not spend odds credits and must not print URLs containing the key, headers, or key material.
2. If authenticated, select one already-known upcoming fixture that is safely matchable to a canonical 5Dollar fixture.
3. Make one event-specific odds request for the minimum required market set; record request start, retrieval time, provider `last_update`, response hash, quota headers, sport key, event ID, bookmaker, market, selection, point and decimal price.
4. Do not call historical odds endpoints unless the current subscription and terms explicitly support them; do not assume historical archive access.
5. Compare actual fixture match rate, required-market completeness, bookmaker diversity, timestamp completeness, freshness and per-request quota cost against the 5Dollar feed.
6. Keep all observations in a dry-run manifest until schema, identity, PIT and data-use tests pass.
7. Only then propose a separate guarded capture writer. Keep collection manual and low-volume initially.

## 7. Provider selection and merge policy

- 5Dollar remains authoritative for fixture identity, kickoff and results.
- The Odds API contributes independent bookmaker quotes only after a unique, exact team-and-kickoff match; ambiguous joins are rejected.
- Never average prices across bookmakers or markets without preserving their individual identities.
- Never use a source's event ID as a 5Dollar fixture ID.
- Never use retrieval time as a substitute for `last_update`; preserve both clocks.
- Never backfill historic PIT availability using a current quote or a provider's old quote timestamp.
- If The Odds API is unavailable, keep valid 5Dollar observations and mark supplemental coverage missing. Do not silently substitute stale quotes.
- Odds data must not change model probabilities or forecasts during this qualification.

## 8. Explicit release gates

This qualification does not enable production odds ingestion, recurring schedules, historical odds backfills, CLV claims, value betting, public odds display, prediction endpoints, model promotion or Android integration. Rights approval, current account entitlement, real quota cost, timestamp coverage and PIT eligibility must be verified first.
