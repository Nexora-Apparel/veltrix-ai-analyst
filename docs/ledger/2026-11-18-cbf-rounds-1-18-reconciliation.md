# CBF Série B 2026 rounds 1–18 reconciliation — 2026-11-18

## Scope and execution

- Workflow: [run 44281831825](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44281831825)
- Commit: `a3d931186f4b88dc930c8c3cc171754c786fb037`
- Evidence artifact SHA-256: `397bd5ead54fae7dd441bb2c2ece4cd4db25beb3a53e833909a83416af508037`
- Database: `veltrix_ai_analyst`; read-only transaction
- Provider: 5DollarFootballAPI; competition `522514093`
- Scope: rounds 1–18, 180 CBF references
- Provider finished rows available: 380
- Raw provider fixture/source-observation rows changed: 0
- Provider calls, Neon writes, bookmaker odds and Odds API credits: 0

## Result

| Check | Result |
|---|---:|
| Official CBF schedule rows parsed | 180/180 |
| Ordered home/away provider pairings found | 180/180 |
| Missing pairings | 0 |
| Multiple provider pairing candidates | 0 |
| Unmapped team labels | 0 |
| Rows matching original detailed schedule | 153 |
| Official CBF schedule changes confirmed | 26 |
| Provider kickoff matches final CBF time for those changes | 26/26 |
| Unadjudicated initial-schedule differences | 0 |
| Scorelines reconciled against the later official CBF score table (rounds 1–29) | 180/180 |

The 26 apparent kickoff discrepancies against the initial PDFs were all explained by official CBF schedule changes. A later official CBF score-table audit, updated 23 September 2026, independently reconciles all 180 scores in rounds 1–18; see [score verification rounds 1–29](2026-11-18-cbf-score-verification-rounds-1-29.md). The provider timestamps match the final CBF match-page kickoff times for all 26.

One additional precision issue was found on CBF ref 6 (Goiás x América): the provider timestamp was 17:58:35 BRT while the official CBF kickoff is 18:00 BRT. It is not an official reschedule. The research-only chronology registry now normalizes this fixture to 18:00 so it remains in the same simultaneous-kickoff batch. The raw provider row remains unchanged. See the [corrected retrospective report](../research/2026-11-18-corrected-retrospective-report.md).

## Confirmed CBF schedule changes

| CBF ref | Fixture | Final CBF kickoff (BRT) | Provider fixture ID | Official CBF match record |
|---:|---|---|---:|---|
| 5 | Ceará x São Bernardo | 21 Mar, 18:00 | 872274192 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ceara-x-sao-bernardo/832842?view=alteracoes) |
| 12 | São Bernardo x Operário | 2 Apr, 19:00 | 836163555 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sao-bernardo-x-operario/832849) |
| 13 | América x Botafogo | 1 Apr, 18:00 | 4245938013 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/america-x-botafogo/832850?view=alteracoes) |
| 20 | Juventude x Novorizontino | 31 Mar, 18:30 | 742396597 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/juventude-x-gremio-novorizontino-saf/832857) |
| 32 | São Bernardo x Fortaleza | 12 Apr, 18:00 | 2270078788 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sao-bernardo-saf-x-fortaleza-saf/832869) |
| 38 | Sport x Avaí | 11 Apr, 18:00 | 4000193841 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sport-recife-x-avai/832875?view=alteracoes) |
| 40 | Juventude x Goiás | 11 Apr, 16:00 | 2721352815 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/juventude-x-goias/832877) |
| 41 | Botafogo x Atlético-GO | 19 Apr, 16:00 | 928428137 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/botafogo-x-atletico-goianiense-saf/832922?view=alteracoes) |
| 43 | América x Sport | 18 Apr, 18:00 | 530964533 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/america-x-sport-recife/832924) |
| 47 | Avaí x Ponte Preta | 18 Apr, 20:30 | 2108743048 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/avai-x-ponte-preta/832928?view=alteracoes) |
| 53 | Athletic x Náutico | 27 Apr, 19:00 | 3677569838 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/athletic-club-x-nautico/832934) |
| 72 | Novorizontino x Botafogo | 10 May, 19:30 | 606478042 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/gremio-novorizontino-saf-x-botafogo/832953) |
| 74 | Londrina x São Bernardo | 12 May, 19:30 | 1764547645 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/londrina-saf-x-sao-bernardo-saf/832955?view=alteracoes) |
| 78 | Náutico x América | 10 May, 16:00 | 1112544622 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/nautico-x-america/832959) |
| 85 | Ceará x Fortaleza | 17 May, 18:30 | 4121407452 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ceara-x-fortaleza-saf/832966?view=alteracoes) |
| 97 | Avaí x Goiás | 24 May, 19:00 | 1322401215 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/avai-x-goias/832978?view=alteracoes) |
| 102 | São Bernardo x Novorizontino | 31 May, 11:00 | 2465307274 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sao-bernardo-x-gremio-novorizontino-saf/832983) |
| 106 | Atlético-GO x Goiás | 30 May, 16:00 | 1469284464 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/atletico-goianiense-saf-x-goias/832987?view=alteracoes) |
| 129 | Cuiabá x Vila Nova | 14 Jun, 17:00 | 4187408541 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/cuiaba-x-vila-nova/833010?view=alteracoes) |
| 132 | São Bernardo x Juventude | 21 Jun, 17:00 | 3263312026 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/sao-bernardo-x-juventude/833013?view=alteracoes) |
| 136 | Goiás x Operário | 21 Jun, 18:30 | 1158823829 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-operario/833017?view=alteracoes) |
| 150 | Juventude x Ceará | 28 Jun, 16:00 | 3429311466 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/juventude-x-ceara/833031?view=alteracoes) |
| 158 | Náutico x Juventude | 5 Jul, 20:30 | 114136660 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/nautico-x-juventude/833039?view=alteracoes) |
| 174 | Londrina x Botafogo | 17 Jul, 21:00 | 4289733035 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/londrina-saf-x-botafogo/833055) |
| 176 | Atlético-GO x Athletic | 18 Jul, 18:00 | 1669151354 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/atletico-goianiense-saf-x-athletic-saf/833057) |
| 177 | Criciúma x Vila Nova | 18 Jul, 16:00 | 1350259540 | [CBF](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/criciuma-x-vila-nova/833058?view=alteracoes) |

The official CBF IMT register is also available at: https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?documento=IMT

## Source schedule documents

| Rounds | Published | Rows | Extraction |
|---|---|---:|---|
| 1–5 | 7 Mar 2026 | 50 | Manual transcription from the image-only official PDF |
| 6–11 | 8 Apr 2026 | 60 | PDF text-table extraction |
| 12–18 | 28 May 2026 | 70 | PDF text-table extraction |

- [CBF detailed schedule, rounds 1–5](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileirao_Serie_B_2026_Rodadas_1_a_5_8495da2f30.pdf)
- [CBF detailed schedule, rounds 6–11](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_6_a_11_rodada_Brasileiro_Serie_B_d95c40657d.pdf)
- [CBF detailed schedule, rounds 12–18](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_12_a_18_rodada_Brasileiro_Serie_B_2026_ea9e84afde.pdf)

## Boundaries and next checks

1. This pass certifies fixture pairing and kickoff schedule reconciliation only. It does not independently verify all 180 scorelines against CBF match records.
2. Team matching uses the existing candidate provider-local ID map. It does not approve canonical team identities or merges.
3. The 4 UNKNOWN rows and duplicate candidates remain preserved and excluded from labeled training; their identity decisions remain in the human-review queue.
4. This schedule audit does not supply historical source publication or availability timestamps and does not change PIT certification status.
5. Rounds 19–24 and 25–30/31–38 require the same final-schedule confirmation treatment before the full 380-fixture chronology is declared closed.
