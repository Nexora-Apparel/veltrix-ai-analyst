# 2026-11-25 — Fresh prospective observation cycle

## Problem
The daily capture collector treated any previously validated import with the same competition, rolling boundaries and import type as permanently reusable. Because the rolling window is the same on each UTC date, a successful prior-day import caused today's capture to return `SKIPPED_ALREADY_VALIDATED`. Stage 6 then replayed the same immutable snapshots, and Stage 7 correctly abstained when their latest PIT cutoff exceeded six hours.

## Change on this branch
- Added `app.providers.prospective_capture_cycle.completed_prospective_capture_run_ids()`.
- For `prospective_capture` only, the collector now checks completed 5Dollar import runs by competition and UTC calendar day, rather than by the rolling window boundaries.
- A validated completed run from today remains idempotent and is skipped on manual reruns/recovery. A completed run from a prior UTC date no longer blocks today's fresh capture.
- Historical backfills and historical feature backfills retain their exact-boundary idempotency behavior.
- Existing resumable RUNNING/PAUSED import runs remain eligible for checkpoint-based resume.
- The workflow request budget, four-request per-competition cap, six-competition scope, 60-second pacing, source approval, provider response capture and database-derived observation timestamps are unchanged.
- Added unit tests for UTC-day normalization, exact half-open UTC day bounds, empty results and rejection of naive timestamps.

## Safety / expected behavior
- This is one completed prospective capture cycle per competition per UTC date; repeated same-day dispatches do not create another completed cycle.
- New-day capture uses the existing request budget and records real provider responses and database-derived `system_observed_at` sightings. It does not rewrite old evidence or manufacture timestamps.
- Stage 6 and Stage 7 triggers are unchanged. Fresh snapshots and forecasts will only appear if the new provider capture yields eligible upcoming fixtures and the downstream six-hour gate passes.
- No Odds API calls, production publication, Telegram delivery, model promotion, certification or Value Betting unlock.

## Validation status
- Branch: `fix/daily-fresh-observation-cycle`.
- Implementation and unit tests are committed. Exact-head CI run [45651504018](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45651504018) passed both Android debug build and backend tests/lint; the backend actionlint step, compile step, pytest and Ruff lint all passed. No provider integration run has been executed yet.
- Before merge, CI must pass backend tests/lint and actionlint. After merge, verify new import_run IDs, provider_response and source_observation_sighting timestamps, fresh Stage 6 snapshot cutoffs, Stage 7 report and isolated research-ledger forecast rows.
