# VELTRIX independent chronological evaluator contract

**Status:** evaluation protocol draft; numeric thresholds require explicit user approval and are not frozen.  
**Primary admission metric:** 1X2 log loss.  
**Release state:** all models remain quarantined.

## 1. Separation of responsibilities

The evaluator is a separate package/module from the model builder and inference code.

- Model builder receives only training-fold data and produces immutable candidate artifacts.
- Evaluator receives immutable prediction rows, labels with point-in-time observation metadata, model/version hashes, and baseline predictions.
- Evaluator must not import model-fitting code or call the model builder. It computes metrics independently from stored probability vectors.
- Evaluator has its own unit, property, leakage, chronology, and fixture-join tests.
- Evaluation outputs are immutable and stored in an append-only `evaluation_runs` ledger with a content hash.
- Candidate code cannot modify evaluator thresholds, baseline predictions, holdout membership, or previously recorded evaluation runs.

## 2. Primary metric: 1X2 log loss

For each eligible fixture (i), the evaluator receives a normalized probability vector (p_i=(p_{H,i},p_{D,i},p_{A,i})) and the settled outcome (y_i\in\{H,D,A\}).

[
L_i=-\log(p_{y_i,i})
]

Primary comparison is the paired per-fixture loss difference:

[
d_i=L_{candidate,i}-L_{baseline,i}
]

Negative values favour the candidate. Report mean paired difference, median, distribution, and a paired date-block-bootstrap confidence interval. The candidate must beat **both** pre-registered baselines:

1. **League climatology with home advantage:** competition-specific historical 1X2 frequencies estimated strictly from the training portion of each chronological fold, with smoothing fixed before evaluation.
2. **Tuned team-aware baseline:** either a properly scaled simple Poisson attack/defence model or Elo. Its tuning is nested within chronological development data and is frozen before outer evaluation.

A candidate that beats only one baseline fails primary admission. The evaluator must not select the weaker baseline after observing the candidate result.

Brier score, calibration, favourite/underdog splits, and market-level breakdowns may be reported as diagnostics, but they are not additional primary metrics unless explicitly approved in the threshold contract.

## 3. Nested chronology and leakage controls

- Use nested chronological validation or a final untouched holdout.
- Every fold stores train start/end, validation start/end, prediction cutoff, label-observed cutoff, data rights, dataset hash and feature snapshot hashes.
- A training label is eligible only if its system-observed timestamp and rights are valid at the fold's prediction cutoff and its kickoff precedes the validation period.
- Validation labels must be observed after the relevant prediction cutoff; historical imported labels without point-in-time availability remain training-only.
- No random train/test split. No kickoff-only retrospective proxy may be called prospective.
- All baseline predictions are generated without access to validation labels.
- Duplicate canonical fixtures, ambiguous team identity, missing labels, invalid probability sums, stale odds timestamps or unlicensed sources fail closed.

## 4. Minimum detectable effect and power — before evaluation

Power must be calculated before the final evaluation or holdout is opened.

Let (d_i) be paired candidate-minus-baseline log-loss differences. Use chronological development folds only to estimate the variability of paired date-block outcomes. Because fixtures on the same date may be dependent, the effective sample size is based on date blocks, not raw match count.

Initial analytic approximation for planning:

[
MDE\approx (z_{1-\alpha}+z_{1-\beta})\frac{\sigma_d}{\sqrt{n_{eff}}}
]

The production protocol should use a simulation-based power check over the same paired date-block bootstrap used for inference:

1. Estimate the distribution of date-block loss differences from development folds.
2. Pre-register the minimum practically meaningful 1X2 log-loss improvement (delta_{min}).
3. Simulate candidate improvements at (delta_{min}) while preserving date-block dependence.
4. Estimate power of the one-sided paired block-bootstrap test.
5. Calculate and record MDE, power, required date blocks, and required match count before final evaluation.
6. If the available dataset cannot reach the pre-registered power/MDE target, admission fails as `INSUFFICIENT_STATISTICAL_POWER`. Do not lower the effect threshold, change confidence level, or switch baselines after seeing results.

Draft threshold values such as (alpha=0.05) and power (=0.80) are proposals only. The user must approve the numeric threshold contract once; then the complete threshold JSON is SHA-256 hashed and frozen.

## 5. Paired date-block bootstrap

- Resample complete kickoff-date blocks, preserving all fixtures from a sampled date together.
- Use identical sampled blocks for candidate and both baselines.
- Report the mean paired log-loss improvement and its confidence interval against each baseline.
- No fixture-level independent bootstrap.
- Record bootstrap seed, replicate count, date-block definition, interval method, and evaluator version in the immutable report.
- A candidate must beat both baselines under the pre-registered confidence rule. No post-hoc baseline substitution or metric switching.

## 6. Single-use final holdout and run ledger

The final holdout is opened once per frozen evaluation protocol.

- Assign an immutable `holdout_period_id` and dataset hash before predictions are evaluated.
- The evaluator ledger enforces one final-holdout attempt per period/protocol. A failed candidate burns that holdout period.
- Every run, including failed, underpowered, interrupted, or rejected runs, receives a unique `evaluation_run_id` and immutable record.
- Log candidate model version, config/data/code hashes, baseline versions, fold boundaries, label-rights coverage, MDE, power, metrics, bootstrap intervals, run status, timestamp and report SHA-256.
- Repeated attempts cannot overwrite, delete or conceal prior runs.
- A new candidate after a failed final holdout requires new unseen data and a new holdout-period identifier.

## 7. Market sequencing

1. Run primary 1X2 log-loss admission against both baselines.
2. If and only if primary 1X2 passes, run non-regression checks for BTTS and O/U 1.5, 2.5 and 3.5.
3. If primary fails or is underpowered, do not re-test or tune the secondary markets on that holdout.
4. Secondary-market non-regression at this stage does not waive the existing market certification requirements. Full release certification remains locked until the existing per-market walk-forward, prospective settled-selection, distinct-date, timestamped-odds coverage and ROI requirements are independently met.

## 8. Odds and market benchmark

- Odds are not model inputs.
- When licensed, compare candidate 1X2 probabilities with margin-removed bookmaker implied probabilities only as an external benchmark.
- Odds timestamps must precede the model prediction cutoff and match the canonical fixture.
- No fresh Odds API calls are needed for protocol development; preserve the stated credit budget.
- Market agreement is not proof of model accuracy and cannot replace the climatology/team-aware baselines.

## 9. Admission output

Evaluator result must be one of:

- `RETROSPECTIVE_SHADOW_ADMITTED`: retrospective primary gate passes with sufficient power and required evidence. Only labelled RESEARCH ONLY output is allowed.
- `REJECTED_PRIMARY_METRIC`: candidate fails 1X2 log-loss comparison against either baseline.
- `INSUFFICIENT_STATISTICAL_POWER`: MDE/power requirement not met.
- `REJECTED_CHRONOLOGY_OR_PROVENANCE`: leakage, PIT, rights, identity or fixture-join failure.
- `PUBLISHED_ADMISSION_PENDING_PROSPECTIVE_EVIDENCE`: retrospective SHADOW tier passed but prospective settled evidence or explicit sign-off is absent.
- `PUBLISHED_ADMITTED`: prospective evidence, all release gates and explicit user sign-off are present.
- `QUARANTINED`: any runtime or audit breach; existing forecasts become invisible through admission-aware API views.

The evaluator never writes forecasts. It writes immutable evaluation evidence only.
