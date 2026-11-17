# ADR-001 — Prediction engine boundaries and execution architecture

**Status:** Proposed for Stage 3 implementation  
**Date:** 2026-11-17  
**Scope:** VELTRIX AI ANALYST only

## Context

Stage 2 completed historical ingestion, provenance capture, canonical coverage and structural reconciliation. The current 384-fixture Brazil Serie B dataset is not point-in-time (PIT) feature eligible: source publication/availability evidence is absent, and canonical fixture identities remain review-required or conflicted. The repository has a FastAPI health endpoint, provider/ingestion foundations and a native Android shell, but no active prediction service.

The prediction engine must therefore be independently implementable and mathematically testable without training on the current ineligible data.

## Decisions

### 1. Strict module boundaries

The backend is divided into the following logical packages:

- `app.contracts`: immutable domain contracts for evidence, eligible observations, fixtures, predictions, model metadata and validation folds.
- `app.features`: feature registry, PIT eligibility and reproducible point-in-time feature snapshots.
- `app.models.elo`: deterministic chronological team-rating engine.
- `app.models.poisson`: independent home/away Poisson goal distributions and scoreline matrix.
- `app.models.dixon_coles`: low-score dependence correction over the Poisson matrix.
- `app.validation`: chronological walk-forward split construction, leakage checks and proper scoring metrics.
- `app.predictions`: orchestration, market derivation, model disagreement, abstention and publication policy.
- `app.registry`: immutable model/config/data-snapshot lineage.

Provider adapters may supply source observations, but model code must not call providers or read provider-specific payloads directly. Android remains a presentation client; it does not calculate probabilities or hold provider credentials.

### 2. Evidence before features

Every feature value must resolve to an exact immutable source observation and exact retrieval sighting/response. Its evidence must include:

- source/provider and provider-local record identity;
- source observation, sighting and captured provider response identifiers;
- payload SHA-256;
- event time, source publication time, availability time and retrieval time;
- availability basis and PIT-certification state;
- effective rights approval permitting both FEATURE_ENGINEERING and MODEL_TRAINING at the prediction cutoff;
- canonical fixture/team identity verification state;
- transformation and feature-schema versions.

All timestamps are timezone-aware. Publication and availability must be no later than the forecast cutoff. Retrieval time is audit evidence, never a substitute for publication/availability. Kickoff time is event time, never publication time. Missing or ambiguous evidence fails closed.

### 3. Identity and label boundary

Only fixtures with verified canonical competition, home-team, away-team and fixture-source mappings can enter certified training/evaluation. `SOURCE_ROW_ONLY`, `IDENTITY_REVIEW_REQUIRED`, `CONFLICT`, quarantined and duplicate-candidate rows are excluded from certified samples.

A settled score may be a target label when settlement and rights are independently valid. It does not become a pre-match feature. The current four UNKNOWN rows and two America MG conflict rows remain excluded pending evidence-backed review.

### 4. Model progression

Implementation order:

1. Formal contracts and PIT validator.
2. Elo rating baseline with explicit update semantics and uncertainty diagnostics.
3. Independent Poisson goal distribution.
4. Dixon–Coles low-score correction with fitted parameter constraints.
5. Chronological walk-forward framework and proper scoring metrics.
6. Later: hierarchical strength, bivariate Poisson, boosted trees, calibration and ensemble only after data admission and sample sufficiency.

No model is admitted because it is more complex. Each candidate must beat its appropriate baseline on sealed chronological test periods.

### 5. Mathematical conventions

- Elo ratings are updated strictly in event-time order using only previously settled eligible results. Same-timestamp fixtures are processed as a batch so one result cannot influence another simultaneous kickoff.
- Elo's result expectation and draw treatment are explicit configuration, versioned, and fitted only on training/validation windows.
- Independent Poisson uses `P(G=k | lambda)=exp(-lambda) lambda^k/k!` for each side. The joint scoreline matrix is the outer product of home and away distributions.
- Dixon–Coles applies the standard low-score `tau(x,y)` correction to 0–0, 0–1, 1–0 and 1–1 cells. The fitted rho must keep every adjusted cell non-negative and the matrix is normalized only for numerical drift; invalid parameter sets are rejected.
- Market probabilities are derived from the same joint scoreline matrix, preserving coherence across 1X2, BTTS and totals.

### 6. Chronological evaluation

- Split by kickoff timestamp, never random rows.
- Keep all rows derived from one fixture in the same fold.
- Build each feature snapshot at its own forecast cutoff.
- Fit feature transforms, model parameters, calibration and ensemble weights only on earlier training/validation periods.
- Apply a configurable temporal embargo where rolling windows or delayed source publication could cross fold boundaries.
- Preserve exact fixture IDs, cutoffs, source evidence IDs, data snapshot hash, code commit, model/config versions and metrics for every fold.
- Report Brier score, log loss, goal-distribution log likelihood, calibration/reliability diagnostics, coverage and abstention. ROI is not a substitute for proper scoring rules.

Synthetic tests validate implementation only. Synthetic rows must be tagged and excluded from all real-world performance reports.

### 7. Release and abstention

No numerical forecast is published if fixture identity, cutoff, source eligibility, feature coverage, model admission, calibration, probability validity or uncertainty checks fail. No generic priors or fallback probabilities are substituted. A rejection record with reason codes is retained.

Value betting remains locked until its separate certification requirements are satisfied. Android prediction API integration remains deferred until a real, gated prediction endpoint exists.

## Consequences

This architecture allows deterministic mathematical components and contract tests to be built now, while preventing the Stage 2 historical dataset from being misrepresented as a valid pre-match training set. It adds explicit lineage and abstention requirements to every future prediction.

## Non-goals

- No training on current PIT-ineligible fixture observations.
- No automatic canonical identity decisions.
- No provider calls as part of model inference.
- No legacy VELTRIX FOOTBALL 2.0 prediction code, priors, weights, calibration or decision rules.
- No production prediction endpoint or Android prediction integration in this ADR.
