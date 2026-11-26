# 2026-11-26 — WAT daily slate correction (rebased on current main)

## Problem
Stage 7 selected upcoming fixtures by kickoff order and capped at 25 without first restricting kickoff dates to the current Africa/Lagos calendar day. This allowed tomorrow's fixtures to fill the daily slate.

## Implementation
- Added `backend/app/wat_calendar.py` with timezone-aware, inclusive-start/exclusive-end UTC boundaries for the current `Africa/Lagos` day.
- Stage 7 now filters eligible, future fixtures to that WAT window before chronological sorting and the maximum-25 cap.
- Published prediction list and single-prediction retrieval now enforce the same current-WAT-day bounds.
- Research prediction query now enforces the same WAT-day bounds while retaining the existing 36-hour run-age condition.
- Added unit coverage for WAT midnight boundaries, timezone-awareness, exclusion of tomorrow, empty daily slate, cap-after-filter, and API query parameters.

## Preserved safeguards
- Six-hour PIT snapshot age and all Stage 7 row eligibility/cutoff checks are unchanged.
- Research predictions remain `RESEARCH ONLY` and `NOT_PUBLISHED`.
- Production promotion and Value Betting remain `LOCKED`.
- No provider or Odds API calls, production database writes, inference dispatches, publication, or model promotion were performed.

## Verification
- This branch was created from current `main` at `7cc3bb77acc6a6a1947d875cf0f8a56ceb4f2fd4`, avoiding the 52-commit divergence discovered on the earlier PR branch.
- Exact-head CI has not yet run for this branch. Draft PR checks are the next gate.
- Vercel preview and CI results must be checked against the exact latest head.
- Physical Android device verification remains outstanding.

## Release decision
Not release-ready. Keep draft until exact-head backend tests/lint and Android build pass, code review is complete, and the Android app is verified to display only today's WAT fixtures.
