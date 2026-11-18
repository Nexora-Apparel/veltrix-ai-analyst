# CBF fixture reconciliation — rounds 31–38 (2026-11-18)

## Scope and method

This is a fixture-level schedule reconciliation of the 80 5DollarFootballAPI FINISHED rows assigned to CBF Série B 2026 rounds 31–38 (CBF match references 301–380). It is read-only: no production fixture, source-observation, canonical-identity, or PIT records were changed.

The production-side comparison joined each CBF match reference to the provider fixture by the ordered home/away provider team IDs, then compared the provider kickoff converted to `America/Sao_Paulo` against the CBF schedule's local date/time. Team identity was mapped through the existing reviewed candidate matrix; this schedule comparison does not approve aliases or canonical merges.

## Result

| Check | Result |
|---|---:|
| CBF schedule references | 80 (301–380) |
| Provider FINISHED fixtures in scope | 80 |
| Ordered home/away pairings found | 80/80 |
| Exact kickoff matches against the original detailed PDFs | 72/80 |
| Official CBF schedule changes explaining the differences | 8 |
| Exact kickoff matches after applying the official changes | 80/80 |
| Provider scorelines independently cross-checked against CBF match pages in schedule-exception pass | 8/8 changed fixtures |
| Production rows modified | 0 |

The eight original-schedule time/date differences are not provider mismatches: each matches the subsequently published CBF match page/current schedule. The 72 unchanged fixtures match the original CBF detailed PDFs exactly on ordered pairing and local kickoff.

## Eight official schedule changes

| CBF ref | Provider fixture ID | Fixture | Original detailed schedule (BRT) | CBF confirmed played time (BRT) | Provider score |
|---:|---:|---|---|---|---:|
| 325 | 792529849 | Fortaleza x CRB | 12 Oct, 20:30 | 12 Oct, 16:00 | 2–2 |
| 360 | 3457017936 | Vila Nova x Juventude | 31 Oct, 18:00 | 31 Oct, 17:30 | 2–2 |
| 361 | 1287617987 | Botafogo-SP x Londrina | 6 Nov, 19:30 | 5 Nov, 19:30 | 4–0 |
| 369 | 2927188191 | Cuiabá x Juventude | 6 Nov, 21:30 | 7 Nov, 20:00 | 1–2 |
| 370 | 1678471033 | Vila Nova x Criciúma | 6 Nov, 20:30 | 7 Nov, 20:00 | 1–0 |
| 371 | 2124148156 | Ponte Preta x Operário-PR | 14 Nov, 16:30 | 12 Nov, 19:00 | 0–2 |
| 372 | 2521759856 | São Bernardo x Athletic-MG | 14 Nov, 16:30 | 12 Nov, 20:00 | 2–2 |
| 374 | 1878457839 | Londrina x Náutico | 14 Nov, 16:30 | 11 Nov, 19:00 | 2–1 |

All times above are Brasília local time. Provider timestamps were converted from UTC using the `America/Sao_Paulo` timezone before comparison.

## Official CBF evidence

Original detailed schedules:
- Rounds 31–34, CBF detailed table published 14 September 2026: https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_31_a_34_rodada_Brasileiro_Serie_B_2026_0d7da23918.pdf
- Rounds 35–38, CBF detailed table published 7 October 2026: https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_35_a_38_rodada_Brasileiro_Serie_B_2026_1_f9990e396e.pdf

Official match/change evidence for the eight exceptions:
- Ref 325, Fortaleza x CRB, played 12 October at 16:00, 2–2: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-crb/833216
- Ref 360, Vila Nova x Juventude, played 31 October at 17:30, 2–2; CBF alteration record states original 18:00 changed to 17:30: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/vila-nova-x-juventude/833271?view=alteracoes
- Ref 361, Botafogo-SP x Londrina, played 5 November at 19:30, 4–0; CBF alteration record states original 6 November changed to 5 November: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/botafogo-x-londrina-saf/833272?view=alteracoes
- Ref 369, Cuiabá x Juventude, played 7 November at 20:00, 1–2; official CBF 2026 match/officials listing: https://www.cbf.com.br/a-cbf/arbitragem/arbitros/567/2026
- Ref 370, Vila Nova x Criciúma, played 7 November at 20:00, 1–0: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/vila-nova-x-criciuma/833281
- Ref 371, Ponte Preta x Operário-PR, played 12 November at 19:00, 0–2; CBF alteration record states original 14 November at 16:30 changed to 12 November at 19:00: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ponte-preta-x-operario/833282?view=alteracoes
- Ref 372, São Bernardo x Athletic-MG, played 12 November at 20:00, 2–2; official CBF 2026 match/officials listing: https://www.cbf.com.br/a-cbf/arbitragem/arbitros/1046/2026
- Ref 374, Londrina x Náutico, played 11 November at 19:00, 2–1: https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/sub-20-b/2026/londrina-saf-x-nautico/833285

The CBF 37th-round article also independently lists the revised 5–8 November match dates/times: https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-b/a/serie-b-penultima-rodada-da-1-fase-comeca-nesta-quinta-feira

## Boundaries and next checks

- This pass covers rounds 31–38 only (80/380 fixtures). Rounds 1–30 schedule reconciliation is now recorded in separate ledgers; see [rounds 1–18](2026-11-18-cbf-rounds-1-18-reconciliation.md), [19–24](2026-11-18-cbf-rounds-19-24-reconciliation.md), and [25–30](2026-11-18-cbf-rounds-25-30-reconciliation.md).
- Eight schedule-changed scorelines were individually checked against the cited official CBF match pages in the schedule-reconciliation pass. The official CBF round-38 results article verifies all 10 round-38 scores, with refs 371, 372 and 374 overlapping those eight. The separate official CBF articles for rounds 33–36 verify 40/40 scores, with refs 325 and 360 overlapping two of the eight individual page checks. The final 27 outstanding scores in rounds 31–32 and 37 were verified against individual official CBF match pages (27/27; zero mismatches; zero missing provider fixtures). The rounds 31–38 corpus is now **80/80 score-verified**. See [rounds 31–32 and 37](2026-11-18-cbf-rounds-31-32-37-score-verification.md), [rounds 33–36](2026-11-18-cbf-rounds-33-36-score-verification.md), and [round 38](2026-11-18-cbf-round38-score-verification.md).
- This does not resolve the four UNKNOWN stale/duplicate source rows or the America MG provider-team identity conflict. No team alias was approved and no canonical merge or fixture deduplication was performed.
- PIT eligibility is unchanged: the 380 FINISHED and four UNKNOWN fixture observations still have zero source-publication timestamps, zero availability timestamps, and zero PIT-certifiable observations. A match schedule or final score is not evidence that a pre-match feature was available before kickoff.
- No bookmaker odds, Odds API credits, prediction model, or value-betting logic was used.
