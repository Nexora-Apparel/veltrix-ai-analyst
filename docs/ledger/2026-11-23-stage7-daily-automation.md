# 2026-11-23 — Stage 7 automatic daily research inference

## Objective

Connect Stage 7 research-only inference automatically to a successful Stage 6 daily snapshot materialization, while retaining an explicitly confirmed manual dispatch fallback.

## Verified baseline

- Main commit inspected: `9e2a6c26f55a6026ae0b101448343e897298257d`.
- Daily capture workflow: `.github/workflows/prospective-5dollar-daily-capture.yml`, already has a scheduled cron and a manual dispatch fallback.
- Capture run `45171104634` on 2026-11-23 completed with conclusion SUCCESS; it was a scheduled event.
- Capture validated six approved competitions and inserted seven records (2 Brazil Serie A, 2 Italy Serie A, 1 Spain La Liga; zero new rows in the other three).
- Stage 6 run `45172986846` completed with conclusion SUCCESS, persisted and verified 14 prospective snapshots, and retained release/promotion/value-betting gates as closed.
- Stage 6 artifact reported 14 distinct fixtures and 0 latest label events.
- Stage 7 is currently manual-only in main.
- Stage 7 run `44998631180` failed at Python parse time in `backend/scripts/build_stage7_shadow_predictions.py` line 103 due literal escaped newline sequences in a dictionary literal. The isolated-ledger write step was skipped.
- The Stage 7 builder hotfix PR #148 fixed the malformed summary construction by extracting `build_run_summary`; run `44999986842` then completed successfully and inserted a research-only run into the isolated ledger (run key `cf87118887071568e5d4279f7a82190cce697790265f56adff47a61957b3323b`).
- Current main's Stage 7 builder contains the corrected `build_run_summary` implementation. CI already includes `python -m compileall -q app scripts` and Ruff coverage for both Stage 7 scripts.

## Changes in this branch

1. Updated `.github/workflows/research-shadow-inference.yml`:
   - Added `workflow_run` subscription to Stage 6 completion.
   - Automatic execution is permitted only when:
     - the upstream workflow ID is Stage 6 (`423623285`);
     - the Stage 6 run itself was triggered by a successful capture workflow (`event == workflow_run`);
     - the upstream run is on `main`;
     - the Stage 6 conclusion is `success`.
   - Retained manual `workflow_dispatch` but still requires explicit `confirm_research_ledger_write=true`.
   - Keeps the same 25-fixture limit, 6-hour snapshot freshness gate, model pipeline, isolated research ledger, and sanitized artifact.
2. Updated `.github/workflows/ci.yml`:
   - Added the Stage 7 workflow to PR/push path filters.
   - Added it to actionlint validation.

## Safety model

- Stage 7 runs only after the capture workflow succeeded and Stage 6 completed successfully.
- Failed capture or failed Stage 6 does not launch Stage 7.
- Research forecasts are persisted only to `research_shadow_forecast_runs` via the existing validator and idempotent writer.
- No published predictions, production performance, release eligibility, or value betting are modified/unlocked.
- The pipeline uses the existing database secret and 5Dollar capture provider; it does not call The Odds API.
- The existing manual path remains gated by an explicit boolean confirmation.

## Verification state

- Source changes are committed on `automation/stage7-after-daily-capture`.
- CI/actionlint verification is pending PR execution.
- No workflow dispatch was initiated from this session because the connected GitHub actions interface exposes run/log reads and reruns but no workflow-dispatch operation.
- No production deployment, provider request, Odds API call, DB write, inference run, or schedule change was initiated by this implementation session.

## Next actions

1. Complete CI and actionlint verification.
2. Merge the reviewed automation workflow change to main after checks pass.
3. Trigger or await the next scheduled capture; verify the full capture → Stage 6 → Stage 7 chain from run events, jobs, artifacts, and isolated-ledger run key.
4. Report the first automatic Stage 7 run separately from any manual historical run.
