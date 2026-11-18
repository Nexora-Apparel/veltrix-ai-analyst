# CBF Série B 2026 score verification — rounds 33–36 (2026-11-18)

## Scope and execution

- Workflow: [run 44285577512](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44285577512)
- Evidence artifact: [cbf-rounds-33-36-score-verification](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44285577512/artifacts/14418144179)
- Artifact SHA-256: `5d9c06950cddc640548868bad0029e141c378647298df46c29c836160b498241`
- JSON report SHA-256: `60152baee42372b382c290ba9a8ec102cdaf86890e0d10819788a31055cda2a3`
- Database: `veltrix_ai_analyst`; read-only transaction
- Provider: 5DollarFootballAPI; competition `522514093`
- Raw provider rows changed: 0

## Result

**40 / 40 verified; 0 mismatches; 0 missing fixtures.**

| Round | Official CBF results | Provider scores matched | New unique scores |
|---:|---:|---:|---:|
| 33 | 10 | 10 | 9 |
| 34 | 10 | 10 | 10 |
| 35 | 10 | 10 | 10 |
| 36 | 10 | 10 | 9 |
| **Total** | **40** | **40** | **38** |

Two results overlap prior individual CBF match-page checks:
- CBF ref 325: Fortaleza 2–2 CRB.
- CBF ref 360: Goiás 2–1 CRB.

These are verified again in this article-based pass but are not double-counted.

## Official CBF results sources

- [Round 33 — Novorizontino assumes second place](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-b/a/novorizontino-chega-a-terceira-vitoria-seguida-na-serie-b-e-assume-vice-lideranca)
- [Round 33 — Athletic 2–2 Londrina](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-b/a/athletic-e-londrina-empatam-em-2-a-2-pela-serie-b)
- [Round 34 — round results through 18 October](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/segundo-colocado-novorizontino-empate-no-ultimo-lance-com-lider-vila-nova)
- [Round 34 — Goiás 0–0 Náutico](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/goias-e-nautico-nao-movimentam-placar-em-jogo-pela-34a-rodada-da-serie-b)
- [Round 34 — Londrina 1–0 Cuiabá](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/serie-b-londrina-vence-cuiaba-mas-permanece-na-zona-de-rebaixamento)
- [Round 35 — Goiás beats Ceará; round results](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/com-dois-golacos-nos-acrescimos-goias-bate-ceara-pela-serie-b)
- [Round 36 — final-round access race and results](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/serie-b-10-equipes-brigam-pelo-acesso-na-reta-final-da-primeira-fase)

The official CBF detailed schedules supply the CBF reference numbers:
- [Rounds 31–34 detailed schedule](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_31_a_34_rodada_Brasileiro_Serie_B_2026_0d7da23918.pdf)
- [Rounds 35–38 detailed schedule](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_35_a_38_rodada_Brasileiro_Serie_B_2026_1_f9990e396e.pdf)

## Boundaries

- The sources are official CBF round-results articles, not 40 individual match pages.
- CBF references were checked against the official detailed schedules; provider fixture IDs and exact provider team labels were checked in the read-only database comparison.
- This does not approve canonical team merges or PIT eligibility.
- No production source rows were modified.
