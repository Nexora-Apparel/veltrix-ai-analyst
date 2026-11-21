# 2026-11-21 — Supervisor review and shrinkage repair v3.1

## Delta from v3

- Replaced the v3 k grid with `{0.5,1,2,4,8,16,32,64,128}`; half-life remains `{180,365,730}` days.
- Added preregistered probability blend weights `{0.25,0.5,0.75,1.0}`, with `p=w*p_model+(1-w)*p_climatology`.
- Added ten-bin HOME/DRAW/AWAY reliability tables, calibration slope/intercept, >0.80 probability counts and hit rates, paired date-block bootstrap comparisons against climatology and plain scaled Poisson, and competition-level breakdown.
- Fixed the convergence rule before evaluation: gradient L2 norm <=1e-7 AND relative objective change <=1e-10 for two consecutive accepted steps; max 200 Newton iterations; no post-hoc tolerance relaxation.
- Recorded exact archived-equivalent team k values: fold 1 128.3802704829587; fold 2 173.29424410186596; fold 3 206.5352382546307; fold 4 269.2584048267363 (diagnostic only).
- Canonical config SHA-256: `14333ab670983a692605e91705bc001707bc3c2319c1e94f116ddc15adcb44dd`.

## Fold-4 leakage review — read-only source artifact inspection

Source artifacts: Stage 6 dataset artifact 14694463354 and forecast artifact 14694089682 from the audit's pinned inputs. No model was refit and no candidate grid was evaluated.

- Fold 4 partition reproduced from the 996 training rows: 835 train rows, 161 test rows, cutoff 2026-10-28 17:30:00 UTC.
- Training kickoff timestamps at/after cutoff: 0.
- Exact cross-fold duplicates by canonical fixture ID: 0; provider fixture ID: 0; same-direction teams/date: 0; unordered teams/date: 0.
- Training labels with `label_observed_at >= fold cutoff`: 835/835.
- Training labels observed after their own kickoff: 835/835 (expected for settled results, but not proof they were available at a historical forecast cutoff).
- Per-row historical `prediction_cutoff_at` on training records: 0/835. Thus own-prediction-time availability cannot be established.
- Dataset exposes only aggregate `fixture_identity_rows=1053`; it does not include the 28 unresolved identity-case records. Those cases cannot be cleared from the supplied artifact.
- Therefore fold 4's 0.905 log loss for k=0.5 is not trustworthy as point-in-time evidence. It remains previously examined and is not clean validation.

### Requested high-probability attribution — unavailable without a new real-data evaluation

The sanitized audit JSON and source artifacts do not preserve per-test-fixture probabilities for the fold-4 k=0.5 fit, nor the per-fixture competition/outcome attribution needed to count forecasts above 0.80 and calculate their hit rate. No refit/replay was run because real-data evaluation requires the owner-dispatched workflow. These metrics remain required in the v3.1 evaluation output.

## Controls

No production or default optimizer change, quarantine change, lock change, feed enablement, database write, provider call, Odds API use, Telegram notification, merge, or workflow dispatch. PR #143 remains draft. All real-data evaluation remains owner-dispatched and read-only.


## Implementation delta — 2026-11-21

- Added opt-in `optimizer="newton"` to `backend/app/models/hierarchical_poisson.py`; default remains `gradient_descent`. The new path uses the analytic weighted-Poisson Hessian, unchanged averaged-objective ridge scaling, diagonal damping, partial-pivoting linear solve, and Armijo backtracking.
- Added fixed convergence guard in the implementation: max 200 iterations, gradient tolerance from the caller (v3.1 uses 1e-7), relative objective tolerance 1e-10, two consecutive accepted steps. Failure raises ArithmeticError and does not return a model.
- Added deterministic equivalence tests against gradient descent and L-BFGS, plus singular linear-system and explicit non-convergence tests.
- Added `shrinkage_repair_metrics.py` with blend, ten-bin reliability, logistic calibration slope/intercept, >0.80 probability hit-rate, competition breakdown, and paired date-block bootstrap helpers.
- GitHub Actions CI run 44918029389 was observed pending at ledger update time; backend and Android jobs were still in progress. No pass is claimed.
- PR #143 body updated to v3.1 and accurately lists remaining evaluator, settlement scorer, workflow, and CI verification work.
- No candidate grid evaluation or real-data fit was run. No workflow dispatch occurred.
- Current branch head at this checkpoint: `f9af5b35c87f6731273306bfe00b29f4d604463c`.


## v3.1 freeze and evaluation scaffolding — 2026-11-21

- Added deterministic selection rule before any grid evaluation: primary = arithmetic mean of the three fold-level mean 1X2 log losses (equal fold weighting); secondary = arithmetic mean of fold-level multiclass Brier; tie-break larger k, then longer half-life, then larger blend weight. Any failed/missing fold excludes the candidate and is reported.
- Updated canonical v3.1 config SHA-256 after freezing that rule: `a6b0f5484a34e4375c02c0b96bb8f0ed4e696a055fd06b1f6bf4a054fcabba24`. No candidate grid was evaluated.
- Added `backend/app/research/shrinkage_repair_evaluation.py`: chronological development-fold selector, recency-scaled k ridge conversion, probability blend, climatology/plain pooled Poisson comparisons, paired date-block bootstrap, reliability/calibration/extreme probability/competition diagnostics. It fails closed unless training labels were observed before each fold cutoff.
- Added `backend/app/research/prospective_shrinkage_settlement_scorer.py`: read-only frozen-hash settlement scoring with canonical fixture deduplication, timestamp checks, exclusions, and calibration/extreme-probability outputs.
- Added tests for the settlement scorer and calibration helpers.
- Added owner-dispatched workflow `.github/workflows/shrinkage-repair-evaluation.yml`; no schedule or push trigger. It pins evaluation commit, dataset/forecast run and artifact IDs, dataset SHA, and v3.1 config SHA. It downloads artifacts read-only, verifies fingerprints, runs focused tests and development selection, and uploads the aggregate report.
- Updated CI actionlint command to lint the new workflow.
- Newton model result now exposes relative objective change for reporting.
- CI runs 44918029389, 44918267482, and 44918298716 were cancelled during rapid branch updates/concurrency; no backend test or lint pass is claimed. A fresh exact-head CI result is still required.
- Workflow dispatch is not authorized and was not performed. Existing 996-row artifact fails the fold-4 point-in-time availability check (835/835 labels observed at/after fold-4 cutoff), so it is not a valid candidate-selection dataset. No real-data run was performed.
- PR #143 remains draft. The selection workflow is drafted but not ready for owner dispatch until exact-head CI passes and the prospective settlement export/score path is integrated and validated.


## Final checkpoint — 2026-11-21

- Added Newton relative-objective-change telemetry to the fitted model result and development report. L-BFGS retains its original four-value return contract; an intermediate return-contract regression was found by source inspection and corrected before any successful CI claim.
- Corrected development recency weighting to use each fold's prediction cutoff, not the latest training kickoff. Training rows are admitted only when both kickoff and label-observation timestamps precede that cutoff.
- Added owner-dispatched evaluation workflow with inputs: exact evaluation commit SHA; dataset run ID/artifact ID/dataset SHA; forecast run ID/artifact ID; frozen config SHA. The workflow has no schedule or automatic trigger and is not dispatched.
- Added prospective settlement scorer unit tests. The scorer accepts frozen-hash forecast and settlement JSON, joins by canonical fixture ID, enforces post-2026-11-21 settlement timing, and is read-only.
- Workflow remains **NOT READY FOR OWNER DISPATCH**: prospective settlement export/scoring is not yet integrated into an executable owner workflow; exact-head CI has not completed successfully; fold-4 per-fixture high-probability attribution is absent from the pinned artifacts.
- Current implementation checkpoint commit: `3ac024ea8c4341f13da1b621d5bab54f109d9793`. Subsequent ledger-only commit records this checkpoint.
- Quarantine, production-promotion lock, value-betting lock, and feed state unchanged. No real-data evaluation, workflow dispatch, provider/odds call, database write, Telegram notification, merge, or production-default change.


## Supervisor amendment v3.2 — 2026-11-21

- Corrected leakage interpretation: `label_observed_at` records bulk-ingestion time and is not a historical availability signal. The leakage checks supplied by the owner are zero training kickoffs at/after cutoff, zero cross-fold fixture-ID matches, zero same-team/same-date matches, goals-only model inputs; 28 identity cases remain unresolved. Fold 4 is statistically suspicious but not proven invalid by ingestion timestamps.
- Preregistered retrospective historical availability: result available at kickoff + 3 hours; training rows require kickoff + 3 hours strictly before each fold cutoff. All outputs are labelled `RETROSPECTIVE_NOT_PIT_CERTIFIED`; this supports SHADOW-tier research display at most, never PIT certification.
- Expanded k grid to `[0.5,1,2,4,8,16,32,64,128,256]`; half-lives `[180,365,730]`; blends `[0.25,0.5,0.75,1.0]`. Selection rule and Newton stopping rule unchanged.
- Canonical v3.2 config SHA-256: `90aea1d84cbe2301f71f5e3d6910d913ae2d1b79c7658319e5cf3ee0817df62a`. No evaluation has been run.
- Pinned artifacts verified available and digests recorded: Stage 6 run 44873016040 / artifact 14694463354 / ZIP SHA-256 `3a2ebfb7dd94899bc1cf5000bb365c440753afcfa474869a733bbeeda0a1ad81`; shadow run 44873166128 / artifact 14694089682 / ZIP SHA-256 `44164d6e9ead148b6fa0e663f81bde18ad5f75e839143e408a2ecce98cc7f16f`. Dataset fingerprint `80148b3f0f42e70d94391d9283c42f35b5b92e1631a9a1cb7baee899373dad0c`; training pool `d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262`.
- Replaced evaluator with a four-window chronological fold builder. Development grid is folds 1-3 only; fold 4 is replayed for the selected config and k=0.5 using selected half-life/blend, as a previously examined sanity check.
- Aggregate report includes the full development loss surface, selected config, baseline paired date-block bootstrap intervals, reliability/calibration, >0.80 hit rate, competition breakdown, expected-goal/P(home) dispersion, and fold-4 high-probability gain attribution. It emits no fixture IDs, team names, or scores.
- Replaced workflow with manual-dispatch-only, read-only workflow. It validates exact merged commit ancestry, pinned artifact IDs/names, ZIP digests, embedded content hashes and row counts; uploads one sanitized JSON with 30-day retention. No schedule or write permissions.
- The prior CI run 44918617920 passed backend tests and Android build but failed Ruff only on import ordering in the evaluator and metrics modules. The CI actionlint step passed. This has been corrected in the v3.2 batch.
- No evaluation, workflow dispatch, merge, feed change, provider/odds call, DB write, Telegram notification, or lock change has occurred. Fold 4 remains previously examined and cannot count as independent validation.


### CI result and final workflow correction — 2026-11-21

- Exact v3.2 head `692e118ecc9a7552e1bdc20fc1686416197ee000`, run `44920132842`: backend tests passed `520 passed, 1 warning`; actionlint passed; Android debug build passed. Backend job failed only Ruff import sorting in `shrinkage_repair_metrics.py`. No other failures were reported.
- Corrected the remaining metrics import order, added a focused retrospective availability test proving bulk `label_observed_at` is ignored and kickoff+3h is enforced, and fixed the workflow's missing `DATASET_SHA256` environment binding in the archive content-hash check.
- The workflow remains manual-only, read-only, and uploads exactly one sanitized aggregate JSON. It has not been dispatched.


### Second CI correction — 2026-11-21

- Exact head `b78b1d094cfb31218b24afc915fa0a304cb2f295`, run `44920316416`: 521 backend tests passed with 1 warning; actionlint passed; Android debug build passed. Backend job failed only Ruff I001 in `shrinkage_repair_metrics.py`.
- Applied Ruff's exact suggested ordering (plain imports before from-imports). No other source or configuration changes.


### Third CI result and spacing correction — 2026-11-21

- Exact head `42df084cc2e06d5a2730f140143a331c694dc9b8`, run `44920661558`: 521 backend tests passed with 1 warning; actionlint passed; Android debug build passed. Ruff I001 remained in the metrics module because the import block had two blank lines before the module constant; this is the sole reported lint issue.
- Removed the extra blank line after imports. No runtime code or evaluation logic changed.


### v3.2 exact-head CI green — 2026-11-21

- Exact head: `650479155df36f2ee04f9faa0fc747e6de51b0f4`.
- GitHub Actions CI run: `44920843696` — SUCCESS.
- Backend job `136896317410`: actionlint PASS; pytest `521 passed, 1 warning`; Ruff PASS.
- Android job `136896317606`: debug APK build PASS; artifact upload PASS.
- This is the first successful CI head for the v3.2 implementation. No real-data evaluation or workflow dispatch was run.
- Evaluation workflow is now structurally ready for the owner-controlled merge/dispatch sequence: manual `workflow_dispatch` only; contents/actions read-only; exact merged commit SHA and main ancestry validation; pinned dataset/forecast run IDs, artifact IDs, names, ZIP digests, embedded dataset/training fingerprints and row-count checks; one aggregate sanitized JSON artifact with 30-day retention.
- Owner next step: review and merge PR #143. After merge, re-read `main`, verify the workflow file and config hash on main, then provide the exact main commit SHA and dispatch input values. Do not dispatch before owner instruction.
- No merge, dispatch, feed re-enable, provider/odds request, database write, Telegram notification, production promotion, or lock change.

### Artifact fingerprint preflight correction — 2026-11-21

- Corrected the evaluation workflow to verify dataset_sha256, recompute training_data_sha256 from training_only_rows using the same projection as shadow_model_audit.training_data_sha256, and require both forecast fingerprints to match. All four checks remain fatal.
- The stored training_pool_sha256 is now logged as informational metadata only. The audit helper defines it as canonical SHA-256 over the complete training_only_rows JSON array (all fields, original array order). By contrast, training_data_sha256 sorts by (kickoff_at, fixture_id) and hashes the model-consumed identity, goal labels, and label provenance projection. These are different quantities.
- Added synthetic-fixture CI tests: matching model fingerprints pass even when the stored pool hash differs; an incorrect recomputed training fingerprint, dataset fingerprint, or forecast fingerprint fails closed.
- Expanded workflow archive-layout validation to require exactly one expected JSON file in each pinned ZIP. Backend dependencies are installed before importing the shared audit fingerprint helper.
- Read-only pinned-artifact preflight: ZIP digests match; each archive contains exactly its expected JSON file; 996 training rows and 25 forecasts; recomputed training fingerprint d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262; observed informational pool fingerprint 823fb3894d40153217cad1223808d059dd8ecaef548326b39ef19ceb1c01ecae; dataset and forecast dataset fingerprints match 80148b3f0f42e70d94391d9283c42f35b5b92e1631a9a1cb7baee899373dad0c.
- All 996 training rows have timezone-aware ISO-8601 kickoff and label-observation timestamps, non-empty competition/team IDs, and valid non-negative goal labels. Four non-empty folds satisfy kickoff_at + 3 hours strictly before each fold cutoff for every training row. No real-data model evaluation was run.
- PR #143 remains open. No workflow dispatch, merge, admission, route/feed change, provider/odds request, database write, Telegram notification, quarantine change, or lock change occurred. Await exact-head CI before reporting ready for owner merge.
- Exact-head CI run 44923142819 on the initial amended tree: actionlint PASS; pytest 524 passed, 1 warning; Android build/upload PASS. Ruff reported one TRY004 type-specific exception lint issue in the new missing-training-rows guard; changed that guard to TypeError before the final exact-head CI attempt.
