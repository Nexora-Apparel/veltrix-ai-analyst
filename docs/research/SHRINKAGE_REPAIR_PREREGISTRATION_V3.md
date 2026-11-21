# Shrinkage repair pre-registration v3

**Status:** pre-registered; no real-data rerun has been dispatched.  
**Base audit:** run 44916186280, implementation commit `4ee0cbfdcb98149524c0a7a369fc0400126b4c6f`.  
**Config SHA-256:** `80658db5ee8a8793e9c9d747101059072dd1fb3af55b08f6f610c4e5a6346a56` (canonical JSON: UTF-8, sorted keys, compact separators, trailing newline).  
**Configuration:** `docs/research/shrinkage-selection-v3.json`.

## 1. Solver method

The repair will add an explicitly selectable damped-Newton optimizer to the existing hierarchical Poisson objective. It will use the analytic Hessian of the same recency-weighted Poisson negative log-likelihood plus the same ridge penalties, with a backtracking Armijo line search and a positive-definite damping strategy. The objective, feature parameterization, home-advantage treatment, and penalty scaling will not be changed as part of the solver repair.

The production/default caller path remains the existing default optimizer unless a separate, explicitly reviewed change is made. The prospective shadow path must not silently switch solver or hyperparameters in this repair PR.

## 2. Required solver verification before real-data use

1. Compare Newton against the existing gradient-descent fitter on a small deterministic synthetic case: fitted objective, parameter vector/predicted rates, and convergence status must agree within predeclared numerical tolerances.
2. Compare Newton against L-BFGS on a small deterministic case where L-BFGS converges. Compare objective, parameter vector/predicted rates, and gradient norm.
3. Exercise singular/ill-conditioned Hessian handling, damping escalation, rejected line-search steps, and explicit non-convergence.
4. Only after these checks pass may synthetic scale tests be run. No 996-row corpus or other real-data regularization/recovery run is permitted until a separately authorized dispatch.

## 3. Hyperparameter selection — frozen grid

Evaluate exactly the Cartesian grid:

- (k \in \{0.25, 0.5, 1, 2, 4, 8\})
- half-life (\in \{180, 365, 730\}) days

The 18 candidates are selected using chronological development folds 1–3 only. No fold 4 result, prospective result, or later settled outcome may influence selection. Use identical fold partitions and the same objective/penalty conversion across candidates. The selection metric and tie-break rule must be implemented and tested before any real-data run; report fold-wise log loss and multiclass Brier against both training-only climatology and plain scaled Poisson. Freeze the selected pair in a versioned immutable config and record its SHA-256 before prospective scoring.

## 4. Previously examined diagnostic window / contamination disclosure

Fold 4, **2026-10-28 through 2026-11-19**, has already been evaluated for the archived model and reference configurations (k=0.5) and (k=2) in audit run 44916186280. It is therefore **not an untouched holdout**. It must be labelled **PREVIOUSLY_EXAMINED_DIAGNOSTIC_WINDOW** in every report and preregistration. It may be used only as a sanity check for SHADOW-tier admission; it cannot be presented as clean validation or used to tune the grid.

The fold 1–3 development-only selection is also constrained by the earlier diagnostic run: this v3 selection is a preregistered repair exercise, not a claim that any historical fold remains pristine.

## 5. Research-only admission gate

Research-only display is eligible only if the frozen candidate:
- beats BOTH the training-only climatology baseline and the plain scaled Poisson baseline on the preregistered chronological development folds 1–3; and
- does not fail the previously examined fold-4 diagnostic sanity check.

A pass supports research-only display consideration only, not production promotion. Anything beyond research-only requires prospective fixtures settled after 2026-11-21, scored automatically against the frozen configuration, plus explicit owner sign-off.

## 6. Prospective settlement scoring

The repair will add a read-only evaluation path that consumes the existing published/shadow forecast ledger and settled fixture outcomes. It must:
- select only forecasts generated with the frozen config hash;
- join settlements by canonical fixture identity and preserve prediction cutoff / settlement timestamps;
- score each eligible settled fixture once, idempotently;
- calculate 1X2 log loss and multiclass Brier against the frozen model, climatology, and plain scaled Poisson;
- retain unscored, void, duplicate, late-label, and lineage-invalid records with explicit exclusion reasons;
- never write predictions, publish forecasts, change quarantine, unlock value betting, call odds providers, or send Telegram notifications.

No real-data execution, feed enablement, database write, provider call, or lock change is authorized by this pre-registration.

## 7. Stop conditions

A non-converged fit is invalid and excluded from model comparison. Any change to the objective, feature parameterization, training cutoff, grid, fold boundaries, selection metric, or tie-break rule requires a new versioned pre-registration before inspecting results. The diagnostic fold-4 window must never be described as untouched.
