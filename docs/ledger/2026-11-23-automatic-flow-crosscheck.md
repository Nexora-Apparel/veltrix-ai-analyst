# 2026-11-23 — Automatic capture → Stage 6 → Stage 7 cross-check

## Scope and method

Read-only audit of the current `main` workflows, recent GitHub Actions runs and job logs, feed routes, Android API consumption, and open integration PRs.

- Repository: `Nexora-Apparel/veltrix-ai-analyst`
- Main head inspected: `8c16efa5c854b667a6a7f5c897e9b660de6ada59`
- Main CI run for that head: `45274517391`, conclusion `success`.
- No workflow was dispatched or rerun for this audit.
- No provider request, The Odds API request, database write, deployment, model promotion, publication, or gate change was initiated.

## Automatic chain: static wiring

### Capture

File: `.github/workflows/prospective-5dollar-daily-capture.yml`

- Current schedule: `0 0 * * *` UTC = 01:00 Africa/Lagos (WAT).
- Uses the existing 5Dollar Football API credential and the dedicated `veltrix_ai_analyst` database.
- Runs PIT schema checks before provider collection.
- Uses a bounded rolling window from the previous UTC day through eight days after the current UTC day.
- Workflow timeout: 180 minutes.
- The CLI receives `--request-budget 4` for each competition. This is a per-competition budget, not a four-request global batch cap. With six configured competitions, the configured ceiling is up to 24 provider requests per run; the latest inspected run used two requests per competition (12 total).
- The provider adapter is configured with a 60-second minimum request interval.

### Stage 6

File: `.github/workflows/stage-6-daily-snapshot-materialization.yml`

- Workflow ID: `423623285`.
- Triggered by completion of the named capture workflow.
- Workflow-run materialization proceeds only after a successful capture.
- It validates PIT dataset integrity, immutable snapshot persistence, distinct fixture identity, append-only guards, and keeps release eligibility false, production promotion locked, and value betting locked.
- A direct push to the Stage 6 workflow file can also trigger Stage 6; Stage 7's lineage condition intentionally blocks automatic inference from that push-triggered Stage 6 run.

### Stage 7 automatic research inference

File: `.github/workflows/research-shadow-inference.yml`

- Workflow ID: `426587312`.
- The hardcoded upstream Stage 6 workflow ID `423623285` matches GitHub's recorded Stage 6 workflow ID.
- Automatic inference requires: workflow-run event, upstream event `workflow_run`, main branch, and successful Stage 6 conclusion.
- Manual dispatch remains gated by explicit `confirm_research_ledger_write=true`.
- Inference cap: 25 fixtures; maximum snapshot age: six hours.
- Writes only to the isolated research ledger.

**Static wiring result:** no workflow-ID mismatch or broken Stage 6 → Stage 7 trigger condition was found.

## Runtime evidence

### Latest capture / Stage 6 / Stage 7 chain inspected

- Capture run `45257630040`: `workflow_dispatch`, completed successfully.
- Stage 6 run `45257770836`: `workflow_run`, completed successfully.
- Stage 7 inference run `45258094322`: `workflow_run`, completed successfully.
- Stage 7 inference job and both build/persist steps completed successfully, proving the automatic Stage 6 → Stage 7 trigger fired for this successful upstream Stage 6 run.

Important: the capture in this chain was manually dispatched. It proves the Stage 6 → Stage 7 automatic trigger, but it does not prove that the new 00:00 UTC scheduled capture has run successfully.

### Why the successful chain produced no forecasts

Capture run `45257630040` reported all six configured competitions as `SKIPPED_ALREADY_VALIDATED`. The matching validated imports were already present from scheduled capture run `45171104634`:

- Brazil Serie A: 2 records inserted, 2 requests used.
- Brazil Serie B: 0 records inserted, 2 requests used.
- England Premier League: 0 records inserted, 2 requests used.
- Germany Bundesliga I: 0 records inserted, 2 requests used.
- Italy Serie A: 2 records inserted, 2 requests used.
- Spain La Liga: 1 record inserted, 2 requests used.

The later manual capture reused these completed validated imports rather than refreshing them.

Stage 6 run `45257770836` verified:

- 14 immutable snapshots.
- 14 distinct fixture identities.
- 145 feature-lineage records.
- 0 settled labels; 14 unsettled rows.
- `release_eligible=false`, `production_promotion=LOCKED`, `value_betting=LOCKED`.

Stage 7 run `45258094322` completed its inference and persistence steps, but its report was:

- `status=NO_FRESH_UPCOMING_SNAPSHOTS`
- `fixture_count=0`
- `fixtures_considered=0`
- `provider_calls=0`
- `value_betting=LOCKED`

This is a correct abstention under the six-hour freshness gate, not a successful forecast-generation run.

### Certification workflow is separate

Run `45258094289` for `stage-7-prospective-research-evaluation.yml` also completed technically, but its report was:

- `status=INSUFFICIENT_PROSPECTIVE_DATA`
- `fixtures=0`, `folds=0`
- `settled_labels=0`, `distinct_dates_with_settled_labels=0)
- `production_certification=BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE`
- production promotion and value betting remained locked.

A green Actions conclusion here means the evaluation script and gates executed; it does not mean the model passed certification.

## Operational risks and separate app-feed blockers

1. **Same-window reuse can prevent same-day recovery.** `scripts/collect_5dollar_all_approved_competitions.py` returns `SKIPPED_ALREADY_VALIDATED` whenever a completed validated import exists for the exact competition, date boundaries and import type. It does not apply a freshness TTL to that reuse decision. A later same-day run can therefore reuse data that has aged beyond Stage 7's six-hour snapshot limit. This is a recovery/design risk; do not bypass it by blindly repeating provider calls. If it recurs, design a reviewed refresh policy with an explicit age threshold and idempotency safeguards.
2. **Scheduled start-time punctuality is not proven.** The prior scheduled capture run `45171104634` was created/started at 12:06:06 UTC even though the workflow revision used at that time declared a 03:17 UTC cron (about 8h49m late). The schedule was subsequently moved to 00:00 UTC / 01:00 WAT to create more runway. The first run under the new schedule is still required; GitHub scheduled events are best-effort.
3. **The legacy shadow workflow is intentionally disabled.** `.github/workflows/prospective-shadow-predictions.yml` has an unconditional `if: false` job guard. Its skipped run `45258094335` is expected and must not be mistaken for failure of the newer Stage 7 inference workflow.
4. **The current API feed still uses future-only filters.** On main, `research_predictions.py` uses `fixture.kickoff_at > now`; `public_predictions.py` also filters to future kickoffs. Open draft PR #160 contains the WAT calendar-day inclusive/exclusive bounds intended to retain today's started/completed fixture records, but it is not merged. This is separate from the absence of fresh Stage 7 forecasts.
5. **Research display has a production configuration gate.** The research route returns its quarantined empty response unless `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true` and the model-admission check passes. The live deployment setting was not inspected in this GitHub-only audit; verify it through a safe read-only deployment/API check before attributing an empty Android feed solely to model output.
6. **Android correctly accepts an empty predictions array.** The Home screen then renders `No matches for today.`; an HTTP 200 empty response is not necessarily an Android parser failure. The app's actual live endpoint payload remains to be compared against the device refresh timestamp.

## Tomorrow's verification sequence

For the first scheduled run under the 00:00 UTC cron (24 November 2026):

1. Read the scheduled capture run; confirm event is `schedule`, run creation/start delay, and whether competitions performed fresh validated imports or were skipped.
2. Confirm Stage 6 was triggered by that exact capture run, with successful conclusion, fresh snapshot timestamps, persistence verification and closed release gates.
3. Confirm Stage 7 inference was triggered by that exact Stage 6 run, with `workflow_run` lineage, and inspect the report for forecast count and abstention reason.
4. Check the research endpoint response, including `status`, `generated_at`, `predictions`, research-display gate and model-admission result.
5. Reconcile API payload with Android logs/device refresh. Keep the existing UI; do not unlock publication or value betting.
6. If snapshots are stale, report the cause and retain the six-hour gate. Do not force stale forecasts into the app.

## Conclusion

The automatic Stage 6 → Stage 7 trigger is correctly wired and has executed automatically after a successful Stage 6 run. The end-to-end daily scheduled path under the new 00:00 UTC schedule is not yet verified. The most recent inference run generated zero forecasts because the available snapshots were not fresh enough; the capture reused previously validated imports. Certification remains blocked by zero prospective settled labels. No release or value-betting gate should change.
