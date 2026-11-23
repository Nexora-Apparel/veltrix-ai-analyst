# 2026-11-23 — Stage B1 WAT daily-feed backend implementation

## Scope and status

Partial implementation of the daily matchday contract on branch `fix/wat-daily-matchday-feed`. This is backend-only work. Stage B is NOT complete: Android integration, research history/settlement, full API tests, and CI verification remain outstanding.

## Repository baseline

- Base branch: `main`
- Base commit: `9e2a6c26f55a6026ae0b101448343e897298257d`
- Existing unrelated draft PR #146 remains open and was not modified.

## Changes made

1. Added `backend/app/wat_calendar.py`.
   - Uses `ZoneInfo("Africa/Lagos")`.
   - Computes the current WAT calendar date.
   - Returns an inclusive UTC start and exclusive UTC end for WAT midnight-to-midnight.
   - Rejects naive datetime inputs.
2. Updated `backend/app/routes/public_predictions.py`.
   - Daily list now filters kickoff timestamps with `>= start_utc` and `< end_utc`.
   - The individual prediction lookup path remains unchanged.
3. Updated `backend/app/routes/research_predictions.py`.
   - Research daily list now uses the same WAT day window.
   - Removed the kickoff-in-the-future predicate for the daily research feed.
   - Preserved the 36-hour latest-run age gate, 25-row cap, research-only status, unpublished status, production-promotion lock, and value-betting lock.
4. Added `backend/tests/test_wat_calendar.py`.
   - Covers UTC/WAT rollover at 23:00 UTC, stability across UTC midnight within the same WAT date, timezone-aware input enforcement, and feed query contract.

## Important semantics

- Today's fixtures remain in the daily endpoint regardless of whether kickoff has passed.
- Tomorrow's fixtures are excluded by the exclusive next-WAT-midnight bound.
- Published and research records remain separate; no research record is promoted or counted as published.
- Existing published history endpoint is unchanged.
- The 36-hour research run freshness gate remains intentionally unchanged pending evidence that it should be altered.

## Verification

- Source changes and test file are committed to the feature branch.
- No local test execution or GitHub Actions result has yet been verified.
- No production DB, provider, Odds API, inference, deployment, environment, or schedule operations were performed.

## Remaining Stage B work

- Run backend test suite and fix any failures.
- Add endpoint-level tests with mocked DB rows and exact boundary fixtures.
- Integrate Android feed filtering with authoritative WAT semantics; update “Upcoming” wording and add research-only labels consistently on BTTS and Over/Under.
- Inspect and implement a separate research-history contract only after confirming settlement evidence lineage; do not alter published history or certification metrics.
- Add Android unit/build verification.
- Compare exact live feed fixture identities against the user's 21-to-5 observation if an existing cached response/log can be used without provider or Odds API calls.
- Keep this PR unmerged and do not deploy without explicit authorization.
