# Shrinkage repair pre-registration v3.1

**Status:** pre-registered; no candidate grid has been evaluated under v3.1.  
**Base diagnostic:** run 44916186280, implementation commit `4ee0cbfdcb98149524c0a7a369fc0400126b4c6f`.  
**Config:** `docs/research/shrinkage-selection-v3.json`.  
**Canonical config SHA-256:** `14333ab670983a692605e91705bc001707bc3c2319c1e94f116ddc15adcb44dd` (canonical JSON UTF-8, sorted keys, compact separators, no NaN, trailing newline).

## 1. Solver and fixed convergence rule

Use damped Newton on the unchanged recency-weighted Poisson negative log-likelihood plus unchanged ridge penalties. Construct the analytic Hessian from each weighted Poisson observation's feature-vector outer products and add the exact ridge diagonal. Solve the damped linear system; escalate damping when the system is not positive definite or the candidate direction is not a descent direction. Use backtracking Armijo line search.

A fit is converged only when **both** conditions hold for **two consecutive accepted steps**:
- Euclidean gradient norm `||g||₂ <= 1e-7`.
- Relative objective change `abs(f_new - f_old) / max(1, abs(f_old)) <= 1e-10`.

Maximum 200 Newton iterations. No tolerance relaxation after observing results. Any fit failing either condition, line search, or finite-value checks is invalid, excluded from model comparison, and reported with its terminal diagnostics. This stopping rule applies uniformly to every candidate and fold.

## 2. Solver verification

Before any real-data evaluation:
1. Compare Newton with the existing gradient-descent fitter on a deterministic small synthetic case: objective, fitted rates, parameter values, and convergence.
2. Compare Newton with L-BFGS on a deterministic small case where L-BFGS converges.
3. Test singular/ill-conditioned Hessians, damping escalation, rejected Armijo steps, non-finite guards, and explicit non-convergence.
4. Run synthetic scaling tests only after the equivalence and edge-case tests pass.

Do not change the existing optimizer default or the prospective shadow caller's selected path.

## 3. Frozen candidate search

Evaluate exactly:
- Team shrinkage `k ∈ {0.5, 1, 2, 4, 8, 16, 32, 64, 128}`.
- Half-life `{180, 365, 730}` days.
- Probability blend `p = w*p_model + (1-w)*p_climatology`, with `w ∈ {0.25, 0.5, 0.75, 1.0}`.

Select only on chronological development folds 1–3. The Cartesian hyperparameter grid is 27 model configurations; evaluate the four blend weights as a preregistered downstream probability layer on the same development folds. No fold-4 result or prospective settlement may influence selection. Selection metric, aggregation, and tie-break rules must be coded and tested before any real-data run.

Archived-equivalent team-prior reference points, computed as `k_equiv = 0.5 * W / mu` using each fold's recency weight sum W and weighted mean goals per team-match mu:
- Fold 1: **128.3802704829587**
- Fold 2: **173.29424410186596**
- Fold 3: **206.5352382546307**
- Fold 4: **269.2584048267363** (diagnostic reference only)

These values are not grid candidates and do not authorize fitting. The fold-4 value is not used for selection.

## 4. Previously examined diagnostic window and leakage disclosure

Fold 4, **2026-10-28 through 2026-11-19**, has already been evaluated in audit run 44916186280. It is **PREVIOUSLY_EXAMINED_DIAGNOSTIC_WINDOW**, not an untouched holdout. It may be used only as a SHADOW-tier sanity check, never for tuning or as clean validation.

The source dataset's historical labels were imported retrospectively. The fold-4 leakage review found:
- 835/835 training rows have label-observation timestamps at or after the fold-4 test cutoff (2026-10-28 17:30 UTC).
- The training rows have no per-row prediction-cutoff timestamp in the artifact, so whether each label was known at its own historical prediction time cannot be established.
- No exact cross-fold duplicate was found among available canonical fixture IDs, provider fixture IDs, or same-direction teams/date keys in the supplied 996-row training table.
- The artifact contains only the aggregate `fixture_identity_rows=1053` count, not the identity-case records; the 28 unresolved cases cannot be independently enumerated or cleared from this artifact.

Therefore fold 4's apparent performance is **not trustworthy as point-in-time evidence**. The existing audit's fold-4 metrics are disclosed but are not admission evidence until identity and timestamp lineage are resolved. The previously examined status remains even after leakage checks.

## 5. Required evaluation and admission report

For each candidate, development fold, and diagnostic window, report:
- 1X2 log loss and multiclass Brier.
- Paired differences against training-only climatology and plain scaled Poisson, with 2,000-replicate paired kickoff-date block bootstrap 95% intervals.
- Reliability tables for HOME, DRAW, AWAY: ten fixed probability bins, count, mean predicted probability, and observed frequency.
- Calibration slope and intercept per outcome, with fit method and sample count.
- Count of forecasts with any outcome probability above 0.80, number of hits, and hit rate.
- Per-competition breakdown of log loss, Brier, high-probability counts, and high-probability hit rate.
- Explicit invalid-fit counts and terminal convergence diagnostics.

Do not cap or clip high probabilities by hand. Probability outputs must remain those of the model or preregistered convex blend.

Research-only display eligibility requires the frozen candidate to beat both climatology and plain scaled Poisson on development folds 1–3, satisfy the calibration/extreme-probability reporting gate, and not fail the examined diagnostic-window sanity check. The examined window cannot establish clean validation.

## 6. Prospective settlement scoring

Score only fixtures settled after 2026-11-21 and forecast under the exact frozen config hash. Join by canonical fixture identity; preserve prediction cutoff, kickoff, settlement, label-observation timestamps, and source lineage. Score each eligible settled fixture once, idempotently. Report model, climatology, and plain scaled Poisson log loss/Brier, calibration, reliability, extreme-probability hit rate, and competition breakdown. Retain exclusions with explicit reasons. The scorer is read-only: no prediction writes, publication, database writes, provider calls, odds calls, Telegram notifications, lock changes, or feed changes.

## 7. Stop conditions

No real-data evaluation or workflow dispatch is included in this preregistration. A real-data run requires owner-dispatched workflow execution with exact immutable input IDs and commit/config hashes. Any change to objective, parameterization, cutoff, folds, grid, blend set, convergence thresholds, selection metric, or tie-break rule requires a new versioned preregistration before results are inspected. Anything beyond research-only requires prospective settled evidence and owner sign-off.
