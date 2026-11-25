# 2026-11-25 — Daily pipeline watchdog

## Verified state
- Capture run 45647801888 completed successfully, but all six competitions returned SKIPPED_ALREADY_VALIDATED; no fresh provider observations were established by that run.
- Stage 6 run 45647925344 (job 139323867954) remained in_progress at the latest check, at canonical identity/PIT dataset construction. Persistence and final verification had not run.
- Capture -> Stage 6 -> Stage 7 inference/evaluation workflow_run dependencies already exist and were not changed.

## Proposed watchdog
- Branch: feat/daily-pipeline-watchdog. PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/177.
- Added .github/workflows/veltrix-daily-pipeline-watchdog.yml. It runs at 04:17 UTC after the primary 00:17 UTC capture schedule and supports manual dispatch.
- No daily capture run: dispatch the existing bounded capture workflow. Active or successful run: do not duplicate. First-attempt failure: retry failed jobs only. Queued for at least 120 minutes with no active capture: dispatch recovery. Otherwise record status and take no action.
- Reuses existing request caps, provider pacing, importer idempotency and concurrency. It does not call 5DollarFootballAPI or The Odds API directly.
- Not active until CI validation and merge.

## Required verification and blockers
1. Validate action syntax and exact-head CI before merge; PR #177 has no check results visible yet.
2. Verify the first watchdog execution and the full capture -> Stage 6 -> Stage 7 chain with run IDs, artifacts and fresh PIT cutoffs.
3. This watchdog handles missed/failed scheduling only. Same-window SKIPPED_ALREADY_VALIDATED needs a separate bounded fresh-observation design; do not bypass idempotency or raise provider request limits without a budgeted protocol.
4. Stage 6 run 45647925344 was still running at the latest check; no downstream result is inferred.
5. Preserve six-hour freshness, immutable snapshots, rights, identity and concentration gates. No Odds API calls, model promotion, publication, Telegram delivery, certification or Value Betting unlock occurred.
