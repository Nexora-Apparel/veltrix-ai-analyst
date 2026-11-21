# Corrected shrinkage audit — pre-registration

This document and the matching code constants are committed before results are computed. Diagnostic only; the 996 imported labels are not point-in-time certified and cannot support admission.

## Fixed configurations
- Archived fit: team ridge 0.5, competition ridge 0.5, half-life 365 days.
- Reference k values: 0.5 and 2.0.
- Reference team penalty: tau_team = k * mu.
- Reference competition penalty: tau_competition = k * 2 * mu.
- Home advantage is unpenalized in archived and both reference fits.
- Every fit sets as_of to the first test kickoff and computes recency weights against that cutoff. Training rows must have kickoff strictly before the cutoff. Unseen teams have zero team effect in all fits, as implemented by the shared model.

## Frozen chronological folds
Sort unique kickoff dates. For each fold, use the first 60%, 70%, 80%, or 90% of dates as training dates; the immediately following ceil(10% of all unique dates) are test dates. The training cutoff is the earliest test kickoff, exclusive for training. Record actual date boundaries and row counts. No test-window row enters fitting, cutoff selection, or recency weighting.

## Metrics and uncertainty
On identical test fixtures, report 1X2 log loss and multiclass Brier. For archived-minus-reference log loss, report paired date-block bootstrap 95% intervals (2,000 replicates; seed 20261121). Report home-advantage climatology on the same folds. Report test fixtures with either side below five training matches. Any failed convergence remains visible and invalidates that fit's metric comparison; it is not dropped.

## Reporting
Report convergence, iterations, gradient norm per fit/fold; centered/identified effects; dispersion of expected home goals, expected away goals and P(home) on archived 25 and training matchups; team effect ratio medians/IQRs weighted and unweighted by match count. The sum(w*lambda) diagnostic is first-order only; joint attack/defence estimation means it is not a standalone shrinkage estimate. No team display names, fixture scores or raw provider fields in JSON.

## Admission and safety
No admission conclusion. Quarantine and value-betting lock remain. No production, DB, provider, Odds API, or Android changes. Workflow is manual workflow_dispatch only with contents:read and actions:read, pinned actions, artifact ZIP and canonical hash checks before computation, and sanitized JSON-only output.
