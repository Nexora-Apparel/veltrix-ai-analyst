# 2026-11-24 — Scheduled 5Dollar capture verification

## Scope and safety

Read-only verification of the current GitHub Actions state and the production Neon default branch. No workflow was dispatched or rerun. No football provider or The Odds API was called by this audit. No Odds API credits were consumed. Database checks were SELECT-only; no production database writes, deployment, release change, or gate change was made.

Repository: `Nexora-Apparel/veltrix-ai-analyst`  
Inspected main head: `8c16efa5c854b667a6a7f5c897e9b660de6ada59`  
Check timestamp: `2026-11-24T04:02:44Z` (05:02:44 WAT)

## 1. Scheduled capture: no 24 November run

- No 24 November 2026 capture run exists in the current Actions run list. The latest scheduled capture remains run [45171104634](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45171104634), created and started on 23 November.
- The requested `03:17 UTC` cron was not active on 24 November. Commit [eafc30f](https://github.com/Nexora-Apparel/veltrix-ai-analyst/commit/eafc30fca814ddf41e3ffd1fc115406210699fff) introduced `17 3 * * *`, but commit [0dae617](https://github.com/Nexora-Apparel/veltrix-ai-analyst/commit/0dae617d299aa005a64dea7bf102cb64525b3a8b) superseded it with `0 0 * * *`. Current main YAML reports `00:00 UTC / 01:00 WAT`.
- No 24 November `schedule` event was present by 04:02 UTC, more than four hours after the active 00:00 UTC cron. The requested 03:17 UTC time was also already past. There is therefore no run ID, creation timestamp, start timestamp, or schedule-to-start delay for 24 November.
- Current Actions queries returned zero queued and zero in-progress runs.
- Last scheduled capture details: run 45171104634, event `schedule`, workflow ID 422976374, created `2026-11-23T12:06:06Z`, started `2026-11-23T12:06:06Z`, head SHA `508e60b57c89d0d23ef2dfdc17a222d11b81718c`. The workflow file at that SHA used `0 3 * * *` (03:00 UTC), so its observed cron-to-start delay was 9h06m06s; GitHub run creation-to-start delay was 0s. This is a prior-day measurement, not a 24 November result.

## 2. Last scheduled capture import evidence (23 November)

Run 45171104634 completed successfully and created six new `prospective_capture` import runs:

| Import run | Competition | Requests | Records seen | Inserted | Duplicates |
|---:|---|---:|---:|---:|---:|
| 45 | Brazil Serie A | 2 | 10 | 2 | 8 |
| 46 | Brazil Serie B | 2 | 2 | 0 | 2 |
| 47 | England Premier League | 2 | 13 | 0 | 13 |
| 48 | Germany Bundesliga I | 2 | 11 | 0 | 11 |
| 49 | Italy Serie A | 2 | 16 | 2 | 14 |
| 50 | Spain La Liga | 2 | 15 | 1 | 14 |

Production readback confirms all six database import rows completed: 12 requests total, 67 records seen, 5 inserted, 62 duplicates, 0 rejected and 0 quarantined. During the capture window, the database recorded 78 new source-observation rows and 196 new observation-sighting rows. These are genuinely new import runs and new observations, not merely a successful workflow status.

A later manual capture, [run 45257630040](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45257630040), was explicitly `workflow_dispatch`, not schedule. Its logs show all six same import IDs (45–50) as `SKIPPED_ALREADY_VALIDATED`. Production readback shows no import runs, source observations, or sightings created after the 23 November 12:18 UTC capture window. The manual run reused the validated imports and did not create fresh provider observations.

## 3. Last scheduled Stage 6 child (23 November)

- [Stage 6 run 45172986846](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45172986846) was event `workflow_run`, created/started `2026-11-23T12:18:06Z`, and completed successfully. It followed the scheduled capture's successful completion at 12:18:02Z. The older run's job log does not echo the parent capture ID; the workflow event and timing identify it as the Stage 6 child, but the explicit parent ID is not independently printed in that run's log.
- Dataset: 14 eligible rows, 14 distinct fixtures, 5 competitions, 5 kickoff dates, 145 feature-lineage records, and 0 invalid system-observed sightings.
- Persistence: 5 snapshots inserted, 9 unchanged; read-back verified 14 snapshots across 14 distinct fixtures and 0 latest label events. Five of the 14 cutoffs were within the six-hour freshness window at dataset creation; nine were approximately 102.6 hours old.
- Cutoff range: `2026-11-19T05:45:59.512717Z` through `2026-11-23T12:16:33.533326Z`. Dataset SHA-256: `7e8a158b168d7c894220ebaa1e56ecfd81cbfbd5a31e9ff6b3b7840fc7d93e91`.
- Artifact: [14816948513](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45172986846#artifacts).

## 4. Stage 7 evaluation and automatic shadow inference

The scheduled Stage 6 run had a Stage 7 evaluation child, [run 45173271027](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45173271027), event `workflow_run`, conclusion success. Its artifact [14818072545](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45173271027#artifacts) reports 0 evaluated fixtures, 0 settled labels, no expanding folds, and `INSUFFICIENT_PROSPECTIVE_DATA`. Every certification gate remained unmet. No automatic `research-shadow-inference` run is present for that older scheduled Stage 6 run.

The latest completed downstream chain is a separate manual chain, not the missing 24 November schedule:

- Capture [45257630040](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45257630040): event `workflow_dispatch`, created/started `2026-11-23T20:16:17Z`.
- Stage 6 [45257770836](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45257770836): event `workflow_run`, created/started `20:17:05Z`, success. Its job log explicitly records capture parent ID `45257630040`. Same 14 fixtures and dataset hash; 0 inserted, 14 unchanged, 0 label events. Latest cutoff was already 8h02m old at dataset creation. Artifact [14858688717](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45257770836#artifacts).
- Stage 7 evaluation [45258094289](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45258094289): event `workflow_run`, success; 0 evaluated fixtures, 0 settled labels, no folds; artifact [14860070546](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45258094289#artifacts).
- Automatic shadow inference [45258094322](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45258094322): event `workflow_run`, workflow ID 426587312, same head SHA as Stage 6, created five seconds after Stage 6 completion. Current workflow conditions restrict automatic execution to successful Stage 6 `workflow_run` events on main. The inference job itself does not print the upstream Stage 6 run ID; the unique Stage 6 run in this sequence and the timing/commit match identify the chain, but the child log lacks an explicit parent-ID line.
- Inference report: max snapshot age 6 hours; newest cutoff `2026-11-23T12:16:33.533326Z`; inference generated at `2026-11-23T20:21:14.406191Z`, so the newest snapshot was 8h04m41s old. Result: `NO_FRESH_UPCOMING_SNAPSHOTS`, 0 fixtures considered, 0 forecasts, 0 abstentions, 0 provider calls, no odds used, and no predictions. The report's `database_writes` field is 0.
- Isolated research ledger: one run record was inserted into `veltrix_ai_analyst.research_shadow_forecast_runs` with forecast_count 0 and status `NO_FRESH_UPCOMING_SNAPSHOTS`; idempotency is keyed by run_key with `ON CONFLICT DO NOTHING`. Sanitized artifact [14858063534](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45258094322#artifacts) contains both the full research report and sanitized summary.

## 5. Production publication and release readback

Read-only queries against the Neon production default branch returned:

- `predictions`: 0 rows.
- `prediction_market_probabilities`: 0 rows.
- `prediction_publication_events`: 0 rows.
- `published_predictions` view: 0 rows.
- `published_prediction_markets` view: 0 rows.
- Two historical model artifacts exist; both have `point_in_time_certified = false`.
- Latest research-ledger record is `NO_FRESH_UPCOMING_SNAPSHOTS`, forecast_count 0.

Stage 6 and Stage 7 artifacts continue to require `release_eligible=false`, `production_promotion=LOCKED`, and `value_betting=LOCKED`. No production prediction was created or published, and no release or value-betting gate was changed.

## Blockers and next engineering action

1. Reconcile the intended 03:17 UTC target with the active 00:00 UTC main cron; the 03:17 schedule was superseded before 24 November.
2. Investigate why no scheduled capture event was present by 04:02 UTC for the active 00:00 UTC cron. Verify workflow enablement and GitHub schedule delivery; do not dispatch or rerun to simulate a schedule.
3. After the next natural scheduled run, verify fresh import-run IDs and new observations, then the exact Stage 6 parent and snapshot freshness.
4. Preserve the six-hour Stage 7 gate. A new capture must supply fresh eligible snapshots; do not weaken the gate to force forecasts.
5. Keep production publication, promotion, and value betting locked until independent certification criteria are met.

This entry records a missing scheduled run and the last verified prior runtime chain. It does not claim a 24 November capture, Stage 6 materialization, or Stage 7 inference occurred.
