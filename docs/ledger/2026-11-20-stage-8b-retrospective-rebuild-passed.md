# 2026-11-20 — Stage 8B retrospective rebuild passed

## Execution evidence

- CI run: [44712955417](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44712955417), job 136209024795, branch `stage-8b-statistics-ci-release`, head `e61791463e142a4afceaab363537ba853f37a4cb`.
- CI conclusion: success. Backend tests, Ruff lint, Android debug build and APK upload all completed successfully.
- APK artifact ID: `14618615613`; size 16,448,828 bytes; artifact SHA-256 `268da91198a0dba132cf0f7bed92d4e9a22acb1a200f323d31891a8a3d3dff96`.
- Research rebuild: [44713600712](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44713600712), job 136211231020, same branch and head. Every step completed successfully: read-only historical import validator, statistics-aware feature dataset build, retrospective report rebuild, paired chronological diagnostics and all three artifact uploads.

## Corrected source accounting

The generated report confirms the expected accounting invariant:

| Classification | Rows |
|---|---:|
| Total source rows | 386 |
| FINISHED with both scores | 380 |
| UNKNOWN without scores | 4 |
| SCHEDULED without scores | 2 |
| INVALID | 0 |

Only the 380 FINISHED rows were used as retrospective labels. The two valid upcoming fixtures were excluded as scheduled/unlabelled, not misclassified as malformed records.

## Retrospective model report

- Report artifact: `corrected-retrospective-research-report`, artifact ID `14618990915`, 38,510 bytes; ZIP digest `sha256:63a157e52f98651e06c7bff7987f829568c8279e147ff2dea24ec1131d551c66`.
- Internal report SHA-256: `14a69cc1d0b3b786d4a11808079b43ab0d3ffa97581e1136a3881e5cb8813ad5`.
- Dataset type: `RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED`; one competition, 20 teams, 380 fixtures, 2026-03-21 through 2026-11-14.
- 1X2 full-corpus prequential scores:
  - Elo: Brier 0.6333636621; log loss 1.0511312957.
  - Poisson: Brier 0.6305494554; log loss 1.0480440262.
  - Ensemble: Brier 0.6293348931; log loss 1.0458888491.
- Ensemble has the lowest point estimate in this retrospective comparison, but paired moving-block bootstrap intervals for all pairwise Brier and log-loss differences include zero. These results do not establish a statistically reliable winner. The diagnostics explicitly prohibit pooling this full-corpus prequential sample with the separate nested chronological walk-forward sample.
- No bookmaker odds were used. The report therefore does not demonstrate improvement over bookmaker Brier/log loss, nor does it certify any betting market or ROI.

## Statistics-aware feature dataset

- Artifact: `statistics-aware-retrospective-feature-dataset`, artifact ID `14618123576`, 653,709 bytes; ZIP digest `sha256:c9b9bdabd0c8a96eaac92c52de723aa2b635d30ca34f26f36995d5698f4de6c2`.
- Dataset SHA-256: `fd805256d0015f08e05f4a312d065fa8f8c00170227ac08e37ac10d11be7bf55`.
- 1,576 rows across seven competitions; 40 statistics-derived home/away feature fields.
- Non-null feature-cell coverage: home perspective 29,960/31,520 (95.05%); away perspective 30,060/31,520 (95.37%). At least one home statistics mean exists in 1,498 rows; at least one away statistics mean exists in 1,503 rows.
- All 1,576 rows are tagged `RETROSPECTIVE_EVENT_TIME_RECONSTRUCTION`; all have `source_available_before_target_kickoff=false`. Dataset-level `point_in_time_certifiable=false`, `validation_eligible=false`; every row is certification-ineligible. Current rights status is APPROVED, but retrospective rights approval does not establish historical pre-kickoff availability.
- These features are suitable for exploratory retrospective research only. They must not be described as PIT-qualified, used for prospective certification, or promoted into production inference based on this run.

## Paired diagnostics

- Artifact: `corrected-paired-chronological-diagnostics`, artifact ID `14619310095`, 3,841 bytes; ZIP digest `sha256:a474c5d3096f374e9d04470c339287ef48b07e7b70c3fff33b8c8b9973758101`.
- 380 fixtures; four chronological periods; 2,000 paired moving-block bootstrap resamples, block size 20 fixtures.
- The 95% intervals include zero for Elo-vs-ensemble, Elo-vs-Poisson and Poisson-vs-ensemble for both Brier and log loss. Descriptive retrospective comparison only; not PIT certification.

## Scope and safety boundaries

- The rebuild reused existing historical observations. No repeat collection or new 5DollarFootballAPI requests were required; no Odds API credits were spent.
- Import validation and dataset materialization were read-only. No production database writes, deployment, PR merge or production publication occurred.
- PR #123 remains open/unmerged at head `e61791463e142a4afceaab363537ba853f37a4cb`.
- Stage 7 prospective certification, production inference/publication and value betting remain locked. This successful CI/research run is engineering/research evidence only.

## Next actions

1. Keep the statistics-aware retrospective dataset isolated from prospective certification datasets.
2. Use it only for exploratory feature diagnostics and model research, with the non-PIT boundary carried into every report.
3. Build/evaluate feature effects on prospectively observed pre-kickoff snapshots joined only to strictly post-kickoff labels; accumulate sufficient distinct dates and settled outcomes.
4. Continue Stage 8B/8C integration and reliability calibration. Do not merge PR #123 solely because these workflows passed; review the complete PR and remaining Stage 8 exit criteria first.
5. Preserve existing Android UI; integrate only after a certified immutable artifact and publisher exist.


## PR integration status — post-rebuild check

- PR #123 remains open and unmerged. GitHub reports `mergeable=false`.
- Branch comparison against `main`: candidate is 119 commits ahead and 3 commits behind; the branches diverged from merge base `7039615d51a30609a67a944c050bd8b31ce20bce`.
- The three main-only commits add the default-branch historical evidence preflight workflow, enforce a read-only transaction in that preflight, and expose the bounded historical backfill workflow. Both main and the candidate branch contain different versions of `.github/workflows/historical-feature-evidence-backfill.yml`; the candidate must preserve its verified run behavior while incorporating the later default-branch safety refinements. The candidate also needs the main-only preflight workflow.
- Do not merge while GitHub reports non-mergeable. Next integration task is a deliberate workflow reconciliation against those three main commits, followed by fresh CI on the resulting exact head. The already successful CI/research runs remain valid evidence for their original tested head only; documentation-only commits and any subsequent workflow reconciliation are not thereby CI-verified.


## 2026-11-20 — PR #123 workflow reconciliation started

- Rechecked branch comparison: `stage-8b-statistics-ci-release` is 120 commits ahead and three commits behind `main`; merge base remains `7039615d51a30609a67a944c050bd8b31ce20bce`. The candidate still lacked the main-only historical entitlement preflight workflow.
- Updated the candidate backfill workflow to preserve its review-before-execution input and bounded collector command while verifying production database identity inside an explicit read-only transaction. The preflight remains opt-in/manual and does not collect historical fixtures.
- Added `.github/workflows/historical-feature-evidence-preflight.yml` to the candidate. It checks the expected Neon database in a read-only transaction, probes the 5Dollar entitlement endpoint, and explicitly performs no collection or database writes.
- Commits: backfill safety update `cb1c0f7ff46de5e8e48df27549b487452b8afdde`; preflight workflow `395d2672f0fbd6b4627350b6b4bf925871e774d7`.
- Fetch-back verified the backfill workflow content and blob SHA `697692a271e3e3a0d39a141a9e3bd07de767b164`. Preflight creation returned commit `395d2672f0fbd6b4627350b6b4bf925871e774d7`; a separate fetch-back and fresh CI are still required.
- No historical collection was dispatched, no provider collection requests were sent, no Odds API credits were spent, and no production database writes or deployments occurred.
- Next: fetch-back verify both workflows; inspect main-only commit patches and the remaining branch diff; update roadmap/ledger; run CI on the resulting exact candidate head. Do not merge until divergence is resolved and CI passes.


## 2026-11-20 — PR #123 workflow reconciliation review completed

- Reviewed all three main-only commits against the candidate branch:
  - `7eadce29f340bbed88ce2c3252744934910d38e3`: introduced the manual entitlement preflight workflow.
  - `7291c90c3cbf89fe0e5f13bbcb129c3a2c9152a9`: corrected that preflight to set and verify a read-only transaction.
  - `6b6c045a50572cf22f12d6ca95038fca81d91b36`: exposed the bounded historical backfill workflow on the default branch.
- Candidate preflight file was fetched back and is byte-for-byte content-equivalent to the corrected `main` version. It checks the expected Neon database within `SET TRANSACTION READ ONLY`, verifies `transaction_read_only = on`, probes provider entitlement, and performs no collection.
- Compared both complete backfill workflow files. Candidate retains the default-branch push parse-validation job, manual dispatch, preflight-only default, review-before-execution wording, bounded 10-request collector invocation and selected-ref behavior (GitHub Actions checks out the dispatch ref by default). Candidate additionally verifies Neon identity in an explicit read-only transaction with a connection timeout before any optional collection step. The main workflow's identity check was weaker and was not copied over the candidate's stricter guard.
- The three main-only changes are therefore functionally represented on the candidate branch; the candidate deliberately keeps its stronger execution safeguards. No wholesale merge/cherry-pick was performed, and no provider collection was dispatched.
- Corrected earlier reconciliation note: both workflow files have now been fetched back successfully; the preflight is no longer awaiting fetch-back verification.
- Current compare and PR metadata still require a fresh check after this ledger update. No PR merge, production deployment, database writes, historical collection, or Odds API spend occurred.
- Next: update roadmap reconciliation status, verify the exact new PR head and fresh CI, then proceed to point-in-time prospective feature/model integration. Existing retrospective event-time reconstruction remains excluded from production inference and prospective certification.


## 2026-11-20 — PIT fold correction, shadow inference and integration checkpoint

### Point-in-time fold leakage correction
- Found that expanding-window validation admitted historical labels observed after a validation fixture's prediction cutoff but before its kickoff. This was a real forecast-time leakage path.
- Added `ExpandingFold.validation_cutoff_at`, defined as the earliest prediction cutoff in the validation block. Training labels must be strictly earlier than this cutoff; validation kickoff remains a separate boundary.
- Enforced `train_cutoff_at < validation_cutoff_at < validation_start_at` in fold construction/evaluation, and required each validation row's own prediction cutoff to be at or after the fold cutoff and before kickoff.
- Added the cutoff to serialized dataset manifests and evaluation reports; corrected protocol metadata to distinguish feature availability at-or-before prediction cutoff from label availability strictly-before cutoff.
- Added regression coverage for a label observed after the prediction cutoff but before kickoff, plus evaluator rejection of corrupted fold cutoff metadata.

### Shadow forecast pipeline
- Added `backend/app/research/prospective_shadow.py` and `backend/scripts/build_prospective_shadow_predictions.py`.
- The read-only dataset manifest now exposes `training_only_rows` (already included in its dataset hash) so the shadow builder can train from verified historical result labels.
- Shadow training accepts only canonical, rights-qualified labels observed strictly before the earliest selected target cutoff; it rechecks rights at both target cutoff and actual training cutoff.
- Shadow output is capped at 25 upcoming fixtures, rejects snapshots older than six hours, uses a single common cutoff-safe training pool, records provenance hashes and model diagnostics, and never writes to Neon or calls a provider.
- The initial probability model uses historical goal outcomes only. Snapshot statistics/events are audited and reported but are not used as probability inputs until prospective feature validation exists. Dixon-Coles rho is estimated only from eligible inner prospective folds; otherwise it remains zero.
- All shadow outputs explicitly remain `NOT_PUBLISHED`, production promotion LOCKED and value betting LOCKED.
- Added `.github/workflows/prospective-shadow-predictions.yml`, scheduled for 05:00 UTC (06:00 WAT), with manual dispatch and a six-hour freshness gate. It is read-only and does not call The Odds API or Telegram.
- Added regression tests for cutoff/rights selection, stale-snapshot rejection and insufficient training evidence.

### Data audit — verified at 2026-11-20
- Prospective snapshots: 59 across seven competitions and six kickoff dates, all from the 19 November capture window.
- Prospective settled labels: 0. Production predictions/published predictions: 0. Two existing model artifacts remain research-only and not PIT-certified.
- The first snapshots were sparse in recent features: 53/59 had no eligible home-team recent history and 54/59 had no eligible away-team recent history. The historical statistics backfill completed after those snapshot cutoffs, so it must not be retroactively injected into them.
- Separate training-label audit: 996 canonical, rights-qualified historical result labels across seven approved competitions; 990 were available before the earliest 19 November snapshot cutoff and all 996 before the last snapshot cutoff. These may seed future-facing model training only when their recorded import-completion times precede the target cutoff.
- By the next scheduled capture cutoff (2026-11-21 03:00 UTC), 1,576 completed source matches across the seven competitions had statistics available and rights approved for feature engineering/model use; 1,575 also had non-empty event arrays. This is future-target evidence, not retrospective historical PIT certification.
- The 19 November 11:23 UTC scheduled capture run reused import run IDs 12–18 and reported `SKIPPED_ALREADY_VALIDATED`; it did not create a second capture. Stage 6 materialized the existing 59 snapshots. No 20 November `prospective_capture` import run was present at the audit time.
- The daily capture workflow remains configured for 03:00 UTC. The next expected scheduled opportunity is 21 November 03:00 UTC; if it does not run, a manual workflow dispatch is required. Do not backdate or mutate existing snapshots.

### CI and PR integration
- CI run 44720976619 passed on implementation commit `e099a4256e143c4d855f3eb2ff8106fe18ddfefe`: backend tests passed, Ruff passed, Android debug build passed.
- APK artifact ID `14622330651`, 16,448,831 bytes, SHA-256 `252366cdeeba4d68ca942c4832b9dd4750dc8213768533482d3419c313e009c6`.
- The initial lint failure in run 44720729600 was corrected (TypeError for invalid input type; import ordering); the successful run above verifies the corrected implementation tree.
- Reviewed all three main-only commits. Candidate preflight is content-identical to corrected main. Candidate backfill workflow retains push validation and manual preflight/execute controls while adding stricter explicit read-only Neon identity verification; main's weaker identity check was not copied.
- Created merge commit `5ef8854d20a1fd2df1798d0d4ee752ed74f078a4` with parents candidate `e099a4256e143c4d855f3eb2ff8106fe18ddfefe` and main `6b6c045a50572cf22f12d6ca95038fca81d91b36`, preserving the reviewed candidate tree `c59f1761a6ddebbec7df27f1953cddb93001c660`.
- GitHub compare now reports 151 commits ahead, 0 behind; PR #123 is mergeable=true, state `unstable`. This is ancestry reconciliation only; PR #123 was not merged.
- Vercel status remains failure: deployment rate limited, retry after the 24-hour window. Do not retry deployment or merge while the required deployment status is failing.
- No new provider requests, Odds API credits, production DB writes, production predictions or publication occurred in this checkpoint.

### Next actions
1. Verify the 21 November 03:00 UTC capture and Stage 6 materialization; require fresh snapshots with the 1,576 statistics/event observations available before their cutoffs.
2. Run the read-only shadow workflow at 05:00 UTC only if fresh snapshots exist; inspect its artifact, model convergence, 25-fixture cap, training cutoff, feature coverage and abstentions.
3. Continue prospective labels and cutoff-correct walk-forward evaluation. Build reliability calibration only from eligible prospective outcomes.
4. Keep production publication, value betting and Android live prediction integration locked until model, reliability and certification gates pass. Preserve the existing Android UI.
5. Recheck Vercel quota/status after the 24-hour retry window before any deployment or PR merge.


## 2026-11-20 — Published history and evidence-backed settlement integration

### Research shadow inference
- Added `backend/app/research/prospective_shadow.py` and `backend/scripts/build_prospective_shadow_predictions.py`.
- Shadow training selects only canonical, rights-qualified result labels observed strictly before the earliest target prediction cutoff. Rights are rechecked at the target cutoff and the actual training cutoff.
- It trains from historical goal outcomes only, records a deterministic training-data SHA-256, caps forecasts at 25, rejects snapshots older than six hours, and records feature coverage without using unvalidated snapshot features as probability inputs.
- No provider requests, odds requests, database writes, publication or Telegram messages.
- All forecasts remain `NOT_PUBLISHED`; production promotion and value betting remain LOCKED.
- The daily shadow workflow runs at 05:00 UTC and also triggers after successful Stage 6 materialization, so a long-running capture cannot permanently race the shadow job. A stale scheduled run safely reports no fresh snapshots.

### Append-only settlement ledger and public history
- Added migration `018_prediction_settlement_ledger.sql`:
  - append-only `prediction_settlement_events`;
  - unique prediction/source-observation key for idempotency;
  - source observation, sighting, provider response, rights approval, payload hash and response hash retained;
  - insert trigger rechecks publication state, verified canonical fixture/source link, exact final score and fixture identity, system-observed timestamps, source response provenance, rights scope/validity and monotonic correction ordering;
  - `latest_prediction_settlements` view exposes the newest evidence-backed result per prediction.
- Migration 018 was applied successfully by the CI PostgreSQL migration test on an ephemeral test database. It has **not** been applied to production Neon.
- Added `GET /v1/predictions/history`, returning only previously published past fixtures, their market probabilities, latest verified final score, settlement timestamp and publication state. Pending results remain score-null.
- Added a dry-run-first `backend/scripts/settle_published_predictions.py`. It uses only 5DollarFootballAPI observations already in the database; `--execute` inserts only new, current, rights-qualified results. Scheduled execution is set for 06:00 UTC; manual dispatch defaults to read-only dry-run.
- Added the settlement workflow and regression/contract tests.
- Updated the existing Android History tab and API client to display published predictions, verified full-time scores and pending-result states. Existing screen design was preserved; no redesign.

### CI and preview deployment — verified
- CI run 44724562661 passed on commit `3708b13cdd74e0f723483f46c92bd3c4b2357675`.
- Backend: 475 tests passed; Ruff: all checks passed.
- Android debug build: BUILD SUCCESSFUL.
- APK artifact ID `14623626293`, size 16,453,448 bytes; uploaded ZIP SHA-256 `7003c9dc745ceda25c9bcb4d6f92bd2c664ba195ed7cce08fb65da3e84ae99d7`.
- Vercel preview deployment `dpl_F8o1xVqgDanA322EXziK2v5xxSSc` is READY for the candidate branch at `https://veltrix-ai-analyst-4dmsp61up-nexora-apparel.vercel.app`.
- Preview `/health` returned HTTP 200. Preview `/ready` reports `database=not_configured`; preview environment has no `DATABASE_URL`, so its prediction endpoints cannot be end-to-end tested there without preview database configuration.
- Production `https://veltrix-ai-analyst-api.vercel.app/ready` returned HTTP 200 with database connected, migrations current and prediction storage available. Production `/v1/predictions` returned an empty list.

### Production Neon state — read-only verified
- Latest applied migration remains `017_append_only_prospective_snapshot_labels.sql`; migration 018 is not yet applied.
- Prediction rows: 0. Published prediction events: 0.
- Prospective snapshots: 59. Prospective snapshot labels: 0.
- `prediction_settlement_events` does not yet exist in production.
- No production DB writes, migration application, publication or settlement insertion occurred in this checkpoint.

### Prospective capture exception
- Read-only import-run query found **zero** `prospective_capture` runs started on 20 November UTC.
- Latest scheduled capture remains run 44514389412 on 19 November 11:23 UTC; Stage 6 materialization run 44514513198 completed successfully after it.
- Next expected capture is 21 November 03:00 UTC. The capture workflow supports manual dispatch, but the connected GitHub toolset does not expose a workflow-dispatch action; if the next schedule is missed, dispatch it from GitHub Actions UI. Do not fabricate or backdate snapshots.
- The 1,576 statistics/event observations remain eligible only for future target snapshots whose cutoffs follow their database-observed times.

### PR and release boundary
- PR #123 candidate head at CI verification: `3708b13cdd74e0f723483f46c92bd3c4b2357675`.
- GitHub compare: 189 commits ahead, 0 behind; PR mergeable=true, mergeable_state=`clean`.
- Vercel preview status is success. PR #123 remains open and unmerged; no production deployment was made.
- The 90-day prospective certification requirement remains independent of historical training. Value betting and production publication remain LOCKED.

### Next actions
1. Verify the 21 November 03:00 UTC capture and the automatic Stage 6 materialization; require fresh, immutable snapshots.
2. Inspect the resulting shadow artifact and confirm cutoff-valid training count/hash, model convergence, fixture cap, feature coverage and abstentions.
3. Once migration 018 is applied through the approved release path, verify the production history endpoint and run the settlement worker in dry-run mode before enabling scheduled inserts.
4. Continue prospective settled labels and corrected prediction-cutoff walk-forward evaluation; build reliability calibration only from prospective evidence.
5. Preserve the existing Android UI and connect it to production history only after the production API deployment and migration are both verified.



## 2026-11-20 — Stage 8B production release and migration 018 verified

- PR #123 merged to `main` as commit `1bdb07b1f87c8fe17ea6698345f99d9323222ae9`.
- Production migration workflow [44729468637](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44729468637) completed successfully. Migration `018_prediction_settlement_ledger.sql` is applied with checksum `50757ee84f83ea1cb70b71b9ca5ef50879a7589d2af720feac6c1bb36e972aca`; its append-only settlement table, evidence guard and latest-settlement view were verified by the workflow.
- Read-only Neon fetch-back at 2026-11-20 11:40 UTC confirms migration 018 is latest. Production counts remain: 59 prospective snapshots, 0 prospective labels, 0 prediction rows, 0 publication events and 0 settlement events. No forecasts were published and no settlement events were inserted.
- Production Vercel deployment `dpl_H6kiYwJhiuu5c893hqmUspytK2ya` is READY for commit `1bdb07b1f87c8fe17ea6698345f99d9323222ae9`. Production `/health` and `/ready` return HTTP 200. `/v1/predictions/history` now returns HTTP 200 with an empty `predictions` array, correcting the previous 422 route collision.
- Main-commit CI [44729468573](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44729468573) passed backend tests/lint and Android debug build. APK artifact ID `14626240750`, 16,453,457 bytes.
- Read-only retrospective rebuild [44729468648](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44729468648) passed and uploaded report artifact `14626225756`, statistics-aware dataset `14625637140`, and paired diagnostics `14625243063`.
- Prospective evaluation [44729468654](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44729468654) passed its workflow but returned `INSUFFICIENT_PROSPECTIVE_DATA`: 0 eligible fixtures, 0 folds, 0 settled labels and 0 distinct prospective dates. Production promotion and value betting remain LOCKED.
- The 20 November scheduled capture [44725750217](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44725750217) failed after 13 provider requests across seven scopes (58 records seen, 5 inserted, 0 duplicate counters, 1 quarantined record). Five completed scopes were rejected by a validator reconciliation defect: repeated fixtures across separate provider responses were counted as one entity rather than one response-scoped sighting. France Ligue 1 also stopped on `PROVIDER_FIXTURE_IDENTITY_CONFLICT`; this is retained as a genuine identity blocker and must not be bypassed. No Odds API credits were used.
- PR #124 `fix/prospective-capture-sighting-reconciliation` adds response-scoped sighting reconciliation, a regression test for the same fixture appearing in separate responses, and partial-scope batch handling. Validated scopes may proceed to Stage 6 while conflicted scopes remain excluded. PR #124 is open; its code is not yet CI-verified or merged. Vercel preview status is currently blocked by the free-tier daily deployment limit.
- The candidate preview's missing `DATABASE_URL` was not populated with production credentials. Production is deployed with its existing production database configuration; preview isolation remains intentional.

### Next actions
1. Verify CI on PR #124 and review its regression result before merge.
2. Keep France Ligue 1 excluded until its provider fixture identity conflict is independently reconciled.
3. After Vercel quota resets, merge/deploy the validated capture correction; then verify Stage 6 materializes only independently validated scopes.
4. Check the next capture opportunity without repeating today's 13 provider requests or mutating existing snapshots.
5. Continue prospective labels and cutoff-correct evaluation; keep all production publication and value betting gates locked until certification evidence passes.
