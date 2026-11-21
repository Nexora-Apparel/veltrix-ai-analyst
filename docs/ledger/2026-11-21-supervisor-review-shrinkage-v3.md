# 2026-11-21 — Supervisor review and shrinkage repair v3.1

## Delta from v3

- Replaced the v3 k grid with `{0.5,1,2,4,8,16,32,64,128}`; half-life remains `{180,365,730}` days.
- Added preregistered probability blend weights `{0.25,0.5,0.75,1.0}`, with `p=w*p_model+(1-w)*p_climatology`.
- Added ten-bin HOME/DRAW/AWAY reliability tables, calibration slope/intercept, >0.80 probability counts and hit rates, paired date-block bootstrap comparisons against climatology and plain scaled Poisson, and competition-level breakdown.
- Fixed the convergence rule before evaluation: gradient L2 norm <=1e-7 AND relative objective change <=1e-10 for two consecutive accepted steps; max 200 Newton iterations; no post-hoc tolerance relaxation.
- Recorded exact archived-equivalent team k values: fold 1 128.3802704829587; fold 2 173.29424410186596; fold 3 206.5352382546307; fold 4 269.2584048267363 (diagnostic only).
- Canonical config SHA-256: `14333ab670983a692605e91705bc001707bc3c2319c1e94f116ddc15adcb44dd`.

## Fold-4 leakage review — read-only source artifact inspection

Source artifacts: Stage 6 dataset artifact 14694463354 and forecast artifact 14694089682 from the audit's pinned inputs. No model was refit and no candidate grid was evaluated.

- Fold 4 partition reproduced from the 996 training rows: 835 train rows, 161 test rows, cutoff 2026-10-28 17:30:00 UTC.
- Training kickoff timestamps at/after cutoff: 0.
- Exact cross-fold duplicates by canonical fixture ID: 0; provider fixture ID: 0; same-direction teams/date: 0; unordered teams/date: 0.
- Training labels with `label_observed_at >= fold cutoff`: 835/835.
- Training labels observed after their own kickoff: 835/835 (expected for settled results, but not proof they were available at a historical forecast cutoff).
- Per-row historical `prediction_cutoff_at` on training records: 0/835. Thus own-prediction-time availability cannot be established.
- Dataset exposes only aggregate `fixture_identity_rows=1053`; it does not include the 28 unresolved identity-case records. Those cases cannot be cleared from the supplied artifact.
- Therefore fold 4's 0.905 log loss for k=0.5 is not trustworthy as point-in-time evidence. It remains previously examined and is not clean validation.

### Requested high-probability attribution — unavailable without a new real-data evaluation

The sanitized audit JSON and source artifacts do not preserve per-test-fixture probabilities for the fold-4 k=0.5 fit, nor the per-fixture competition/outcome attribution needed to count forecasts above 0.80 and calculate their hit rate. No refit/replay was run because real-data evaluation requires the owner-dispatched workflow. These metrics remain required in the v3.1 evaluation output.

## Controls

No production or default optimizer change, quarantine change, lock change, feed enablement, database write, provider call, Odds API use, Telegram notification, merge, or workflow dispatch. PR #143 remains draft. All real-data evaluation remains owner-dispatched and read-only.
