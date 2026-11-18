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
| Provider kickoff discrepancies remaining after official changes | 1 |
| Changed/discrepant scorelines cross-checked against CBF match pages | 7/7 |
| Production rows modified | 0 |

Six provider kickoff times match official CBF changes to the original detailed schedule. One row remains inconsistent with the current official CBF match record and is explicitly quarantined from trusted chronological research pending adjudication.

## Six official schedule changes

| CBF ref | Provider fixture ID | Fixture | Original detailed schedule (BRT) | CBF confirmed played time (BRT) | Provider time (BRT) | Provider score |
|---:|---:|---|---|---|---|---:|
| 247 | 2374694874 | Avaí x Atlético-GO | 30 Aug, 11:00 | 30 Aug, 16:00 | 30 Aug, 16:00 | 0–1 |
| 267 | 3333656081 | Criciúma x Juventude | 8 Sep, 21:30 | 8 Sep, 21:00 | 8 Sep, 21:00 | 0–2 |
| 279 | 997354348 | CRB x Sport Recife | 15 Sep, 21:30 | 15 Sep, 21:00 | 15 Sep, 21:00 | 2–1 |
| 287 | 2279851191 | Criciúma x Operário-PR | 21 Sep, 19:30 | 22 Sep, 19:30 | 22 Sep, 19:30 | 0–2 |
| 294 | 496665715 | Operário-PR x Ceará | 26 Sep, 16:00 | 26 Sep, 16:30 | 26 Sep, 16:30 | 2–2 |
| 298 | 136318749 | Náutico x Sport Recife | 26 Sep, 20:30 | 26 Sep, 16:30 | 26 Sep, 16:30 | 3–1 |

## Unresolved provider kickoff discrepancy — CBF ref 262

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
| Adjudication | OPEN — provider timestamp conflicts with official CBF match record |

The provider's raw payload contains `kickoff_at=2026-09-10T23:49:59Z`; this is not a display-time conversion issue. The official CBF match page records 19:30 BRT and the same 1–2 score.

The retrospective training artifact also contains fixture `2179333578` at `2026-09-10T23:49:59+00:00`, while the other same-official-kickoff fixture `3196722470` (Vila Nova x Goiás) appears at `2026-09-10T22:30:00+00:00`. This creates a possible same-kickoff ordering/leakage defect if the training runner updates model state fixture-by-fixture instead of treating the CBF-simultaneous kickoff batch atomically. The training runner's batch/update behavior must be inspected; leakage is not asserted as proven until that code path is checked.

Do not rewrite the provider's raw kickoff timestamp. Before this fixture or its downstream prequential metrics are treated as trusted:
1. Preserve the raw provider timestamp and this CBF evidence.
2. Add an explicit, separately sourced CBF kickoff adjudication/override in the research data layer, not in the raw provider row.
3. Ensure all fixtures with the same official kickoff are predicted before any result from that batch updates model state.
4. Regenerate the retrospective prequential report from the corrected chronology and re-run the paired diagnostics.
5. Keep the fixture excluded from PIT-certified evidence until actual source publication/availability evidence exists.

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

- This pass covers rounds 25–30 only (60/380 fixtures). Rounds 1–24 remain to be reconciled.
- The seven changed/discrepant scorelines were checked against official CBF match pages. The other 53 scorelines still need independent CBF match-page score comparison.
- Do not modify raw provider fixture/source rows to make them agree with CBF. Keep adjudicated schedule data separate and traceable.
- The 380 FINISHED and four UNKNOWN fixture observations still have zero source-publication timestamps, zero availability timestamps, and zero PIT-certifiable observations.
- No bookmaker odds, Odds API credits, prediction model, or value-betting logic was used in this audit.
