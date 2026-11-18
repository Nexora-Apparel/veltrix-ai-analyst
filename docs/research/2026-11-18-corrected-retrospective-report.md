# Corrected retrospective research report — 2026-11-18

## Execution and provenance

- Workflow: [run 44280512801](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44280512801)
- Source commit: `a45b634daea37221cfdc63b6d31eb7ff584dff3d`
- Database: `veltrix_ai_analyst` (read-only transaction)
- Provider/source/competition: `5DollarFootballAPI` / `5dollarfootballapi` / `522514093`
- Raw source rows: 384
- FINISHED labeled rows: 380
- UNKNOWN unlabeled rows excluded: 4
- Invalid rows: 0
- Distinct provider-local teams in finished corpus: 20
- Date range: 2026-03-21T20:00:00Z through 2026-11-14T19:30:00Z
- Chronology basis: provider kickoff with evidence-backed official CBF adjudication
- PIT status: NOT PIT CERTIFIED; retrospective lagged-results research only
- Odds used: none
- Provider requests / Neon writes / Odds API credits: none

## Official kickoff adjudication

Exactly one research-only adjudication was consumed:

- CBF ref 262, São Bernardo x Londrina, provider fixture `2179333578`
- Raw provider kickoff: `2026-09-10T23:49:59Z`
- Official CBF kickoff: `2026-09-10T22:30:00Z` (19:30 America/Sao_Paulo)
- Official CBF match record: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sao-bernardo-saf-x-londrina-saf/833143
- The provider score and CBF score both record 1–2.
- Raw provider fixture and source-observation rows were not changed.
- Registry validation passed; all registered adjudications were consumed.

## Corrected full-corpus prequential metrics

| Model | Matches | Brier | Log loss |
|---|---:|---:|---:|
| Elo | 380 | 0.63330884 | 1.05106409 |
| Poisson | 380 | 0.63043121 | 1.04788807 |
| Adaptive ensemble | 380 | 0.62916948 | 1.04567758 |

The ensemble has the lowest point estimate in this retrospective sample. This is descriptive only and does not establish statistically reliable superiority.

## Paired chronological diagnostics

- Evaluator: `evaluate_paired_chronological.py`
- Protocol: `RETROSPECTIVE_PREQUENTIAL_PAIRED_DIAGNOSTICS_NOT_PIT_CERTIFIED`
- Predictions: 380
- Bootstrap: 2,000 resamples; moving chronological blocks of 20 fixtures; whole simultaneous-kickoff batches retained; seed `20261118`.
- Source report SHA-256: `98c18b77e24e3adb47beaaf834ec2993cb5178982f2f5aec54ea29eec2415ccc`

Paired differences are left model minus right model; negative values favour the left model.

| Comparison | Brier difference | 95% CI | Log-loss difference | 95% CI |
|---|---:|---:|---:|---:|
| Elo − Ensemble | +0.004139 | [-0.000457, +0.011204] | +0.005387 | [-0.001053, +0.015661] |
| Elo − Poisson | +0.002878 | [-0.008503, +0.017872] | +0.003176 | [-0.013209, +0.025647] |
| Poisson − Ensemble | +0.001262 | [-0.007691, +0.007650] | +0.002210 | [-0.011355, +0.011441] |

All six confidence intervals cross zero. The sample does not establish a statistically clear winner between Elo, Poisson and the adaptive ensemble. Do not promote a model or tune production parameters from this result.

## Chronological and cold-start diagnostics

Four chronological periods contain 91, 97, 99 and 93 fixtures respectively. The early sample is unstable: the first 50 fixtures show substantially higher losses than the mature 330-fixture period. Retain cold-start safeguards and evaluate on additional independent competitions/seasons before any selection decision.

## Boundaries

1. This is a full-corpus prequential retrospective scorecard, not a historical point-in-time replay.
2. Source publication and availability timestamps remain absent; none of the 384 provider observations is PIT-certifiable.
3. Team identifiers remain provider-local; this report does not approve canonical team identity links.
4. Four UNKNOWN source rows remain excluded as unlabeled observations. Their duplicate candidates remain in the human-review queue; raw rows are preserved.
5. Do not compare or pool these metrics with the separate nested walk-forward protocol.
6. Do not activate value betting, production prediction publication, or Android prediction endpoints from this report.

## Artifacts

- Corrected report artifact: [download from workflow run](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44280512801/artifacts/14415339764)
- Paired diagnostics artifact: [download from workflow run](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44280512801/artifacts/14416776631)
- Report SHA-256: `98c18b77e24e3adb47beaaf834ec2993cb5178982f2f5aec54ea29eec2415ccc`
