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
