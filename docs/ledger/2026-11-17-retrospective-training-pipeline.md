# 2026-11-17 — Retrospective model development authorization and first training pipeline

## Owner directive
The project owner explicitly directs the team to use the historical data already collected for personal-use model development and training. This is not a request for further permission paperwork. Treat the existing corpus as authorized for this project's personal-use model research under the owner's declaration. Preserve the source provenance and any explicit source-level limits already recorded. Do not reopen this authorization question in routine development.

This workstream supersedes older progress statements that broadly prohibited model training on the collected corpus. It does not relabel retrospective research as point-in-time-certified historical replay.

## Dataset policy
- Source: 5DollarFootballAPI, source ID `5dollarfootballapi`, Brazil Serie B competition ID `522514093`.
- Preserve provider-native team IDs as the initial identity namespace. Do not silently merge cross-provider or real-world identities.
- Use completed FINISHED rows with both goals as supervised outcome labels.
- Preserve and exclude UNKNOWN rows without scores.
- Build features only from matches with strictly earlier kickoff times. Simultaneous kickoff fixtures are scored from the same pre-batch state and only update model state after the entire batch.
- Historical lagged results are valid for retrospective research, but source publication/availability timestamps were not captured. Outputs must be labeled `RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED`; do not present them as historically reproducible pre-match forecasts or prospective production predictions.

## Initial implementation
- `backend/app/models/retrospective.py`: smoothed recency-weighted team attack/defence rates, draw-shrunk Elo 1X2 probabilities, prequential scorecards and training-only Dixon-Coles rho fitting.
- `backend/scripts/train_retrospective_research.py`: read-only Neon extract, score/identity namespace checks, exclusion accounting, deterministic JSON report and SHA-256 manifest.
- `backend/tests/test_retrospective_training.py`: regression tests for draw Elo updates, strictly prior feature history, simultaneous kickoff isolation, duplicate fixture rejection and model scorecards.
- Fixed a latent Elo defect: drawn matches previously reached a code path where the rating delta was not initialized.

## Accuracy-improvement safeguards
- Use prequential/chronological scoring: each fixture is predicted before its result is added to model state.
- Fit Dixon-Coles rho only from prior results and refresh it at controlled intervals; no target or future outcome enters the fit.
- Compare Elo, Poisson/Dixon-Coles and their fixed-weight ensemble using multiclass Brier and log loss.
- Treat current hyperparameters and ensemble weights as initial baselines, not certified optimums. Tune only with nested chronological validation once the first report is available.
- Do not train on post-match corners/cards as pre-match predictors. They may be retained as outcomes or descriptive diagnostics only.
- No production prediction API or Android/backend integration is enabled by this research pipeline.

## Next actions
1. Pass CI for the new retrospective model code and tests.
2. Execute the read-only training runner against `veltrix_ai_analyst`.
3. Inspect the generated report, exclusions, calibration and model scorecards.
4. Improve rate priors, recency decay, Elo parameters, Dixon-Coles fitting and ensemble weights through chronological tuning.
5. Expand to additional authorized collected competitions/sources only after validating their data contracts and retaining source-local identities.
