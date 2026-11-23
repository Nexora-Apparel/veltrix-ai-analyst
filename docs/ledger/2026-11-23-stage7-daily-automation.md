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

## Follow-up verification — 2026-11-23 evening

### Capture timing finding
- The configured capture cron on main is `0 3 * * *` (03:00 UTC = 04:00 WAT).
- Capture job `137680551170` in run `45171104634` began at `2026-11-23T12:06:10Z` (13:06:10 WAT), approximately 9 hours 6 minutes after the configured time.
- The six-competition batch completed at `12:18:00Z` (13:18:00 WAT).
- This is an observed start-time delay, not a timezone conversion error. The capture schedule is UTC and the WAT conversion is +1 hour.
- GitHub's official Actions documentation confirms scheduled events are best-effort and may be delayed during high load; it recommends moving away from the top of the hour. An off-peak timing/diagnostics proposal already exists separately as PR #146. Its 03:17 UTC schedule is a mitigation only, not a punctuality guarantee.
- Stage 6 run `45172986846` completed successfully after capture and verified 14 snapshots, 14 distinct fixtures, and 0 latest label events.

### CI failure and correction
- Initial PR #150 CI run `45250606777`: actionlint and Python compile passed; Android debug build passed; backend suite had 1 failure and 540 passes.
- The single failure was a stale test assertion, `test_inference_workflow_is_manual_only_and_old_schedule_remains_disabled`, which explicitly rejected the new `workflow_run` trigger. It did not indicate a production/runtime failure.
- Updated `backend/tests/test_stage7_shadow.py` on this branch to assert the intended Stage 6 lineage conditions, success/branch/workflow-ID gates, manual confirmation gate, six-hour freshness limit, and 25-fixture cap.
- Correction commit: `4357a7e11d3b32c122fcd433d8f9de10304b4d6c`.
- CI for the corrected head must be rechecked before merge.

### Current limitations
- The run/job log establishes the runner start time; the exact scheduled-event enqueue timestamp is not available from the connected GitHub read tools in this session. The 9h06m figure is measured from configured cron time to runner start.
- No schedule change has been merged. PR #146 is a separate open draft and must be reviewed independently.
- No fresh provider capture, Stage 6/7 inference, Odds API request, production deployment, or model/value-betting promotion was initiated during this follow-up.

## Final execution update — 2026-11-23

### Stage 7 automation merged
- PR #150 merged successfully to main as commit `2158a0a4b7ae5eff77f67a04ff170b7e4bfe6234`.
- Exact-head CI run `45252072956` completed successfully. Backend tests/lint and Android debug build passed; Vercel preview check passed.
- Main now subscribes Stage 7 to successful Stage 6 workflow completion, with strict workflow ID, event lineage, main-branch and success checks.
- Manual dispatch remains gated by explicit confirmation. Six-hour snapshot freshness, 25-fixture cap, isolated research ledger and closed production/value-betting gates remain unchanged.

### Capture timing mitigation merged
- PR #146 rebased onto the new main head, expanded CI path coverage to include both capture and Stage 6 workflow files, and added actionlint validation for both.
- Exact-head CI run `45254675406` completed successfully:
  - Backend tests and lint: success.
  - actionlint: success (within backend validation step).
  - Python compile: success.
  - Android debug build/APK upload: success.
  - Vercel preview check: success.
- PR #146 merged as commit `eafc30fca814ddf41e3ffd1fc115406210699fff`.
- Main capture cron is now `17 3 * * *`: 03:17 UTC / 04:17 WAT.
- Capture and Stage 6 workflow summaries now record run creation/start timestamps and step outcomes; Stage 6 summary also records capture-to-Stage-6 lineage/timing.
- This is an off-peak scheduling mitigation and observability improvement, not a hard punctuality guarantee. GitHub Actions scheduled events remain best-effort.

### Verified current main
- Main head: `eafc30fca814ddf41e3ffd1fc115406210699fff`.
- Capture workflow contains the 03:17 UTC cron and timing summary.
- Stage 6 workflow contains capture/Stage 6 timing summary.
- Stage 7 workflow contains the automatic Stage 6 lineage trigger and success gates.

### Remaining verification
- No new capture was dispatched after the schedule change in this session. The first post-merge scheduled capture must be checked to confirm actual run-created and runner-start times against the 04:17 WAT target.
- The connected GitHub interface used here supports workflow-run reads and reruns but does not expose a workflow-dispatch operation; rerunning the prior successful capture would execute its old workflow revision and is not a valid test of the merged schedule.
- After the next successful capture, verify capture → Stage 6 → Stage 7 and inspect the Stage 7 artifact plus isolated research-ledger run key.
- Stage 7 forecasts remain research-only. No published production predictions, release eligibility, or value betting were unlocked or modified.
- No The Odds API requests were made.
