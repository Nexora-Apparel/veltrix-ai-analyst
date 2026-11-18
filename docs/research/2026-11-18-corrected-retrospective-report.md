# Corrected retrospective research report — 2026-11-18 (v2)

## Execution and provenance

- Workflow: [run 44281629472](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44281629472)
- Source commit: `cef8f9efcbfb61a096a890e0083d58e3f5867c98`
- Database: `veltrix_ai_analyst` (read-only transaction)
- Provider/source/competition: `5DollarFootballAPI` / `5dollarfootballapi` / `522514093`
- Raw source rows: 384
- FINISHED labeled rows: 380
- UNKNOWN unlabeled rows excluded: 4
- Invalid rows: 0
- Distinct provider-local teams in finished corpus: 20
- Date range: 2026-03-21T20:00:00Z through 2026-11-14T19:30:00Z
- Chronology basis: provider kickoff with evidence-backed official CBF adjudications
- PIT status: NOT PIT CERTIFIED; retrospective lagged-results research only
- Odds used: none
- Provider requests / Neon writes / Odds API credits: none

## Official kickoff adjudications

Exactly two research-only adjudications were consumed. Both preserve raw provider rows and source observations unchanged.

| CBF ref | Fixture | Provider fixture | Raw provider kickoff (UTC) | Official CBF kickoff (UTC) |
|---:|---|---:|---|---|
| 6 | Goiás x América | 3116209225 | 2026-03-22 20:58:35 | 2026-03-22 21:00:00 |
| 262 | São Bernardo x Londrina | 2179333578 | 2026-09-10 23:49:59 | 2026-09-10 22:30:00 |

- Ref 6: CBF records the scheduled kickoff at 18:00 BRT and the 3–1 result. The provider timestamp was 17:58:35 BRT. Normalizing to the official 18:00 batch prevents a potentially unsafe split of simultaneous matches. [Official CBF match page](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843)
- Ref 262: CBF records kickoff at 19:30 BRT (22:30 UTC), score 1–2. The provider timestamp was 23:49:59 UTC. [Official CBF match page](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sao-bernardo-saf-x-londrina-saf/833143)

Registry validation passed: both entries matched their raw provider rows, and all registered adjudications were consumed.

## Corrected full-corpus prequential metrics

| Model | Matches | Brier | Log loss |
|---|---:|---:|---:|
| Elo | 380 | 0.63336366 | 1.05113130 |
| Poisson | 380 | 0.63054946 | 1.04804403 |
| Adaptive ensemble | 380 | 0.62933489 | 1.04588885 |

The ensemble has the lowest point estimate in this retrospective sample. This does not establish statistically reliable superiority.

## Paired chronological diagnostics

- Evaluator: `evaluate_paired_chronological.py`
- Protocol: `RETROSPECTIVE_PREQUENTIAL_PAIRED_DIAGNOSTICS_NOT_PIT_CERTIFIED`
- Predictions: 380
- Bootstrap: 2,000 resamples; moving chronological blocks of 20 fixtures; whole simultaneous-kickoff batches retained; seed `20261118`.
- Source report SHA-256: `1eb2ff33999df3d9c83af5d89a9006fca6b3e096ef8b4b83285fc05aa69d8ca3`

Paired differences are left model minus right model; negative values favour the left model.

| Comparison | Brier difference | 95% CI | Log-loss difference | 95% CI |
|---|---:|---:|---:|---:|
| Elo − Ensemble | +0.004029 | [-0.000681, +0.010797] | +0.005242 | [-0.001237, +0.015100] |
| Elo − Poisson | +0.002814 | [-0.007758, +0.018282] | +0.003087 | [-0.012022, +0.026389] |
| Poisson − Ensemble | +0.001215 | [-0.007751, +0.007759] | +0.002155 | [-0.011253, +0.011626] |

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

- Corrected report artifact: [download from workflow run](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44281629472/artifacts/14417271623)
- Paired diagnostics artifact: [download from workflow run](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44281629472/artifacts/14417565846)
- Report SHA-256: `1eb2ff33999df3d9c83af5d89a9006fca6b3e096ef8b4b83285fc05aa69d8ca3`

The earlier 2026-11-18 report generated with only ref 262 adjudicated is superseded by this v2 report.
