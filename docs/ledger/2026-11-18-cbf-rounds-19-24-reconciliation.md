# CBF fixture reconciliation — rounds 19–24 (2026-11-18)

## Scope and method

This read-only audit covers CBF Série B 2026 match references 181–240 (60 fixtures) against the 5DollarFootballAPI FINISHED rows in competition `522514093`.

The join used ordered home/away provider team IDs from the existing reviewed candidate matrix. Provider `kickoff_at` was converted to `America/Sao_Paulo` before comparing with the official CBF local kickoff. No aliases or canonical team merges were approved in this pass.

## Result

| Check | Result |
|---|---:|
| CBF schedule references | 60 (181–240) |
| Provider FINISHED rows in scope | 60 |
| Ordered home/away pairings found | 60/60 |
| Exact local kickoff matches | 60/60 |
| Missing ordered pairings | 0 |
| Kickoff discrepancies | 0 |
| Scorelines reconciled against the later official CBF score table (rounds 1–29) | 60/60 |
| Production rows modified | 0 |

The provider schedule timestamps agree with the official CBF schedule for all 60 ordered fixture pairings in rounds 19–24. A later official CBF score-table audit, updated 23 September 2026, independently reconciles all 60 scores in rounds 19–24; see [score verification rounds 1–29](2026-11-18-cbf-score-verification-rounds-1-29.md). The schedule reconciliation and score verification are separate evidence passes.

## Official CBF sources

- CBF announcement of the detailed schedule for rounds 19–24, published 6 July 2026: https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/cbf-divulga-tabela-detalhada-das-rodadas-19-a-24-da-serie-b
- CBF official Série B 2026 detailed-table page, printed 26 July 2026, which lists match references, opponents, dates and Brasília kickoff times: https://cbf-hml.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?documento=Tabela+Detalhada

The CBF schedule explicitly states that listed times are Brasília time and that the detailed schedule is the official day/time/location programming, unlike the basic table.

## Boundaries and next checks

- This pass covers rounds 19–24 only (60/380 fixtures). Rounds 1–18 schedule reconciliation is recorded in [the rounds 1–18 ledger](2026-11-18-cbf-rounds-1-18-reconciliation.md).
- All 60 ordered pairings and kickoff times matched, but all 60 final scores still need independent CBF match-page verification.
- Team identity remains limited to the existing reviewed provider-ID candidate matrix. This audit does not approve aliases or canonical merges.
- The four UNKNOWN source rows and the separate America MG provider-team identity conflict remain unresolved.
- Source-publication and availability timestamps remain absent for the retrospective FINISHED corpus. This schedule reconciliation does not create PIT evidence.
- No bookmaker odds, Odds API credits, prediction models, or value-betting logic were used.
