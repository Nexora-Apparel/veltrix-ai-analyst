# Corrected retrospective research report — 2026-11-18

## Execution and immutable evidence

- Commit: `9af309fbe9d5f34d1e650e0055e843da98bdb047`
- Workflow: [Rebuild retrospective research report — run 44286932299](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286932299)
- Result: **SUCCESS**
- Training report artifact: [corrected-retrospective-research-report](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286932299/artifacts/14419193217)
- Paired diagnostics artifact: [corrected-paired-chronological-diagnostics](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286932299/artifacts/14420445186)
- Canonical report SHA-256: `e5d8356a4cd34551d5fe2a5a98f0f3b476d338335873c0b721fd507a844c3caa`
- JSON artifact SHA-256: `0166c3dff1bc167a0e130b90082e9e320888a10d0d833b36d2707961b762275a`
- Paired diagnostics JSON SHA-256: `4d9701b505311126a4466dae4d99959e2d9217c84785e3f2e740cf92187bf0fb`
- Database: `veltrix_ai_analyst`; transaction explicitly read-only
- Provider: 5DollarFootballAPI; competition `522514093`
- No provider API calls, Odds API credits, or production writes were used.

## Corrected source accounting

| Item | Count |
|---|---:|
| Source observations | 384 |
| FINISHED labeled fixtures | 380 |
| UNKNOWN unlabeled rows excluded | 4 |
| Invalid rows | 0 |
| Provider-local teams | 20 |
| Evidence-backed official kickoff adjudications applied | 2 |
| Officially cross-checked score labels | 380 / 380 |
| Score labels still pending independent CBF check | 0 / 380 |

The report uses all 380 provider FINISHED labels for retrospective diagnostics, and all 380 scorelines now have independent official CBF cross-checks. The two chronology corrections are applied only to the research input; raw provider timestamps and source observations remain unchanged.

## Overall prequential metrics

| Model | Brier (lower is better) | Log loss (lower is better) |
|---|---:|---:|
| Elo | 0.63336366 | 1.05113130 |
| Poisson | 0.63054946 | 1.04804403 |
| Adaptive ensemble | 0.62933489 | 1.04588885 |

The ensemble has the best point estimates in this full-corpus retrospective prequential run. This is not sufficient evidence to select or promote it.

## Paired moving-block bootstrap

- 2,000 resamples
- 20-fixture chronological blocks
- Whole simultaneous-kickoff batches retained
- Seed: `20261118`

Differences are left model minus right model; negative values favour the left model.

| Comparison | Brier mean difference (95% CI) | Log-loss mean difference (95% CI) |
|---|---:|---:|
| Elo − ensemble | 0.00403 (−0.00068, 0.01080) | 0.00524 (−0.00124, 0.01510) |
| Elo − Poisson | 0.00281 (−0.00776, 0.01828) | 0.00309 (−0.01202, 0.02639) |
| Poisson − ensemble | 0.00121 (−0.00775, 0.00776) | 0.00216 (−0.01125, 0.01163) |

Every paired 95% interval crosses zero. The sample does not establish a statistically reliable winner among the three models.

## Chronological diagnostics

The 380 fixtures were split into four consecutive kickoff-time periods (92, 97, 98 and 93 fixtures). In the mature 50+ history phase (330 fixtures), Poisson had the best point estimates; the ensemble led in the two later full periods. These shifts reinforce that a single aggregate point estimate is not a promotion criterion.

Cold-start and warm-up diagnostics are included in the paired artifact. They remain descriptive and use the same retrospective label corpus.

## Explicit boundaries

- Dataset type: `RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED`.
- Feature semantics: lagged historical results; not historical point-in-time replay.
- Source-publication and availability timestamps remain absent for the historical 384 observations.
- The retrospective evaluation is not prospective deployment evidence and does not meet the 1,000-match walk-forward or 300-settled prospective-selection gates.
- No model was selected or promoted.
- Value betting remains locked.
- No bookmaker odds were used in the core prediction model.
- Android prediction integration remains deferred until real validated prediction endpoints exist.

## Next qualification work

1. Retain the 380/380 official CBF score-verification evidence and monitor future source integrity.
2. Resolve the 28 identity/quality review cases through evidence-backed human review; do not auto-merge ambiguous teams or fixtures.
3. Implement forward-only immutable source snapshots with source publication, retrieval and verified availability timestamps plus provider rights metadata.
4. Expand prospective, multi-competition validation before any model-selection or production decision.
