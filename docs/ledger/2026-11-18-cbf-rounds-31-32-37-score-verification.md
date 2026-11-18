# CBF Série B 2026 score verification — rounds 31–32 and 37 (2026-11-18)

## Scope and execution

- Workflow: [run 44286701796](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286701796)
- Evidence artifact: [cbf-remaining-score-verification](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44286701796/artifacts/14419317538)
- Artifact SHA-256: `c1d6051e02f3b5d39a9ee61374e586241747b876c7887e4651944067e515d3f3`
- JSON report SHA-256: `8cd8efd187b2a7d1534e41e2c4c5bbe42e29821c066dbee4d6d377c82edaffeb`
- Database: `veltrix_ai_analyst`; read-only transaction
- Provider: 5DollarFootballAPI; competition `522514093`
- Raw provider rows changed: 0

## Result

<badge>27 / 27 verified</badge>

- Official CBF match pages: 27
- Provider fixture records matched: 27
- Score mismatches: 0
- Missing provider fixtures: 0
- Exact provider team labels matched: 27/27

| CBF ref | Round | Fixture | CBF score | Provider fixture ID |
|---:|---:|---|---:|---:|
| 301 | 31 | Botafogo-SP x Vila Nova | 0–1 | `1091678025` |
| 302 | 31 | São Bernardo x CRB | 3–1 | `2805830360` |
| 303 | 31 | Athletic-MG x Sport | 1–2 | `679654652` |
| 304 | 31 | Londrina x Criciúma | 0–2 | `1566836191` |
| 305 | 31 | Fortaleza x Náutico | 1–1 | `157772905` |
| 306 | 31 | Atlético-GO x América-MG | 2–0 | `2385956390` |
| 307 | 31 | Avaí x Ceará | 0–1 | `4118537950` |
| 308 | 31 | Novorizontino x Goiás | 3–0 | `3774242963` |
| 309 | 31 | Cuiabá x Ponte Preta | 2–0 | `957301731` |
| 310 | 31 | Juventude x Operário-PR | 3–0 | `2907742700` |
| 311 | 32 | Ponte Preta x Juventude | 0–2 | `3566581788` |
| 312 | 32 | Sport x São Bernardo | 2–1 | `780158030` |
| 313 | 32 | América-MG x Fortaleza | 0–1 | `2127073988` |
| 314 | 32 | Operário-PR x Botafogo-SP | 1–2 | `1523389359` |
| 315 | 32 | Ceará x Criciúma | 1–0 | `1896319805` |
| 316 | 32 | Goiás x Athletic-MG | 2–1 | `118503256` |
| 317 | 32 | Avaí x Londrina | 2–1 | `1615301508` |
| 318 | 32 | Náutico x Novorizontino | 0–2 | `2218351212` |
| 319 | 32 | CRB x Atlético-GO | 3–1 | `2953261326` |
| 320 | 32 | Vila Nova x Cuiabá | 0–0 | `2558236640` |
| 362 | 37 | Novorizontino x Fortaleza | 2–1 | `1350157273` |
| 363 | 37 | Athletic-MG x Atlético-GO | 2–3 | `672570090` |
| 364 | 37 | Operário-PR x Sport | 3–2 | `3418633874` |
| 365 | 37 | Ceará x América-MG | 0–1 | `3749693447` |
| 366 | 37 | Goiás x Ponte Preta | 1–0 | `3728617699` |
| 367 | 37 | Avaí x São Bernardo | 2–1 | `751482855` |
| 368 | 37 | Náutico x CRB | 0–3 | `4070869087` |

## Official CBF sources

Each fixture above is linked to its individual official CBF match page in the machine-readable evidence registry:
`backend/data/research/cbf_rounds31_32_37_official_results.json`.

The CBF match-reference numbers are cross-referenced against the official detailed schedules:
- [Rounds 31–34 detailed schedule](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_31_a_34_rodada_Brasileiro_Serie_B_2026_0d7da23918.pdf)
- [Rounds 35–38 detailed schedule](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_35_a_38_rodada_Brasileiro_Serie_B_2026_1_f9990e396e.pdf)

## Boundaries

- Provider fixture IDs and exact provider team labels were checked; no canonical team merge is approved.
- The audit is read-only; no production source rows or observation rows were modified.
- This score verification does not establish historical point-in-time feature availability.
