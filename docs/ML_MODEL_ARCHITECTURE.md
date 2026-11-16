# VELTRIX AI ANALYST — Model Architecture & Intelligence Specification

**Document ID:** VAA-ML-001  
**Version:** 1.0  
**Date:** 2026-11-16  
**Status:** Proposed architecture; no predictive model is yet implemented or certified  
**Owner repository:** `Nexora-Apparel/veltrix-ai-analyst`

## 1. Purpose and design principles

This document defines the candidate modelling architecture for VELTRIX AI ANALYST. The system is intended to produce calibrated, evidence-grounded football forecasts across supported competitions and markets.

The architecture is deliberately hybrid: interpretable statistical goal models, dynamic team-strength models, gradient-boosted machine learning, and (only where justified by data volume) temporal neural models. A model's sophistication is not evidence of predictive value. Every candidate must earn admission through chronological out-of-sample evaluation.

Core principles:

- No LLM-only numerical prediction.
- No fabricated features, fallback probabilities, or invented source timestamps.
- No reuse of legacy VELTRIX prediction code, weights, priors, calibration or decision rules.
- Historical raw data may be reused only after source-rights, provenance, quality and point-in-time checks.
- Model outputs remain versioned, reproducible and auditable.
- Abstention is a valid result when evidence is insufficient.
- Model and market certification are separate decisions.

## 2. Candidate model portfolio

### M01 — Bayesian hierarchical team-strength model

**Purpose:** Estimate latent attacking and defensive strengths while sharing statistical information appropriately across teams and competitions.

**Candidate formulation:** Hierarchical Poisson or negative-binomial goal model with partial pooling. Team attack, team defence, home advantage and competition scoring environment are estimated with uncertainty.

**Feature/evidence inputs:** Timestamp-valid historical goals, home/away status, competition identity, opponent identity and recency weights. Additional features are admitted only after point-in-time validation.

**Outputs:** Posterior team attack/defence strengths, expected scoring rates, uncertainty intervals and diagnostics.

**Risks and controls:** Sparse teams must retain wider posterior uncertainty. Hierarchical borrowing must be measured and must not silently turn an unsupported team into a high-confidence forecast.

### M02 — Independent Poisson baseline

**Purpose:** Establish a transparent and reproducible goal-distribution baseline.

**Candidate formulation:** Separate home and away Poisson scoring distributions driven by estimated scoring intensities.

**Outputs:** Scoreline matrix and derived 1X2, BTTS, totals, team-goal and correct-score probabilities.

**Role:** Mandatory benchmark for more complex goal models. It is not automatically a production winner.

### M03 — Dixon–Coles model

**Purpose:** Improve low-scoreline modelling by adjusting dependence in low-scoring outcomes.

**Candidate formulation:** Time-decayed attack/defence Poisson model with a fitted low-score dependence correction.

**Outputs:** Joint scoreline distribution and derived market probabilities.

**Admission test:** Must outperform the independent Poisson baseline on appropriate chronological test windows, especially goal-distribution likelihood and market-specific scoring rules, without destabilising calibration.

### M04 — Bivariate Poisson model

**Purpose:** Test whether shared match-level scoring variation improves the joint goal distribution.

**Candidate formulation:** Bivariate Poisson or a justified alternative joint count distribution.

**Outputs:** Joint home/away goal probabilities and derived markets.

**Admission test:** Retain only if it adds robust out-of-sample value beyond M02/M03. Compare parameter stability, calibration and computational cost.

### M05 — Dynamic Elo strength model

**Purpose:** Track relative team strength over time as an independent signal.

**Inputs:** Chronological results, opponent rating, home advantage, competition context and rating-update parameters.

**Candidate extensions:** Goal-difference adjustments, rating uncertainty, competition-aware scaling and time decay.

**Outputs:** Relative strength, expected result probabilities and rating trajectory.

**Controls:** Ratings at kickoff may use only results known before kickoff. Promotion, relegation and cross-competition rating transfers require explicit treatment.

### M06 — LightGBM outcome/market models

**Purpose:** Learn nonlinear relationships across verified structured features.

**Candidate targets:** 1X2, BTTS, goal totals and team goals. Train distinct market-specific estimators where target definitions and evidence permit.

**Candidate features:** Opponent-adjusted form, xG/xGA, shot quality, shots, defensive indicators, rest, home/away splits, competition context and verified availability/lineup features.

**Controls:** Chronological folds, leakage-safe feature generation, missingness indicators where justified, probability calibration, feature-importance stability and drift monitoring.

### M07 — CatBoost outcome/market models

**Purpose:** Complement gradient boosting where categorical variables and heterogeneous competition metadata are useful.

**Candidate categorical inputs:** Competition, team identifiers, venue status and verified categorical match context.

**Admission test:** Compare against LightGBM and simpler baselines using identical chronological folds and feature cutoffs. Do not include both merely to increase model count.

### M08 — Temporal sequence models (research track)

**Candidates:** Temporal Convolutional Networks, GRU/LSTM and transformer-based sequence models.

**Purpose:** Learn evolving team performance and temporal patterns from sufficiently large, timestamp-correct sequences.

**Preconditions:** Adequate data volume, consistent feature definitions, reliable point-in-time timestamps, leakage-safe sequence construction and meaningful baseline comparisons.

**Status:** Research-only until these preconditions and out-of-sample improvement are demonstrated. Neural complexity is not a release requirement.

## 3. Feature and intelligence layers

Feature families are admitted only when source rights, semantics, timestamp and quality are documented.

1. **Team performance:** goals, xG, xGA, shots, shots on target, chance creation, defensive actions, home/away splits and opponent-adjusted form.
2. **Player and squad:** confirmed lineups, injuries, suspensions, player minutes, player contribution and goalkeeper performance. Confirmed and projected information must be separately labelled.
3. **Match context:** rest days, fixture congestion, travel where verifiable, neutral venue and competition context.
4. **Tactical indicators:** pressing/PPDA, possession and style indicators only where definitions and provider coverage are consistent.
5. **Market evidence:** bookmaker-specific odds with market, region, bookmaker, observation timestamp and source provenance. Opening/current/closing labels require actual evidence; no average price is assumed to be a closing price.

Post-match statistics, final lineups not known at forecast time, final scores and retrospectively updated tables must never enter a pre-match feature vector.

## 4. Ensemble architecture

The ensemble consumes only out-of-fold or otherwise leakage-safe model predictions.

Candidate strategies, in increasing complexity:

- Equal-weight probability averaging as a baseline.
- Validation-derived weighted averaging.
- Stacked generalisation trained on out-of-fold predictions.
- Competition- or market-specific weighting only where sample size and stability justify it.

Weights are fitted using training/validation periods only. The final test period is sealed from model selection and ensemble tuning.

Each constituent prediction must carry model ID/version, dataset snapshot, feature schema version, forecast cutoff, market, probability output and uncertainty/diagnostics.

The ensemble must calculate and retain constituent disagreement. Material disagreement triggers review, uncertainty escalation or abstention; it must not be hidden by averaging.

## 5. Probability calibration

Candidate calibrators:

- Isotonic regression.
- Platt/logistic scaling.
- Temperature scaling for suitable multiclass models.
- Other justified calibration methods evaluated on leakage-safe validation predictions.

Calibration is assessed independently by market and, where evidence supports it, by competition or data-quality tier.

Required diagnostics:

- Brier score.
- Log loss.
- Reliability diagrams.
- Expected calibration error, with binning methodology recorded.
- Calibration stability across time windows and probability ranges.

Calibration is not fitted on the final test set. A well-ranked model with unreliable probabilities is not eligible for probability-based value decisions.

## 6. Market derivation and independence

Initial target markets:

- 1X2.
- BTTS.
- Over/Under goal lines.
- Team goals.
- Correct score.
- Double chance, derived consistently from the calibrated 1X2 distribution.

Goal-model-derived markets must be internally coherent with the underlying scoreline distribution. Direct ML market models are separately evaluated and must not be blended blindly with derived probabilities.

Every market receives its own validation record and publication gate. Success in 1X2 does not certify BTTS, totals or correct score.

## 7. Training and evaluation protocol

### 7.1 Point-in-time feature contract

For every fixture, define a forecast cutoff timestamp. A feature is eligible only if it was genuinely available by that cutoff. Store source publication/effective time when provided and ingestion/observation time separately. If availability cannot be established, the feature is excluded from PIT-certified evaluation or clearly classified as non-PIT research data.

### 7.2 Chronological walk-forward

- Train on earlier periods.
- Tune using a subsequent validation period.
- Evaluate on later, untouched periods.
- Advance the cutoff and repeat.
- Preserve fold definitions, fixture IDs, feature snapshots, model versions and outputs.

Random splitting is not an acceptable primary certification protocol.

### 7.3 Baselines

At minimum compare against:
- Competition/base-rate benchmark.
- Independent Poisson.
- Dixon–Coles.
- Elo-derived baseline.
- Timestamp-valid bookmaker-implied benchmark where available.

### 7.4 Metrics

**Probabilistic:** Brier score, log loss, calibration error and reliability curves.

**Goal distribution:** joint scoreline log likelihood and count-distribution diagnostics.

**Market:** market-specific proper scoring rules, coverage, abstention/selective-risk curves and stability.

**Operational:** feature coverage, missingness, inference latency, failure rate and reproducibility.

ROI is secondary and may only be reported when odds are bookmaker-specific, market-specific, timestamp-valid, settlement rules are explicit and the sample is sufficiently large. Report uncertainty intervals; do not infer profitability from a small sample.

## 8. Model admission and release gates

A candidate is not production-ready until it passes:

1. Data provenance and rights review.
2. Point-in-time and leakage audit.
3. Chronological out-of-sample evaluation.
4. Baseline comparison.
5. Market-specific calibration.
6. Stability across time and competition tiers.
7. Reproducibility from pinned data/code/config versions.
8. Runtime and failure-mode tests.
9. Documented model card and approval record.

Models may be approved for selected markets/tiers and restricted elsewhere. A failed or inconclusive candidate remains research-only.

## 9. Prediction publication and abstention

Before publishing a fixture-market forecast, verify:

- Canonical fixture and team identity.
- Kickoff time and forecast cutoff.
- Fixture has not started.
- Required feature coverage and source provenance.
- Model and calibration versions are approved for that market/tier.
- Probabilities are finite, valid and internally consistent.
- Uncertainty and constituent disagreement are within policy.
- No prohibited post-cutoff information is present.

If a check fails, publish no numerical forecast for that market. Retain the rejection reason for audit. Do not substitute generic probabilities.

## 10. LLM research assistant boundary

An LLM may support research and explanation by:
- Summarising verified team news.
- Extracting facts from authorised sources with citations/provenance.
- Identifying conflicting reports and missing inputs.
- Explaining numerical model outputs in plain language.

An LLM must not invent statistics, assign unsupported numerical probabilities, modify model outputs, or bypass publication gates. Structured numerical predictions remain the responsibility of tested statistical/ML services.

## 11. Model registry and reproducibility

Every trained or approved model must record:

- Unique model ID and semantic version.
- Algorithm and hyperparameters.
- Training data snapshot/checksum.
- Feature schema and point-in-time cutoff policy.
- Code commit and dependency lock.
- Training/validation/test windows.
- Metrics by market and competition tier.
- Calibration method/version.
- Approval state, limitations and rollback target.

Prediction records must link to the exact model, calibration, feature snapshot and forecast timestamp that generated them.

## 12. Compute and quota discipline

- Prefer local/offline training and evaluation on immutable snapshots.
- Never repeatedly download complete historical datasets when incremental sync is possible.
- Use bounded provider request budgets, pagination, caching, checksums and resumable checkpoints.
- Keep raw restricted provider files outside the public repository.
- Avoid unnecessary database readbacks and unbounded full-table queries.
- Benchmark CPU-first methods before introducing GPU infrastructure.
- Introduce distributed training or additional infrastructure only when measured workload requires it.

## 13. Implementation sequence

1. Define feature contracts, timestamp semantics and dataset snapshot format.
2. Build reproducible offline evaluation harness and baseline metrics.
3. Implement independent Poisson and Elo baselines.
4. Implement Bayesian hierarchical and Dixon–Coles candidates.
5. Add Bivariate Poisson comparison.
6. Build leakage-safe LightGBM and CatBoost pipelines.
7. Add calibration, ensemble and disagreement/abstention logic.
8. Research temporal neural candidates only after data sufficiency review.
9. Build model registry, model cards and market-specific publication gates.
10. Run prospective shadow forecasts and independent certification before production.

## 14. Current status and explicit non-claims

As of 2026-11-16, this document is an architecture specification only.

The repository's Stage 2 data foundation is in progress. No predictive model described here is claimed to be implemented, trained, evaluated, calibrated, certified or operational. No accuracy or profitability claim is made.

**Approval principle:** Architecture candidates become production models only after evidence-based admission.