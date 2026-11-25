# 2026-11-25 — Daily pipeline watchdog

## Verified state
- Capture run 45647801888 completed successfully, but all six competitions returned SKIPPED_ALREADY_VALIDATED; no fresh provider observations were established by that run.
- Stage 6 run [45647925344](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45647925344), job 139323867954, subsequently completed successfully. All pipeline steps, immutable persistence, artifact upload and persisted-snapshot verification passed.
- Stage 6 artifact 15039492090, ZIP SHA-256 4272c728b121c8d0dc40ffaf4819bb94abab2351e567227a96512c65c115c4c4, contains 114 dataset rows: 54 settled labels and 60 unsettled targets; 1,442 fixture identity rows; 3,038 lineage records; zero invalid system-observed sightings.
- Critical result: all 114 immutable snapshots were reused; zero new snapshots were materialized. Dataset SHA-256 remained 414d8333f8f8bf7dd9d2318994ac64521f1448d2c5c04eee34d5297c2e50bd54.
- The latest unsettled prediction cutoff remained 2026-11-25T08:40:05.859675Z. Stage 6 dataset creation was 2026-11-25T15:51:53.747065Z, so the newest targets were already more than seven hours old. The six-hour Stage 7 freshness gate must therefore reject them. Do not infer a successful forecast from Stage 6 success.
- Capture -> Stage 6 -> Stage 7 inference/evaluation workflow_run dependencies already exist and were not changed. The Stage 7 run triggered by this latest Stage 6 completion has not yet been independently identified/inspected through the available Actions tools.

## Proposed watchdog
- Branch: feat/daily-pipeline-watchdog. PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/177.
- Added .github/workflows/veltrix-daily-pipeline-watchdog.yml. It runs at 04:17 UTC after the primary 00:17 UTC capture schedule and supports manual dispatch.
- No daily capture run: dispatch the existing bounded capture workflow. Active or successful run: do not duplicate. First-attempt failure: retry failed jobs only. Queued for at least 120 minutes with no active capture: dispatch recovery. Otherwise record status and take no action.
- Reuses existing request caps, provider pacing, importer idempotency and concurrency. It does not call 5DollarFootballAPI or The Odds API directly.
- The workflow YAML was read back from the feature branch and parsed successfully with PyYAML. No actionlint binary or exact-head GitHub CI result was available at the latest check. It is not active until CI validation and merge.

## Required verification and blockers
1. Obtain exact-head workflow/actionlint validation and required CI before merge; PR #177 currently has no visible check results.
2. Verify the first watchdog execution and the full capture -> Stage 6 -> Stage 7 chain with run IDs, artifacts, fresh PIT cutoffs and isolated ledger read-back.
3. This watchdog handles missed/failed scheduling only. Same-window SKIPPED_ALREADY_VALIDATED needs a separate bounded fresh-observation design; do not bypass idempotency or raise provider request limits without a budgeted protocol.
4. The latest Stage 6 run completed successfully but reused all 114 snapshots. The pipeline still needs an earlier successful fresh observation cycle so that Stage 7 receives targets within six hours.
5. Preserve six-hour freshness, immutable snapshots, rights, identity and concentration gates. No Odds API calls, model promotion, publication, Telegram delivery, certification or Value Betting unlock occurred.
