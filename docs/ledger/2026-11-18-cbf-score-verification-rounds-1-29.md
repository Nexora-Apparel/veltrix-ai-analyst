# CBF Série B 2026 score verification — rounds 1–29 (2026-11-18)

## Scope and execution

- Workflow: [run 44283802008](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44283802008)
- Evidence artifact: [cbf-score-verification-rounds-1-29](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44283802008/artifacts/14417383290)
- Artifact SHA-256: `f31b198277c6ba11d2fd30906eacaf90898de7cad607eea761a772ad8f528685`
- JSON report SHA-256: `be15200c8e18aa5de5027b7f72e093bb87a3a9d20bd38f4f3a0820736e5bb8bc`
- Database: `veltrix_ai_analyst`; read-only transaction
- Provider: 5DollarFootballAPI; competition `522514093`
- Provider finished rows: 380
- CBF score rows in source: 290 (rounds 1–29)
- Raw provider rows changed: 0
- Odds API credits / provider calls during report generation: no Odds API calls; one CBF PDF download; one read-only database query

## Result

**290 / 290 reconciled**

| Check | Result |
|---|---:|
| Official CBF score rows parsed | 290/290 |
| Exact PDF score matches | 289 |
| Individual official CBF match-page adjudications | 1 |
| Unresolved score mismatches | 0 |
| Missing provider fixture pairings | 0 |
| Multiple provider pairing candidates | 0 |
| Unmapped CBF team labels | 0 |
| Unused score adjudications | 0 |

The source is the official CBF 2026 Série B basic schedule PDF, emitted 6 February and updated 23 September 2026. Its score column carries results for rounds 1–29; rounds 30–38 are unscored in this document and are deliberately excluded from this verification.

- [Official CBF PDF](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf)
- PDF SHA-256: `ab3b8ccc4254648f2d573bee021b08e5761f6cedbd7ddd0eaa3b16de1495b629`

## Official-source conflict: CBF ref 245

The PDF score column lists Fortaleza 1–0 Operário. The individual CBF match page for match 245, Round 25, 31 August 2026, records **Fortaleza 1–1 Operário**. The official CBF Round 25 news article independently reports the same 1–1 result. The provider also records 1–1.

- [Individual official CBF match page](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-operario/833126)
- [Official CBF Round 25 article](https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro/campeonato-brasileiro-serie-b/juventude-tenta-disparar-na-lideranca-da-serie-b)

The individual match page controls. The source conflict is recorded in `backend/data/research/official_score_adjudications.json`. This is a research-only adjudication: the PDF and provider raw records are preserved unchanged.

## Full-corpus score verification status

- Rounds 1–29: 290/290 scorelines reconciled against the official CBF score table, with one individual match-page adjudication.
- Rounds 31–38: 8 changed/discrepant scorelines were independently checked against official CBF match pages in the existing rounds 31–38 ledger.
- Unique total verified: **298/380**.
- Remaining scorelines requiring official CBF evidence: **82/380** (round 30: 10; rounds 31–38: 72).

The seven score checks previously recorded in the rounds 25–30 ledger overlap with the 290 rows in this PDF and are not double-counted.

## Boundaries

1. This verifies scores, not historical source availability or PIT certification.
2. Team IDs are joined using the existing candidate provider-local mapping; this does not approve canonical team identity merges.
3. The CBF PDF score table is not described as 290 individual match pages; one PDF discrepancy was separately resolved using the individual match page and official CBF article.
4. No raw provider source row or database row was modified.
5. Production model promotion and value-betting activation remain blocked pending the separate prospective validation gates.
