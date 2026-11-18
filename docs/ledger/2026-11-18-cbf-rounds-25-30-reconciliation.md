# CBF fixture reconciliation — rounds 25–30 (2026-11-18)

## Scope and method

This is a fixture-level schedule reconciliation of the 60 5DollarFootballAPI FINISHED rows assigned to CBF Série B 2026 rounds 25–30 (CBF match references 241–300). It is read-only: no production fixture, source-observation, canonical-identity, or PIT records were changed.

The comparison joined each CBF reference to the provider fixture using the ordered home/away provider team IDs, then compared the provider kickoff converted to `America/Sao_Paulo` against the official CBF local date/time. Team identity was mapped through the existing reviewed candidate matrix; this schedule comparison does not approve aliases or canonical merges.

## Result

| Check | Result |
|---|---:|
| CBF schedule references | 60 (241–300) |
| Provider FINISHED fixtures in scope | 60 |
| Ordered home/away pairings found | 60/60 |
| Exact kickoff matches against the original detailed PDF | 53/60 |
| Official CBF schedule changes explaining differences | 6 |
| Provider kickoff discrepancies remaining after official changes | 1 raw timestamp; corrected in research layer |
| Changed/discrepant scorelines cross-checked against CBF match pages | 7/7 |
| Production rows modified | 0 |

Six provider kickoff times match official CBF changes to the original detailed schedule. The seventh discrepancy (ref 262) has now been corrected through the research-only chronology adjudication registry. All 60 rows therefore have a reconciled research kickoff; raw provider timestamps remain unchanged.

## Six official schedule changes

| CBF ref | Provider fixture ID | Fixture | Original detailed schedule (BRT) | CBF confirmed played time (BRT) | Provider time (BRT) | Provider score |
|---:|---:|---|---|---|---|---:|
| 247 | 2374694874 | Avaí x Atlético-GO | 30 Aug, 11:00 | 30 Aug, 16:00 | 30 Aug, 16:00 | 0–1 |
| 267 | 3333656081 | Criciúma x Juventude | 8 Sep, 21:30 | 8 Sep, 21:00 | 8 Sep, 21:00 | 0–2 |
| 279 | 997354348 | CRB x Sport Recife | 15 Sep, 21:30 | 15 Sep, 21:00 | 15 Sep, 21:00 | 2–1 |
| 287 | 2279851191 | Criciúma x Operário-PR | 21 Sep, 19:30 | 22 Sep, 19:30 | 22 Sep, 19:30 | 0–2 |
| 294 | 496665715 | Operário-PR x Ceará | 26 Sep, 16:00 | 26 Sep, 16:30 | 26 Sep, 16:30 | 2–2 |
| 298 | 136318749 | Náutico x Sport Recife | 26 Sep, 20:30 | 26 Sep, 16:30 | 26 Sep, 16:30 | 3–1 |

## Research-only chronology adjudication applied — CBF ref 262

| Field | Value |
|---|---|
| Fixture | São Bernardo x Londrina |
| Provider fixture ID | `2179333578` |
| CBF official reference | 262 |
| Original and current CBF kickoff | 10 Sep 2026, 19:30 BRT |
| Provider `kickoff_at` | 10 Sep 2026, 20:49:59 BRT |
| Provider UTC timestamp | `2026-09-10T23:49:59Z` |
| Provider score | 1–2 |
| CBF score | 1–2 |
| Source observation ID | `1052` |
| Provider observation retrieved | `2026-11-16T21:53:08.484Z` |
| Source-published timestamp | NULL |
| Available-at timestamp | NULL |
| Adjudication | APPLIED in research-only registry; raw provider timestamp preserved |

The provider's raw payload contains `kickoff_at=2026-09-10T23:49:59Z`; this is not a display-time conversion issue. The official CBF match page records 19:30 BRT and the same 1–2 score. The correction is recorded separately in `backend/data/research/official_kickoff_adjudications.json`.

The retrospective training artifact contains fixture `2179333578` at `2026-09-10T23:49:59+00:00`, while fixture `3196722470` (Vila Nova x Goiás) appears at `2026-09-10T22:30:00+00:00`. CBF's official schedule places both CBF refs 262 and 270 at 19:30 BRT on 10 September. The training code was inspected: `chronological_research_run` batches only rows with exactly equal `kickoff_at` values, predicts each batch, then updates Elo/history from that batch. Because the provider timestamp splits these two simultaneous CBF fixtures into separate batches, the 2–0 result from fixture `3196722470` is included in the history used to predict fixture `2179333578`. The prequential prediction for `2179333578` is therefore confirmed to contain same-kickoff look-ahead leakage. The adaptive ensemble's prior-scored prediction set is also advanced before the contaminated fixture is scored. The current 380-fixture report and all aggregate metrics that include this row are provisional and must be regenerated after correction.

Do not rewrite the provider's raw kickoff timestamp. The research-only adjudication is applied. The corrected training report and paired diagnostics were regenerated in workflow [44281629472](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44281629472). The evaluator preserves simultaneous-kickoff batches. The fixture remains excluded from PIT-certified evidence because source publication/availability evidence is absent.

## Official CBF evidence

Original detailed schedule:
- Rounds 25–30, CBF detailed table published 13 August 2026: https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_25_a_30_rodada_Brasileiro_Serie_B_2026_b4b09851d2.pdf

Official match/change evidence:
- Ref 247, Avaí x Atlético-GO, 30 August 16:00, 0–1; CBF alteration record changes 11:00 to 16:00: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/avai-x-atletico-goianiense-saf/833128?view=alteracoes
- Ref 262, São Bernardo x Londrina, 10 September 19:30, 1–2: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sao-bernardo-saf-x-londrina-saf/833143
- Ref 267, Criciúma x Juventude, 8 September 21:00, 0–2; CBF alteration record changes 21:30 to 21:00: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/criciuma-x-juventude/833148?view=alteracoes
- Ref 279, CRB x Sport Recife, 15 September 21:00, 2–1; official CBF match history: https://www.cbf.com.br/futebol-brasileiro/times/campeonato-brasileiro/serie-b/2026/20032?tab=historico-de-partidas
- Ref 287, Criciúma x Operário-PR, 22 September 19:30, 0–2; CBF alteration record changes 21 September to 22 September: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/criciuma-x-operario/833172?view=alteracoes
- Ref 294, Operário-PR x Ceará, 26 September 16:30, 2–2; CBF alteration record changes 16:00 to 16:30: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/operario-x-ceara/833185?view=alteracoes
- Ref 298, Náutico x Sport Recife, 26 September 16:30, 3–1; CBF alteration record changes 20:30 to 16:30: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/nautico-x-sport-recife/833189?view=alteracoes

## Boundaries and next checks

- This pass covers rounds 25–30 only (60/380 fixtures). Rounds 1–24 and 31–38 now have separate schedule reconciliation ledgers.
- The seven changed/discrepant scorelines were checked against official CBF match pages. The other 53 scorelines still need independent CBF match-page score comparison.
- Do not modify raw provider fixture/source rows to make them agree with CBF. Keep adjudicated schedule data separate and traceable.
- The 380 FINISHED and four UNKNOWN fixture observations still have zero source-publication timestamps, zero availability timestamps, and zero PIT-certifiable observations.
- No bookmaker odds, Odds API credits, prediction model, or value-betting logic was used in this audit.
