# 2026-11-23 — Morning research-readiness target (07:00–10:00 WAT)

## User requirement
Target the VELTRIX AI ANALYST morning prediction window to 07:00–10:00 Africa/Lagos (WAT). This is an operational target, not a delivery guarantee.

## Repository and workflow state inspected
- Repository: `Nexora-Apparel/veltrix-ai-analyst`; default branch: `main`.
- The previous capture cron was `17 3 * * *` UTC = 04:17 WAT.
- Capture has a 180-minute job timeout and uses the existing 5DollarFootballAPI secret with request budget 4.
- Successful capture triggers Stage 6 materialization; successful Stage 6 can trigger Stage 7 automatic research inference.
- Stage 7 currently enforces a maximum snapshot age of six hours and caps inference at 25 fixtures.
- Stage 6 has a 20-minute timeout; Stage 7 has a 30-minute timeout.
- The 23 November runtime audit found that a manual capture reused six already-validated imports, Stage 6 left 14 snapshots unchanged, and Stage 7 correctly abstained with `NO_FRESH_UPCOMING_SNAPSHOTS`. The snapshots were approximately 8.27 hours old at inference time.
- PR #153, which records that audit, is merged. PR #149 remains an open draft for WAT matchday feed scoping at the time of inspection.

## Proposed schedule adjustment
- Changed the capture cron in this branch to `0 0 * * *` UTC = 01:00 WAT.
- Added the target window to the Actions summary.
- Kept the 180-minute capture timeout, request budget 4, provider, concurrency group, PIT checks, Stage 6/7 triggers, six-hour Stage 7 freshness gate, and all release locks unchanged.
- The earlier capture is intended to leave time for capture, Stage 6, and Stage 7 to complete before the 07:00–10:00 WAT target.
- GitHub scheduled workflow start times are not exact guarantees. Actual run-created/start times and downstream completion must be measured after merge.

## Critical delivery distinction
- This change schedules prospective evidence capture earlier. It does not itself publish predictions to the production API or make them appear in Android.
- Stage 7 remains research-only. Production forecasts remain quarantined/unpublished; release eligibility and model promotion remain locked; value betting remains locked.
- The existing app integration and publication path must still be completed and validated against the existing Android UI. No interface redesign is included.
- The six-hour snapshot freshness gate must not be weakened to force forecasts. If capture or downstream inference misses the freshness window, the system must abstain and report the blocker.

## Safety and cost
- No workflow was dispatched or rerun.
- No provider or Odds API request was made by this change.
- No Odds API credits were consumed.
- No production database write, deployment, model promotion, publication, certification, or value-betting unlock was performed.
- Existing provider request budget and source restrictions remain unchanged.

## Verification still required
1. Review and merge the schedule PR before the cron takes effect.
2. Inspect the first scheduled run for actual UTC/WAT creation and runner-start delay, fresh imports versus skipped imports, and capture conclusion.
3. Verify the exact Stage 6 parent run, snapshot persistence, lineage, artifact, and closed release gates.
4. Verify Stage 7 was automatically triggered by that Stage 6 run, generated eligible research forecasts, and persisted only to the isolated research ledger.
5. Complete and validate the production publication/API-to-Android integration before describing any forecast as delivered in the app.
6. Record the first end-to-end morning timing against 07:00–10:00 WAT. Do not claim the target is met until the scheduled runtime evidence proves it.

## Next step
Review CI and merge readiness for the schedule PR; then continue the separate app-consumption/publication integration work without opening production release gates.
