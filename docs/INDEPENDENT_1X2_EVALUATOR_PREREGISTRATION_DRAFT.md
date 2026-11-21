# VELTRIX independent 1X2 evaluation and pre-registration — draft

**Status:** draft only; no numeric release threshold is approved or frozen.  
**Owner:** independent validation path, separate from candidate model fitting.  
**Current model state:** QUARANTINED; production and value betting locked.

## 1. Primary endpoint

The sole primary metric is multiclass 1X2 log loss:

`LL = - mean(log(p_actual_outcome))`

Each forecast must contain a valid HOME/DRAW/AWAY probability triplet, each in (0,1), summing to 1 within a fixed numerical tolerance. No outcome may be removed after observing its result. The evaluator rejects duplicate fixture IDs, duplicate fixture/date records where canonical fixture identity is the same, non-finite probabilities, missing outcomes, or invalid prediction cutoffs.

**Direction:** lower log loss is better. Define paired improvement as baseline log loss minus candidate log loss; positive values favour the candidate.

## 2. Baselines (both mandatory)

The candidate must beat both baselines on the same fixture set:

1. **League climatology with home advantage:** fold-specific, training-only 1X2 outcome frequencies by competition, with a pre-registered shrinkage rule for sparse competitions. This is not a global 1X2 frequency that discards home advantage.
2. **Tuned team-aware baseline:** either a properly scaled simple Poisson goal model or Elo. Choice and all tuning rules are frozen on chronological development data before final holdout access. It must use the same eligible fixtures, timestamp cutoffs and rights-valid training labels as the candidate.

A candidate that beats only one baseline fails primary admission.

## 3. Chronology and data eligibility

- All splits are chronological and grouped by kickoff date.
- Training labels must have been system-observed, rights-valid and available by the fold's recorded training cutoff.
- Prediction generation time must be at or before the fixture's prediction cutoff, which must be strictly before kickoff.
- Validation labels must be settled and rights-valid for evaluation, but cannot enter that fold's training data.
- Historical imports lacking defensible point-in-time availability remain training-only and cannot become validation outcomes.
- Team identity is competition-scoped. Do not join across seasons using display names. Unresolved provider identity conflicts, ambiguous promotions/relegations, and unverified aliases are excluded or cause abstention.
- The evaluator accepts forecast records and labels only. It must not import the model fitter, feature builder, or prediction-generation modules.

## 4. Development, MDE and power

Before final holdout access:

1. Use nested chronological development folds to estimate paired daily log-loss improvement and its between-date variance.
2. Pre-register the smallest worthwhile 1X2 log-loss improvement, alpha, target power, and planned number of distinct holdout dates.
3. Compute minimum detectable effect (MDE) from the development-period date-block variance and planned holdout dates.
4. If MDE exceeds the pre-registered smallest worthwhile effect, or the planned holdout has insufficient dates/fixtures, admission fails for insufficient power. No threshold relaxation or post-hoc sample-size change is allowed.
5. Report power/MDE separately against both baselines; use the more demanding requirement.

Suggested values for review only (not approved): two-sided alpha 0.05 and power 0.80. The smallest worthwhile log-loss improvement and minimum sample/date thresholds remain blank pending explicit user approval.

## 5. Inference and uncertainty

- Primary comparison is paired on exactly the same fixtures.
- Use a paired bootstrap resampling whole kickoff-date blocks, preserving all fixtures from each sampled date.
- Report candidate-minus-baseline mean log-loss delta, improvement, 95% confidence interval and p-value for each baseline.
- Primary pass requires the lower 95% confidence bound of improvement to be strictly above zero against **both** baselines, and the pre-registered practical-effect/MDE gate to pass.
- Report overall, competition-stratified and favourite/draw/underdog diagnostics as descriptive secondary analyses. They do not replace the primary endpoint.

## 6. Secondary markets

BTTS and O/U 1.5, 2.5 and 3.5 are **not** separate admission tests at this stage. They are non-regression checks only after 1X2 primary admission passes. Do not tune or retest secondary markets to rescue a failed 1X2 result. Their non-regression margins must be separately drafted and approved before they are evaluated.

## 7. Final holdout: one use

- Final holdout period, eligible fixture set, dataset hash, forecast inputs, candidate version and evaluation protocol are frozen before first access.
- A durable evaluation-run record is written before scores are calculated, containing run UUID, candidate version, data/report hashes, baseline versions, protocol hash, holdout identifier/hash, start time and actor.
- Database uniqueness constraints prevent the same holdout hash from being evaluated more than once for the same admission decision.
- The evaluator writes completion status and output hash. Failed, interrupted or completed access burns that holdout; a failed candidate requires new unseen holdout data.
- Every nested development run and final holdout attempt is logged. No manual deletion or overwrite of failed attempts.
- No holdout is read while the candidate, baselines, thresholds or evaluator code remain mutable.

## 8. Evaluator isolation and test requirements

The independent evaluator module must contain only input validation, proper scoring rules, paired comparisons, MDE/power calculations, date-block bootstrap and report hashing. It must not import any model-building code.

Required tests:
- known probability triplets have exact expected log loss;
- malformed/non-normalized/zero probabilities reject;
- same fixture predicted twice rejects;
- prediction timestamp at/after kickoff rejects;
- label observed before kickoff rejects;
- label available after training cutoff is excluded from that fold;
- same fixture set is used for candidate and both baselines;
- block bootstrap resamples dates, not individual matches;
- MDE rises when variance increases and falls when planned dates increase;
- insufficient power fails closed;
- lower confidence bound must exceed zero against both baselines;
- secondary markets remain untested until primary passes;
- repeated final holdout hash is rejected by the evaluation-run ledger;
- a failed/aborted final attempt remains logged and burns the holdout.

## 9. Approval and freeze process

Before the first final holdout:
1. Publish a threshold sheet containing smallest worthwhile 1X2 log-loss improvement, alpha, power, minimum distinct dates, minimum fixtures, baseline tuning rules, bootstrap replicate count/seed policy, secondary-market non-regression margins and any competition-level minimums.
2. Obtain explicit user approval of the numeric values.
3. Canonicalize the sheet (stable key order, normalized numeric representation), calculate SHA-256, and freeze it as the protocol hash.
4. Any later threshold or protocol change creates a new protocol version. It cannot be applied retroactively to a holdout already consumed.

No numeric thresholds are frozen by this draft. No final holdout has been accessed.
