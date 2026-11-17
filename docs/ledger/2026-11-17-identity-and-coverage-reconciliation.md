# 2026-11-17 — Evidence-backed identity and coverage reconciliation

## Production database scope

Dedicated Neon project `young-wind-27772160`, database `veltrix_ai_analyst`; provider 5DollarFootballAPI, source `5dollarfootballapi`, competition `522514093`, historical import run 3.

All queries in this audit were read-only. No source row, canonical row, identity link, score, status or PIT flag was modified.

## Canonical materialization verification

Guarded workflow [#44086857898](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086857898), job [#134051435015](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086857898/job/134051435015), reported `MATERIALIZATION_COMMITTED`.

Independent Neon counts:
- canonical teams 21
- canonical competitions 1
- canonical fixtures 374
- provider team identity links 21
- provider competition identity links 1
- canonical fixture-source links 374
- canonical identity review events 0
- pre-match feature observations 0

Independent status grouping:
- 21 team links: `REVIEW_REQUIRED`
- one competition link: `REVIEW_REQUIRED`
- 374 fixture-source links: `REVIEW_REQUIRED`
- 374 canonical fixtures: `SOURCE_ROW_ONLY`
- 2 canonical fixture identities: `CONFLICT`
- 372 canonical fixture identities: `IDENTITY_REVIEW_REQUIRED`
- 370 provider fixtures: `FINISHED`
- 4 provider fixtures: `UNKNOWN`

Source PIT audit:
- 374 fixture/result source observations.
- 374 linked sightings.
- zero observations with `point_in_time_certifiable=true`.
- zero sightings with `point_in_time_certifiable=true`.
- No `source_published_at` or `available_at` evidence for this fixture set.

## America MG / América Mineiro collision

Provider team identity usage:
- ID `1102583842`, label `America MG`: 37 fixture appearances, 18 home and 19 away.
- ID `3808811746`, label `América Mineiro`: one fixture appearance, away side of the duplicate UNKNOWN Goiás row.

Canonical team links:
- ID `1102583842` → link 1, canonical placeholder `08d164b5-b56e-42dc-8246-315a0cfce0d8`.
- ID `3808811746` → link 16, canonical placeholder `ae7e562a-99e3-48ba-be39-25843e74fa05`.

The provider fixtures:
- `3116209225`, row 4, 2026-03-22 20:58:35Z, Goiás 3–1 America MG, FINISHED.
- `2341822348`, row 2, 2026-03-22 21:00:00Z, Goiás vs América Mineiro, UNKNOWN, `kickoff_unconfirmed`.

Official CBF match [832843](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843) records one Round 1 Goiás 3–1 América MG match on 2026-03-22 at 18:00 local time at Hailé Pinheiro. The official CBF schedule also lists one Goiás 3–1 América MG fixture. This supports a single official fixture and a strong alias/duplicate hypothesis. It does not justify changing immutable provider IDs or merging canonical team placeholders without human confirmation.

## All four UNKNOWN rows matched to existing FINISHED fixtures

| UNKNOWN provider ID | UNKNOWN row | FINISHED provider ID | FINISHED row | Official CBF match |
|---|---:|---|---:|---|
| 2341822348 | 2 | 3116209225 | 4 | Goiás 3–1 América MG, Round 1, [832843](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843) |
| 2336910968 | 227 | 1587564237 | 94 | Fortaleza 3–0 Londrina, Round 10, [832976](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-londrina-saf/832976) |
| 933498248 | 223 | 236839304 | 201 | Fortaleza 1–0 Botafogo SP, Round 20, [833076](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-botafogo/833076) |
| 1988139832 | 217 | 553958702 | 235 | Ceará 2–1 Londrina, Round 24, [833116](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ceara-x-londrina-saf/833116) |

Exact DB comparison:
- Three UNKNOWN rows have the same exact ordered home/away provider team IDs as the corresponding FINISHED row. The Goiás-América row has a different away provider team ID; CBF official evidence and the source appearance counts support an alias candidate.
- Each UNKNOWN row has a different provider fixture ID and an incompatible/stale kickoff timestamp.
- The corresponding CBF official match record provides one actual match and a settled result for each pairing.
- Therefore the four UNKNOWN rows are strong duplicate/stale source-record candidates. Recommended action: exclude each duplicate source row after explicit human confirmation; keep the original provider rows and canonical source links intact.

## Season schedule coverage

The run-3 collection window is `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`.

The official CBF basic 2026 schedule lists Round 37 on 6–8 November and Round 38 on 14 November; the detailed CBF record dates Botafogo SP–Londrina to 5 November. The run-3 dataset contains 370 FINISHED rows. A separate aggregate query confirms 20 distinct team IDs, exactly 37 appearances per team, 370 distinct ordered home/away pairs and zero repeated ordered pairs. All 10 Round 37 pairings match the official CBF schedule. The four UNKNOWN rows are duplicate candidates, not additional unique fixtures.

Coverage conclusion:
- The imported interval is consistent with rounds 1–37.
- The 370-match / 20-team / 37-appearance structure and complete Round 37 pairing match are strong coverage evidence.
- Count equality and the structural audit are not proof that all 370 exact pairings match the official schedule.
- A fixture-by-fixture comparison of all 370 FINISHED rows against the CBF round 1–37 schedule is still required.
- The 10 Round 38 fixtures (14 November) are outside run 3's scope and are not present in this import.
- Do not call the 2026 season complete based on run 3.

Official schedule references:
- [CBF 2026 Série B detailed schedule page](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026?doc=Tabela+Detalhada)
- [CBF official 2026 fixture table PDF](https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Brasileiro_Serie_B_2026_23_09_378b396600.pdf)
- [CBF 2026 competition page with final Round 38 standings/fixtures](https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026/2009)

## Migration 009 review-queue implementation

Branch: `identity-review-coverage-reconciliation-20261117`.

Prepared `009_canonical_identity_review_cases.sql` to add:
- immutable `canonical_identity_review_cases`;
- immutable `canonical_identity_review_case_events`;
- strict separation between `AUTOMATED_SYSTEM` recommendations and `HUMAN` confirmations/rejections;
- effective review-case status view;
- source-local team and competition provenance audit views;
- canonical fixture source provenance audit view;
- four official CBF-backed duplicate fixture cases;
- one America MG / América Mineiro team-alias case;
- 20 real-world team identity candidate cases;
- one competition/season identity case;
- one official schedule coverage case;
- one PIT timestamp gap case.

Expected seed count in production: 28 cases (20 team identity + 1 team alias + 1 competition identity + 4 fixture duplicate + 1 coverage + 1 PIT). Automated recommendations are not final decisions. Every case remains human-review-required. The migration does not modify provider rows, canonical rows, canonical links or PIT flags.

Added CI coverage for the migration, append-only case/event behavior, seeded base cases, audit views, and checksum verification through the existing manual migration workflow.

## Remaining gates

1. Run PR CI and review migration 009.
2. Merge only after all CI checks pass.
3. Manually dispatch the existing checksum-verified migration workflow; no production migration was run during this audit.
4. Independently verify 28 seeded cases and the source provenance audit view counts.
5. Have a human reviewer confirm or reject alias and duplicate cases; only then record corresponding canonical identity review events.
6. Reconcile all 370 FINISHED rows to official CBF rounds 1–37; obtain a separate bounded, rights-approved import for the final 10 Round 38 fixtures if the season-complete dataset is required.
7. Keep all 374 observations excluded from pre-match features until valid publication/availability timestamps and rights approval for FEATURE_ENGINEERING and MODEL_TRAINING are available.

No model training, calibration, prediction publication, or Android prediction API integration is authorized by this stage.
