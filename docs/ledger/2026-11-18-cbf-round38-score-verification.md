# CBF Série B 2026 score verification — round 38 (2026-11-18)

## Scope and execution

- Workflow: [run 44284653062](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44284653062)
- Evidence artifact: [cbf-round38-score-verification](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44284653062/artifacts/14418138075)
- Artifact SHA-256: `fad66dc4fae4b0f890c9637b2f590d21860c1641105ab453c544505c762f959d`
- JSON report SHA-256: `52dc823ebfcd087b6494d1c8a02a8e742e931b8bf8e74fd778b68f61326ef00f`
- Database: `veltrix_ai_analyst`; read-only transaction
- Provider: 5DollarFootballAPI; competition `522514093`
- Raw provider rows changed: 0

## Result

**10 / 10 verified; 0 mismatches; 0 missing fixtures.**

| CBF ref | Fixture | Official CBF score | Provider fixture ID |
|---:|---|---:|---:|
| 371 | Ponte Preta x Operário-PR | 0–2 | `2124148156` |
| 372 | São Bernardo x Athletic-MG | 2–2 | `2521759856` |
| 373 | América-MG x Avaí | 0–2 | `1194891794` |
| 374 | Londrina x Náutico | 2–1 | `1878457839` |
| 375 | Fortaleza x Vila Nova | 1–0 | `2100843448` |
| 376 | Atlético-GO x Cuiabá | 1–0 | `4281273739` |
| 377 | Criciúma x Novorizontino | 0–1 | `186598545` |
| 378 | Sport x Goiás | 3–0 | `322759957` |
| 379 | CRB x Ceará | 1–1 | `930712726` |
| 380 | Juventude x Botafogo-SP | 2–0 | `1366792905` |

## Official CBF source

[CBF: Novorizontino é campeão da Série B](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-b/a/novorizontino-e-campeao-da-serie-b), published 14 November 2026. It records the title match, Juventude's 2–0 win over Botafogo-SP, five simultaneous fixtures and three matches played earlier in the week.

## Unique verification accounting

Three fixtures (CBF refs 371, 372 and 374) were already individually checked against CBF match pages in the rounds 31–38 schedule-exception pass. They are not double-counted. This round-38 audit therefore adds **7 new unique verified scores** to the corpus.

## Boundaries

- This is an official CBF round-results article, not 10 individual match pages.
- Provider-local fixture IDs and exact provider team labels were checked; no canonical team merge is approved.
- No source/provider rows were modified; this does not establish PIT availability.
