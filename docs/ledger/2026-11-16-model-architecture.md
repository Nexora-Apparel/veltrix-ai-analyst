# Project Ledger Entry — Model Architecture Specification

**Date:** 2026-11-16  
**Project:** VELTRIX AI ANALYST  
**Repository:** `Nexora-Apparel/veltrix-ai-analyst`  
**Branch:** `main`  
**Entry type:** Architecture decision and documentation milestone  
**Status:** Recorded; architecture is proposed, not implemented or certified

## Work completed

- Authored `docs/ML_MODEL_ARCHITECTURE.md`, version 1.0.
- Defined the candidate portfolio: Bayesian hierarchical team-strength model, independent Poisson baseline, Dixon–Coles, Bivariate Poisson, dynamic Elo, LightGBM, CatBoost and a conditional temporal-model research track (TCN, GRU/LSTM, transformer).
- Specified feature families for team performance, player/squad intelligence, match context, tactical metrics and timestamped market evidence.
- Defined leakage-safe ensemble options, calibration candidates, model disagreement handling and abstention.
- Established chronological walk-forward evaluation, baselines, proper scoring rules, model admission gates, model registry requirements and resource/quota controls.
- Defined the LLM research assistant as an evidence extraction and explanation component only; numerical forecasts remain with validated statistical/ML services.

## Architectural decisions

1. The system will use a hybrid statistical/ML portfolio; no single model is assumed to be best across all markets and competitions.
2. Independent Poisson and Elo are mandatory transparent baselines. More complex candidates must demonstrate incremental out-of-sample value.
3. Dixon–Coles, Bivariate Poisson, LightGBM and CatBoost are candidate models, not automatically approved production models.
4. Temporal neural models remain research-only until data volume, timestamp integrity and baseline comparisons justify them.
5. Ensemble weights and calibration are fitted without access to the final test period.
6. Each market receives separate validation and publication approval.
7. Insufficient evidence results in abstention, not generic or fabricated probabilities.
8. No legacy prediction code, weights, priors, calibration or decision rules are imported from VELTRIX FOOTBALL 2.0.
9. Training and evaluation should use pinned local/offline snapshots wherever possible to protect provider and database quotas.

## Validation and implementation status

- Documentation authored and committed to the public project repository.
- No model code was implemented in this documentation task.
- No model was trained, benchmarked, calibrated or certified.
- No provider API was called.
- No database was provisioned or queried.
- No historical dataset was downloaded or imported.
- No secrets, credentials or private provider data were added.

## Commit

`4a996a2e65f7ad2201494c642a385c442c0c3e9d` — `docs(models): define hybrid prediction architecture v1`

## Next execution items

1. Link this specification from the project progress register and README.
2. Define feature contracts, forecast cutoff semantics and immutable dataset snapshot format.
3. Build the offline chronological evaluation harness and baseline metrics before implementing advanced models.
4. Keep Stage 2 data ingestion bounded, resumable and quota-aware; do not begin bulk recollection until recovery and coverage-gap inventory is complete.

## Release caveat

This entry records an architecture specification only. It does not claim that the prediction engine or any listed model is operational.