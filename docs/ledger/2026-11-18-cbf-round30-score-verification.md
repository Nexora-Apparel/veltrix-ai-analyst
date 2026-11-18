# CBF Série B 2026 score verification — round 30 (2026-11-18)

## Scope and execution

- Workflow: [run 44284780532](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44284780532)
- Evidence artifact: [cbf-round30-score-verification](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44284780532/artifacts/14417864681)
- Artifact SHA-256: `203a1f7d2edc9e222fda807c026a6c3bebd14ede493449846d18246d268ed637`
- JSON report SHA-256: `324bb0ee193ebc1da8164fc10aa4662b37cd75380d87d484837100db57ad5555`
- Database: `veltrix_ai_analyst`; read-only transaction
- Provider: 5DollarFootballAPI; competition `522514093`
- Raw provider rows changed: 0

## Result

**10 / 10 verified; 0 mismatches; 0 missing fixtures.**

| CBF ref | Fixture | Official CBF score | Provider fixture ID |
|---:|---|---:|---:|
| 291 | Botafogo-SP x Ponte Preta | 2–0 | `3266706807` |
| 292 | Novorizontino x São Bernardo | 0–0 | `2013695471` |
| 293 | América-MG x Juventude | 0–1 | `400939676` |
| 294 | Operário-PR x Ceará | 2–2 | `496665715` |
| 295 | Fortaleza x Athletic-MG | 2–2 | `3011700618` |
| 296 | Goiás x Atlético-GO | 0–1 | `3545396550` |
| 297 | Criciúma x Avaí | 3–0 | `4029087001` |
| 298 | Náutico x Sport | 3–1 | `136318749` |
| 299 | CRB x Cuiabá | 3–0 | `2572294410` |
| 300 | Vila Nova x Londrina | 2–0 | `3465954523` |

## Official CBF sources

- [CBF: Vitória de Juventude e Botafogo-SP encerram 30ª rodada](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/vitorias-de-juventude-e-botafogo-sp-encerram-30-rodada-da-serie-b) — published 30 September 2026; reports the round's results.
- [CBF: Fortaleza empata com Athletic e permanece em 2º](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/fortaleza-empata-com-athletic-e-permanece-em-2-na-serie-b) — corroborating report for Fortaleza 2–2 Athletic.

The first article lists eight results and describes the other two (Juventude 1–0 América-MG and Botafogo-SP 2–0 Ponte Preta) in its body. The registry preserves the source text and provider-local fixture IDs.

## Boundaries

- The evidence is from official CBF round-results articles, not 10 individual match pages.
- Team labels are checked against the exact provider fixture record, but no canonical team merge is approved.
- No source/provider rows were modified; this does not establish PIT availability.
