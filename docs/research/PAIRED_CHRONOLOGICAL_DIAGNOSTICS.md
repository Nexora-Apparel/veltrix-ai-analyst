# Paired chronological model diagnostics

## Input and protocol

The evaluator consumes the immutable JSON artifact produced by
`scripts/train_retrospective_research.py`. Elo, Poisson and adaptive ensemble
are scored on the exact same ordered fixture rows. The ensemble vector is
reconstructed per fixture from the recorded Elo weight and the Elo/Poisson
vectors; no bookmaker odds are read or requested.

This is a full-corpus prequential retrospective protocol using lagged results.
It is explicitly **not PIT-certified**.

## Outputs

- Overall 1X2 multiclass Brier and log loss for all three models.
- Four approximately equal chronological periods, with simultaneous kickoff
  groups kept intact.
- Cold-start/warm-up phases based on the number of prior FINISHED fixtures
  available before each kickoff batch: 0, 1–4, 5–19, 20–49 and 50+.
- Paired moving chronological block-bootstrap 95% percentile intervals for
  each pairwise model difference, separately for Brier and log loss.
- Classwise one-vs-rest reliability bands (0.1 probability width) and
  classwise expected calibration error for home win, draw and away win.

Negative paired differences mean the left-hand model has lower loss than the
right-hand model. Bootstrap resampling uses the same sampled chronological
blocks for both models in each pair, preserving pairing. The report records
the seed, resample count and block size for reproducibility.

## Run

From `backend/`:

```bash
python scripts/evaluate_paired_chronological.py \
  --input artifacts/retrospective-training-report.json \
  --output artifacts/paired-chronological-diagnostics.json \
  --resamples 5000 --block-size 20 --seed 20261118
```

This is a local/offline artifact calculation. It makes no provider requests,
does not connect to Neon, and does not spend The Odds API credits.

## Protocol separation

Do not merge or average this scorecard with the existing nested chronological
walk-forward report. The nested report uses a distinct held-out fixture set,
fold construction and nested parameter selection. Comparisons across these
protocols are not paired and cannot establish model superiority. Any future
head-to-head model selection must be performed on one common, predeclared
evaluation sample and protocol.

Neither this diagnostic report nor the existing retrospective reports
establish PIT eligibility, prospective performance, bookmaker-market
outperformance, CLV or value-betting certification. Production promotion and
value betting remain blocked by their independent gates.

## Mandatory kickoff-integrity prerequisite

The evaluator trusts the `kickoff_at` values in its input report and does not independently adjudicate them against official competition schedules. Do not use its output as trusted chronological or model-selection evidence until every fixture kickoff has been reconciled and simultaneous kickoff batches are represented correctly.

A live CBF audit of rounds 25–30 found provider fixture `2179333578` (CBF ref 262, São Bernardo x Londrina) stored at 20:49:59 BRT, while the official CBF match record is 19:30 BRT. The retrospective training artifact contains the provider timestamp and places another fixture from the same official 19:30 kickoff (`3196722470`, Vila Nova x Goiás) earlier in the sequence. This creates a possible same-kickoff leakage path if the training runner updates state fixture-by-fixture. The training runner's simultaneous-batch behavior must be inspected, the chronology corrected in a separate evidence-backed research layer, and the retrospective predictions regenerated before paired diagnostics are interpreted. Never rewrite the raw provider timestamp to hide this discrepancy.
