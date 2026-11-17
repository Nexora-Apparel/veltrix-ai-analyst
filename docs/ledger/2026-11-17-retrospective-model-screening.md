# Retrospective model screening — 2026-11-17

## Corpus snapshot

A read-only query against the dedicated `veltrix_ai_analyst` Neon database returned:

- 380 completed 5DollarFootballAPI fixtures with final scores.
- 20 provider-local team IDs represented in those completed fixtures.
- Four additional UNKNOWN source rows are not admitted as outcome labels.
- No canonical team aliases were merged for this screening run; the model keys teams by provider ID.

The data are used for exploratory personal-use model research under the project owner's directive. This is not a PIT-certified dataset: historical source publication and availability timestamps were not captured.

## Preliminary expanding-window comparison

A separate in-session numerical reproduction of the committed regularized, recency-weighted attack/defence Poisson algorithm was run against the 380-row query. Kickoff groups were kept intact. The first 75 fixtures formed the initial history; the remaining 305 fixtures were scored across 12 expanding event-time folds. Each fold fitted only on earlier kickoff groups. Dixon–Coles rho was held at 0.0; no calibration or hyperparameter selection was performed.

| Model | Evaluated fixtures | 1X2 Brier (lower) | 1X2 log loss (lower) |
|---|---:|---:|---:|
| Recency-weighted attack/defence Poisson | 305 | 0.61015 | 1.01722 |
| Recency-weighted league-average Poisson baseline | 305 | 0.64203 | 1.06332 |
| Elo-shifted Poisson (draw mass retained) | 305 | 0.61706 | 1.02761 |

The attack/defence component screened better than the league-average baseline in this run: approximately 4.96% lower Brier and 4.33% lower log loss. The simple Elo probability adjustment did not improve the Poisson result and should not be blended into the ensemble without further tuning and validation.

The attack/defence run's mean predicted goals were approximately 1.284 home / 1.021 away, versus observed 1.367 home / 1.016 away. Home-goal underprediction is a calibration diagnostic for later fold-contained tuning.

## Interpretation limits

- These figures are a preliminary numerical reproduction, not output from the committed Python CLI runner and not yet a CI-verified training artifact.
- The results are event-time retrospective only. They do not establish that historical inputs were actually available before each original kickoff.
- The corpus is one competition and one season. It is too small and narrow to claim broad-league generalization.
- No bookmaker benchmark, odds calibration, prospective paper results, or independent external holdout has been included.
- The Elo result is reported as a comparator only. It is not selected for the production ensemble.
- No production endpoint, Android integration, value-bet activation, or public prediction publication is authorized by this research report.

## Next research sequence

1. Complete CI for the attack/defence model, retrospective evaluator, odds contracts and Android build.
2. Run the committed read-only Python research runner against a controlled export/connection and preserve its exact output.
3. Add fold-contained hyperparameter selection for recency half-life, ridge strength and home advantage; reserve outer chronological folds for final scoring.
4. Estimate Dixon–Coles rho from inner out-of-fold scoreline predictions only.
5. Evaluate Elo independently and only include it in an ensemble if inner chronological validation shows repeatable gains.
6. Add additional competitions/seasons and prospective timestamped feature/odds collection before making general accuracy claims.


## Corrected Python evaluation and full-corpus training — 2026-11-17

The initial screening numbers above were an exploratory reproduction. They are superseded by the committed Python evaluator after the ridge-regularization correction and same-fold baseline implementation.

Successful workflow: https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44159228994

- 380 finished provider fixtures loaded.
- 75 initial training fixtures.
- 305 chronological evaluation fixtures across 12 expanding folds.
- Simultaneous kickoff groups remain intact.
- Corrected attack/defence 1X2 Brier: **0.6081835337**.
- Corrected attack/defence 1X2 log loss: **1.0153185492**.
- Mean scoreline log loss: **2.7326232988**.
- Same-fold recency-weighted league baseline Brier: **0.6420315331**.
- Same-fold league baseline log loss: **1.0633200835**.
- Relative improvement: approximately 5.27% Brier and 4.51% log loss.

This is retrospective event-time validation, not historical PIT-certified validation. It covers one competition/season and does not establish multi-league generalization.

## Full-corpus model artifact

A successful private training workflow fitted and persisted the full 380-result corpus to the dedicated Neon database:
- Artifact ID: `v1-5790da5427a7029b9267778728386b8d`.
- Dataset fingerprint SHA-256: `5790da5427a7029b9267778728386b8df2cd583b922a421341dc586c8d03b839`.
- Model family: `RECENCY_WEIGHTED_ATTACK_DEFENCE_POISSON`.
- Version: `attack-defence-poisson-v1`.
- 20 provider-local team coefficient sets.
- Training cutoff: `2026-11-14T19:30:00Z`.
- Project-owner training authorization declaration: `PROJECT_OWNER_PERSONAL_USE_AUTHORIZATION_2026-11-17`.
- `point_in_time_certified=false`.
- Deployment status: `RESEARCH_ARTIFACT_ONLY`.

The artifact row was independently queried from Neon and matched the training workflow output. The model artifact is private in the dedicated database; it was not committed to the public repository.

Elo ratings were retained as a separate research comparator and are not selected for the current ensemble. Dixon–Coles rho remains 0.0 and uncalibrated. No production prediction endpoint, Android integration, or value-bet activation was made.

## Ridge objective correction

The original attack/defence optimizer divided the ridge penalty gradient by total training weight along with the likelihood gradient. This unintentionally weakened regularization as sample volume increased. The corrected implementation applies the penalty to the normalized objective, and a regression test verifies that stronger ridge strength shrinks team effects.

The corrected model, baseline evaluator, final-corpus training runner, migration, private workflow and tests are merged to main. PR CI passed backend tests/lint and Android debug build.


## Nested-tuned v2 model artifact — 2026-11-17

PR #34 added the nested chronological tuner; PR #35 integrated it into the full-corpus trainer. Both are merged, and main-branch CI passed.

The successful v2 training run persisted:
- Artifact ID: `v2-5790da5427a7029b9267778728386b8d`.
- Model version: `attack-defence-poisson-v2-nested-tuned`.
- Training rows: 380; provider-local team IDs: 20.
- Inner OOF tuning: 34 chronological folds and 340 inner predictions.
- Selected half-life: 180 days.
- Selected ridge: 0.08.
- Selected Dixon–Coles rho: 0.10.
- Inner 1X2 Brier: 0.6188714654.
- Inner 1X2 log loss: 1.0305409710.
- Inner scoreline log loss: 2.7461398753.

The selected hyperparameters match the existing defaults for half-life/ridge; the inner tuning selected rho 0.10. The v1 artifact remains immutable and preserved. The v2 artifact remains research-only and not PIT-certified.

A separate nested outer walk-forward run is still in progress to evaluate whether this tuning generalizes to unseen chronological folds. Do not treat the inner OOF metrics as independent outer-test performance. No production endpoint or Android integration is enabled.


## Nested chronological outer evaluation — completed 2026-11-17

Workflow run [#44160528516](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44160528516) completed successfully on commit `5174259f072c24b9ef94d4992068f84a985217cb`. The expanding chronological evaluation ran before the idempotent v2 artifact persistence step.

- Completed fixtures loaded: 380.
- Initial training fixtures: 75.
- Held-out fixtures: 305.
- Outer folds: 12.
- Simultaneous kickoff groups remained intact.
- Nested-tuned attack/defence 1X2 Brier: **0.6124461060**.
- Nested-tuned attack/defence 1X2 log loss: **1.0215836752**.
- Mean scoreline log loss: **2.7313871693**.
- Same-fold league baseline 1X2 Brier: **0.6420315331**.
- Same-fold league baseline 1X2 log loss: **1.0633200835**.
- Relative to the league baseline, nested tuning improved Brier by approximately **4.61%** and log loss by approximately **3.92%**.
- Relative to the corrected fixed-parameter Python evaluation (Brier **0.6081835337**, log loss **1.0153185492**), nested tuning was worse by approximately **0.70%** Brier and **0.62%** log loss.

The selected parameters varied across outer folds; they were not stable enough to establish that the full-corpus v2 settings generalize. Fold selections included half-lives of 90/180/365 days, ridge values 0.08/0.25, and rho values from -0.10 to 0.05. The final full-corpus v2 artifact was then successfully re-persisted idempotently as `v2-5790da5427a7029b9267778728386b8d`, with 380 training fixtures, 20 provider-local team IDs, cutoff `2026-11-14T19:30:00Z`, `point_in_time_certified=false`, and `RESEARCH_ARTIFACT_ONLY`.

### Model selection decision

- Retain v1/fixed-parameter attack/defence Poisson as the current **best research candidate** because its same-fold outer metrics are better than the nested-tuned evaluation.
- Preserve v2 as a separate immutable research artifact; do not delete or overwrite it.
- Do not promote v2 to champion solely because its inner tuning selected rho 0.10.
- Elo remains a separate comparator and is not selected for an ensemble.
- Neither artifact is production-certified, PIT-certified, calibrated against timestamped market odds, or validated across multiple competitions/seasons.
- No production endpoint, Android prediction integration, value-bet activation, or public prediction publication is enabled.

### Next model research work

1. Diagnose fold-level parameter instability and compare fold-by-fold predictions, not only aggregate scores.
2. Add probability calibration only with calibration fitted inside each training fold and assessed on untouched outer predictions.
3. Add reliability diagrams, classwise Brier decomposition, calibration slope/intercept, and confidence intervals for paired score differences.
4. Expand the corpus across seasons and competitions before attempting a multi-league champion.
5. Keep Elo as a comparator until an inner-fold-selected ensemble shows repeatable outer-fold gains.
6. Do not use the current one-season retrospective metrics as a forecast-accuracy guarantee.



## Paired chronological fold-block bootstrap — completed 2026-11-17

PR [#39](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/39) was squash-merged as `7ab2610837e6ba5be0e222feb5373a4883ddce82`. Exact-head CI for `25f505c6aeeaeaef651562a42d955a011c09ea12` passed backend tests/Ruff and Android debug build.

Post-merge evaluator workflow [#44171335925](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44171335925) completed successfully. It read 380 FINISHED provider rows, used 75 initial training fixtures, and evaluated 305 fixtures across 12 expanding chronological outer folds. Simultaneous kickoff groups remained intact. The v2 research artifact was re-persisted idempotently as `v2-5790da5427a7029b9267778728386b8d`; no artifact replacement or production deployment occurred.

### Nested-v2 versus same-fold league baseline

| Metric | Nested v2 | League baseline |
|---|---:|---:|
| 1X2 Brier (lower is better) | 0.6124461060 | 0.6420315331 |
| 1X2 log loss (lower is better) | 1.0215836752 | 1.0633200835 |
| Mean scoreline log loss | 2.7313871693 | — |

Calibration diagnostics for the uncalibrated nested-v2 probabilities:
- Classwise ECE: **0.0394121500**.
- Top-label ECE: **0.0498733163**.

### Paired chronological fold-block bootstrap

The evaluator ran 5,000 deterministic resamples (seed `20261117`), resampling the 12 outer folds as blocks and weighting sampled folds by their held-out fixture counts. Differences are model minus league baseline; negative favours nested v2.

| Difference | Point estimate | 95% percentile interval |
|---|---:|---:|
| 1X2 Brier | -0.0295854271 | [-0.0417743132, -0.0177778528] |
| 1X2 log loss | -0.0417364083 | [-0.0596155640, -0.0248281955] |

Both exploratory intervals are below zero, consistent with the nested-v2 model outperforming the league-average baseline on this retrospective sample. This is not evidence that v2 beats fixed v1; the matched v1/v2 run is tracked separately.

### Limitations and disposition

- Only 12 chronological outer folds are available. Fold-block bootstrap intervals with so few blocks are exploratory and sensitive to which dates are represented; they are not a high-powered inferential guarantee.
- All 305 test fixtures come from one competition and one season. No multi-league or cross-season generalization claim is supported.
- Historical publication/availability timestamps remain absent. This is event-time retrospective evaluation, not PIT-certified validation.
- Identity review, duplicate adjudication, and source provenance constraints remain unchanged.
- No timestamped odds benchmark, bookmaker comparison, prospective paper ledger, CLV test, or live prediction settlement was included.
- Nested hyperparameter selections varied across outer folds (half-life 90/180/365 days, ridge 0.08/0.25, rho -0.10/0.00/0.05), so the final v2 parameterization is not established as stable.
- Earlier fixed-v1 outer metrics were numerically better than nested-v2, but the exact paired v1-v2 rerun is still required before selecting a champion.
- ECE is descriptive and bin-dependent. It is not sufficient alone to certify calibrated probabilities.
- v1 and v2 remain immutable research artifacts; neither is production/PIT-certified. No production endpoint, Android prediction integration, value-bet activation, or public forecast publication is enabled.

## Matched v1-v2 and calibration follow-up

PR [#40](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/40) merged as `43f393e632c026f33cb3fbee752523b701f07719`. It adds an evaluator that runs fixed-v1 and nested-v2 on the same chronological outer folds, rejects fixture/fold mismatches, and reports paired fold-block intervals for Brier and log loss. The private research workflow now runs this matched comparison before artifact persistence.

PR #40 also adds a tested scalar multiclass temperature-scaling utility. At merge time it was not yet integrated into the outer-fold evaluator. Calibration integration is being developed separately and must fit each fold's temperature only from inner out-of-fold predictions contained within that fold's training history; outer test labels remain excluded.
