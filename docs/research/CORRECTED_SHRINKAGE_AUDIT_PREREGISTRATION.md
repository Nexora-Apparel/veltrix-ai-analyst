# Corrected shrinkage audit — pre-registration

This document and the matching code constants are committed before results are computed. Diagnostic only; the 996 imported labels are not point-in-time certified and cannot support admission.

## Version history and optimizer pre-registration
- Version 1.0 fixed the fold-specific prior scaling and synthetic stationarity negative control. No computation on the 996-row corpus has been performed.
- Version 2.0 (2026-11-21, before any real-corpus audit): replace the shared fitter's slow plain gradient descent with a pure-Python limited-memory BFGS solver for this audit and the subsequent repair. The objective, parameterization, recency weights, priors and penalty units are unchanged. The solver uses the same analytic gradient, L-BFGS history size 10, Armijo sufficient-decrease coefficient 1e-4, initial step 1.0, up to 50 backtracking reductions, max_iterations 4,000 and Euclidean gradient tolerance 1e-7. The existing gradient-descent solver remains available as the default for unrelated callers. Audit fits explicitly select L-BFGS.
- Version 2.0 is a documented pre-result method change prompted by supervisor review of a 4,000-iteration synthetic convergence failure. The 996-row data have not been loaded or fitted. A 1,000-fixture/130-team synthetic test is required for both k=0.5 and k=2.0, plus a small-case comparison against the existing gradient-descent fitter. A fit that does not converge remains invalid and is not used for comparative metrics.

## Fixed configurations
- Archived fit: team ridge 0.5, competition ridge 0.5, half-life 365 days.
- Reference k values: 0.5 and 2.0.
- Optimizer settings for every audit fit: solver = L-BFGS with Armijo backtracking; history size = 10; sufficient-decrease coefficient = 1e-4; initial step = 1.0; max_iterations = 4,000; Euclidean gradient tolerance = 1e-7. The audit explicitly selects L-BFGS; the existing gradient-descent solver remains the default for unrelated callers.
- Reference team penalty: tau_team = k * mu.
- Reference competition penalty: tau_competition = k * 2 * mu.
- Home advantage is unpenalized in archived and both reference fits.
- Every fit sets as_of to the first test kickoff and computes recency weights against that cutoff. Training rows must have kickoff strictly before the cutoff. Unseen teams have zero team effect in all fits, as implemented by the shared model.

## Frozen chronological folds
Sort unique kickoff dates. For each fold, use the first 60%, 70%, 80%, or 90% of dates as training dates; the immediately following ceil(10% of all unique dates) are test dates. The training cutoff is the earliest test kickoff, exclusive for training. Record actual date boundaries and row counts. No test-window row enters fitting, cutoff selection, or recency weighting.

## Metrics and uncertainty
On identical test fixtures, report 1X2 log loss and multiclass Brier. For archived-minus-reference log loss, report paired date-block bootstrap 95% intervals (2,000 replicates; seed 20261121). Report home-advantage climatology on the same folds. Report test fixtures with either side below five training matches. Any failed convergence remains visible and invalidates that fit's metric comparison; it is not dropped.

## Slimmed report outputs (Commit B)
- On each identical chronological fold, report a training-only, recency-weighted HOME/DRAW/AWAY climatology and its 1X2 log-loss and multiclass Brier on that fold's test fixtures. This is the home-advantage-aware categorical baseline; no test outcomes enter its probabilities.
- For archived-versus-reference team effects, centre attack and defence effects by each team's training-match-count-weighted mean before forming ratios. Summarize absolute centred archived/reference ratios with ordinary and match-count-weighted median, Q1 and Q3 (IQR), and disclose omitted near-zero reference effects and sign reversals. These are descriptive ratios, not identified raw-effect comparisons.
- Report expected home goals, expected away goals and P(home) dispersion (mean, SD, minimum, maximum) on the fixed archived forecast fixtures, plus the already specified test-fold and training-matchup dispersion. Explicitly report expected, matched and missing archived-fixture counts.
- Preserve paired archived-minus-reference log-loss differences with the pre-registered date-block bootstrap and per-fit convergence/iteration/gradient diagnostics. A failed or non-converged fit remains visible and is excluded from comparative metrics, never silently dropped.
- Commit B adds report calculations and synthetic unit tests only. It does not load, fit, or evaluate the 996-row artifact.
- Version 2.0 adds synthetic convergence tests on approximately 1,000 fixtures and 130 teams for both reference k values, plus a small-case numerical comparison against the original gradient-descent solver. These tests are synthetic only.

## Reporting
Report convergence, iterations, gradient norm per fit/fold; centered/identified effects; dispersion of expected home goals, expected away goals and P(home) on archived 25 and training matchups; team effect ratio medians/IQRs weighted and unweighted by match count. The sum(w*lambda) diagnostic is first-order only; joint attack/defence estimation means it is not a standalone shrinkage estimate. No team display names, fixture scores or raw provider fields in JSON.

## Admission and safety
No admission conclusion. Quarantine and value-betting lock remain. No production, DB, provider, Odds API, or Android changes. Workflow is manual workflow_dispatch only with contents:read and actions:read, pinned actions, artifact ZIP and canonical hash checks before computation, and sanitized JSON-only output.
