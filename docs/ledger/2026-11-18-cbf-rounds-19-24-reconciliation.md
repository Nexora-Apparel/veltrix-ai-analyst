# CBF fixture reconciliation — rounds 19–24 (2026-11-18)

## Scope and method

This is a fixture-level schedule reconciliation of the 60 5DollarFootballAPI FINISHED rows assigned to CBF Série B 2026 rounds 19–24 (CBF match references 181–240). It is read-only: no production fixture, source-observation, canonical-identity, or PIT records were changed.

The comparison joined each CBF reference to the provider fixture using the ordered home/away provider team IDs, then compared the provider kickoff converted to `America/Sao_Paulo` against the official CBF local date/time. Team identity was mapped through the existing reviewed candidate matrix; this schedule comparison does not approve aliases or canonical merges.

## Result

| Check | Result |
|---|---:|
| CBF schedule references | 60 (181–240) |
| Provider FINISHED fixtures in scope | 60 |
| Ordered home/away pairings found | 60/60 |
| Exact kickoff matches against the original detailed PDF | 58/60 |
| Official CBF schedule changes explaining differences | 2 |
| Exact kickoff matches after applying official CBF changes | 60/60 |
| Changed scorelines cross-checked against CBF match pages | 2/2 |
| Production rows modified | 0 |

All 60 ordered pairings are present. The two kickoff differences from the original PDF are explained by official CBF changes; the provider matches the current CBF match records for both.

## Two official schedule changes

| CBF ref | Provider fixture ID | Fixture | Original detailed schedule (BRT) | CBF confirmed played time (BRT) | Provider time (BRT) | Provider score |
|---:|---:|---|---|---|---|---:|
| 212 | 1445462732 | São Bernardo x Botafogo-SP | 16 Aug, 16:00 | 14 Aug, 19:30 | 14 Aug, 19:30 | 0–1 |
| 215 | 498786251 | Ceará x Cuiabá | 15 Aug, 18:30 | 15 Aug, 16:00 | 15 Aug, 16:00 | 1–3 |

Ref 212 was changed in two steps by CBF: the date/time moved from 16 August 16:00 to 14 August 19:00, then the time was adjusted to 19:30. Ref 215 was moved from 18:30 to 16:00 on the same date. The provider matches the final official kickoff for both.

## Official CBF evidence

Original detailed schedule:
- Rounds 19–24, CBF detailed table published 6 July 2026: https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_19_a_24_rodada_Brasileiro_Serie_B_2026_2043b0972d.pdf

Official match/change evidence:
- Ref 212, São Bernardo x Botafogo-SP, played 14 August at 19:30, 0–1; CBF alteration record shows the two-step date/time change: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sao-bernardo-saf-x-botafogo/833093?view=alteracoes
- Ref 215, Ceará x Cuiabá, played 15 August at 16:00, 1–3; CBF alteration record changes 18:30 to 16:00: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ceara-x-cuiaba/833096?view=alteracoes

## Boundaries and next checks

- This pass covers rounds 19–24 only (60/380 fixtures). Rounds 1–18 remain to be reconciled.
- Only the two changed scorelines were independently checked against official CBF match pages. The other 58 scorelines still need their own CBF match-page score comparison.
- Do not modify raw provider fixture/source rows to make them agree with CBF. Keep adjudicated schedule data separate and traceable.
- The 380 FINISHED and four UNKNOWN fixture observations still have zero source-publication timestamps, zero availability timestamps, and zero PIT-certifiable observations.
- No bookmaker odds, Odds API credits, prediction model, or value-betting logic was used in this audit.
