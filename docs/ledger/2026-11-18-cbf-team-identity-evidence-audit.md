# CBF Série B 2026 provider-team identity evidence audit (2026-11-18)

## Scope

Read-only audit of the 5DollarFootballAPI provider-team identity candidates for competition `522514093`. This is an evidence pack for human review, not an identity approval or merge.

## Independent schedule evidence

- All 380 FINISHED provider fixtures are reconciled to CBF match references 1–380.
- Ordered home/away pairings: 380/380.
- Final local kickoff times: 380/380 after the 42 documented official CBF schedule changes and two research-only timestamp adjudications.
- Scorelines: 380/380 verified against official CBF score tables, result articles or individual match pages.
- Raw provider fixture and source-observation rows changed: 0.

See the [consolidated qualification ledger](2026-11-18-cbf-consolidated-data-qualification.md) and the round-specific fixture/score ledgers.

## Provider-local team coverage

Each of the 20 active provider-team IDs appears in exactly 38 FINISHED fixtures: 19 home and 19 away. Their ordered fixture pairings reconcile to the CBF schedule. This provides strong season-level evidence for the mapping candidates below, but the canonical mappings remain `REVIEW_REQUIRED` until a human reviewer records the decision.

| Provider team ID | Immutable provider label | CBF 2026 club label |
|---:|---|---|
| `1102583842` | America MG | América-MG |
| `1446563615` | Avai / Avaí | Avaí |
| `1548718709` | Ponte Preta | Ponte Preta |
| `1620921678` | Novorizontino | Grêmio Novorizontino |
| `1657329649` | Ceara / Ceará | Ceará |
| `1684426968` | Atletico GO / Atlético GO | Atlético-GO |
| `2016651568` | Operario PR / Operário PR | Operário-PR |
| `2434042650` | Vila Nova | Vila Nova |
| `2651466053` | CRB | CRB |
| `2672186301` | Juventude | Juventude |
| `3007875643` | Athletic Club MG | Athletic-MG |
| `3126624865` | Goias / Goiás | Goiás |
| `3219034225` | Londrina | Londrina |
| `3250670103` | Botafogo SP | Botafogo-SP |
| `3324195045` | Criciuma / Criciúma | Criciúma |
| `4227927162` | Cuiaba / Cuiabá EC | Cuiabá |
| `4267737771` | Nautico / Náutico | Náutico |
| `559667509` | Sport Recife | Sport |
| `744720326` | Fortaleza | Fortaleza |
| `844813267` | Sao Bernardo / São Bernardo | São Bernardo |

Provider spelling/diacritic variants above remain the same provider ID; this audit does not rewrite provider labels.

## Separate América Mineiro identity conflict

Provider ID `3808811746`, labelled `América Mineiro`, appears only in one UNKNOWN duplicate candidate and has zero FINISHED appearances. Provider ID `1102583842`, labelled `America MG`, has 38 FINISHED appearances (19 home, 19 away). The [official CBF Round 1 Goiás 3–1 América-MG match page](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843) records one real match, while the provider catalogue has one FINISHED row and one UNKNOWN row 85 seconds apart.

**Recommendation for human review:** treat `3808811746` as a probable duplicate/alias identity candidate, not a second active club. Preserve both source IDs and all raw rows; do not merge until signed off.

## Four UNKNOWN fixture duplicates

All four duplicate candidates pair a FINISHED fixture with an UNKNOWN source row. They remain excluded from model training and require human confirmation before any duplicate-source exclusion is applied:

| Case | FINISHED fixture ID | UNKNOWN fixture ID | FINISHED score |
|---|---:|---:|---:|
| Goiás x América-MG | `3116209225` | `2341822348` | 3–1 |
| Fortaleza x Londrina | `1587564237` | `2336910968` | 3–0 |
| Fortaleza x Botafogo-SP | `236839304` | `933498248` | 1–0 |
| Ceará x Londrina | `553958702` | `1988139832` | 2–1 |

## Review boundary

- 20 active team identity candidates have complete CBF schedule-pairing evidence.
- 1 separate América Mineiro provider-ID alias/duplicate candidate remains unresolved.
- 4 duplicate-fixture candidates remain human-review-required.
- 1 competition identity candidate remains human-review-required.
- No team alias, canonical merge, fixture deduplication, source-row mutation or PIT certification is performed by this audit.
