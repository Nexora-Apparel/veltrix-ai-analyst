# Stage 3 model-core and data-blocker disposition — 2026-11-17

## Status

Stage 3 now contains deterministic Elo, Poisson scoreline, Dixon–Coles low-score correction, chronological walk-forward folds, and multiclass Brier/log-loss utilities. These are tested statistical components, not a trained or accuracy-certified prediction model.

No production identity mapping, canonical fixture, source observation, source sighting, or review case was modified during this work.

## Production review register — independently queried

The effective production review register contains exactly 28 cases. All 28 have effective status HUMAN_REVIEW_REQUIRED; all 28 latest review events are AUTOMATED_RECOMMENDATION; there are zero human review events.

| Case category | Count | Current disposition |
|---|---:|---|
| Team real-world identity candidates | 20 | Keep mappings REVIEW_REQUIRED |
| Fixture duplicate candidates | 4 | Preserve both source records; keep UNKNOWN rows out of training |
| America MG alias candidate | 1 | Do not merge provider IDs without human confirmation |
| Competition identity/season | 1 | Keep competition mapping REVIEW_REQUIRED |
| Season coverage reconciliation | 1 | Full fixture-by-fixture reconciliation still required |
| PIT timestamp gap | 1 | All affected observations remain ineligible |
| **Total** | **28** | **No automated approval** |

### Team identity candidates

The 20 provider IDs under review are:

- 1102583842 — America MG
- 3007875643 — Athletic Club MG
- 1684426968 — Atletico GO
- 1446563615 — Avai
- 3250670103 — Botafogo SP
- 2651466053 — CRB
- 1657329649 — Ceara
- 3324195045 — Criciuma
- 4227927162 — Cuiaba
- 744720326 — Fortaleza
- 3126624865 — Goias
- 2672186301 — Juventude
- 3219034225 — Londrina
- 4267737771 — Nautico
- 1620921678 — Novorizontino
- 2016651568 — Operario PR
- 1548718709 — Ponte Preta
- 844813267 — Sao Bernardo
- 559667509 — Sport Recife
- 2434042650 — Vila Nova

All 20 associated identity links remain REVIEW_REQUIRED. Their names and fixture graph are plausible matches to the official Série B club list, but a matching display name and appearance count are not a substitute for evidence-backed identity approval. The CBF's 17 November table reports the official 20-club competition and completed 38-match season; this is corroborative context, not a complete provider-row identity adjudication.

### Four duplicate candidates

| Primary FINISHED provider fixture | Related UNKNOWN provider fixture | Match |
|---|---|---|
| 3116209225 | 2341822348 | Goiás 3–1 América MG |
| 1587564237 | 2336910968 | Fortaleza 3–0 Londrina |
| 236839304 | 933498248 | Fortaleza 1–0 Botafogo SP |
| 553958702 | 1988139832 | Ceará 2–1 Londrina |

The four secondary rows have status UNKNOWN and no settled score. They are not permitted into model training or validation. They remain preserved in source history until the duplicate case is human-confirmed and the audited effective-deduplication mechanism is used. No source row is deleted or rewritten.

### America MG alias

The alias case concerns provider IDs 1102583842 (America MG) and 3808811746 (América Mineiro). The latter appears in the duplicate UNKNOWN Goiás fixture. CBF evidence indicates one official Goiás 3–1 América MG Round 1 match. This is strong alias evidence, but the canonical alias decision remains human-pending.

### Competition and coverage

- Provider competition ID 522514093 is labelled Brazil Serie B. The canonical competition mapping remains REVIEW_REQUIRED; the season scope must be explicitly confirmed.
- The 370 FINISHED rows in the original run-3 interval have strong structural round-robin consistency. That is not a complete match-by-match reconciliation of all 370 provider fixtures to official CBF records.
- The CBF PDF captured on 23 September is explicitly a Tabela Básica, and CBF states that the basic table is not the definitive schedule for dates/times/venues; the detailed table is the official programming record. Do not certify complete match-level reconciliation from the basic table alone.

## PIT source evidence — blocker confirmed

A fresh production query on 2026-11-17 returned:

| Metric | Current production value |
|---|---:|
| Provider fixtures | 384 |
| FINISHED | 380 |
| UNKNOWN | 4 |
| Fixture source observations | 384 |
| Fixture source sightings | 384 |
| Sightings with source_published_at | 0 |
| Sightings with available_at | 0 |
| PIT-certifiable sightings | 0 |
| Human review events | 0 |

All 384 fixture observations use RETRIEVED_AT_ONLY; source publication/availability fields are null. Captured 5DollarFootballAPI response headers contain the HTTP Date and rate-limit headers, but no verified Last-Modified or publication time. Captured fixture payload objects expose event/kickoff, status, teams, goals, cards and corners fields, but no source publication timestamp.

Retrieval time is not source publication time. Kickoff is event time, not publication time. The missing historical PIT metadata cannot be reconstructed by estimation or backfilled from either value.

## Safeguards implemented in code

- Feature admission requires exact observation/sighting/response lineage, payload hash, verified publication and availability times at or before cutoff, active rights permitting feature engineering and training, verified canonical identity, and non-quarantined source data.
- Walk-forward eligibility requires verified team/fixture identity, verified competition identity, duplicate exclusion, approved rights, PIT eligibility, and feature availability before the prediction cutoff.
- Training labels must have become available by the earliest test cutoff minus embargo.
- Simultaneous-kickoff fixtures remain in one fold group; their results cannot leak into each other's pre-match ratings.
- Explicit exclusion reason codes are returned by the walk-forward fixture contract.

## Release restrictions

- No training on the current 384-fixture set.
- No production prediction endpoint, value-bet activation, or Android/backend prediction integration.
- Elo defaults (1500 initial rating, K=20, 55-point home advantage) are provisional engineering defaults, not tuned or accuracy-certified parameters.
- Poisson/Dixon–Coles output is a statistical scoreline engine; goal-rate estimation and rho calibration still require eligible training data and chronological out-of-fold validation.
- Synthetic CI tests verify implementation invariants only. They are not predictive-accuracy evidence.

## Evidence references

- CBF current Série B 2026 first-phase table and official club standings: https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026/2009
- CBF detailed table documents index (16 November 2026): https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?doc=Tabela+Detalhada
- CBF 23 September basic table PDF: https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf
- CBF 7 October detailed schedule notice for rounds 35–38: https://www.cbf.com.br/futebol-brasileiro/noticias/campeonato-brasileiro-serie-b/a/cbf-divulga-tabela-detalhadaa-da-reta-final-da-serie-b
