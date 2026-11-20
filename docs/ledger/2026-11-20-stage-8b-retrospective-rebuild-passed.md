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
