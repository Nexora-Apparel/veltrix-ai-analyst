# 2026-11-18 — Live Neon historical corpus qualification audit

## Scope and method

Read-only audit of the existing Neon project `veltrix-ai-analyst-db`, default branch, database `veltrix_ai_analyst`. Queries inspected the 5DollarFootballAPI Brazil Serie B corpus, source observations and sightings, canonical identity links, canonical fixtures, fixture source links, and outstanding review cases.

No INSERT, UPDATE, DELETE, DDL, migration, provider request, odds-credit use, or production configuration change was performed. This document records observed database state; it does not certify source facts beyond the evidence described.

## Corpus inventory

For provider `5DollarFootballAPI`, source `5dollarfootballapi`, competition `522514093`:

| Measure | Observed |
|---|---:|
| Provider fixture rows | 384 |
| FINISHED with scores | 380 |
| UNKNOWN without scores | 4 |
| Fixture/result source observations | 384 |
| Fixture/result observation sightings | 384 |
| Canonical fixtures | 384 |
| Canonical fixture source links | 384 |
| Provider team IDs | 21 |
| Provider team identity links | 21 |
| Provider competition identity links | 1 |

The separate source-observation inventory also contains 37 competition-catalogue observations and 30 team-catalogue observations for this provider/source.

## Point-in-time provenance

All 384 fixture/result source observations and all 384 corresponding sightings have:

- `source_published_at IS NULL`
- `available_at IS NULL`
- `point_in_time_certifiable = false`
- `availability_basis = RETRIEVED_AT_ONLY`

This is a hard exclusion from historical pre-match feature replay and PIT certification. Retrieval time proves only when this system retrieved the observation. Kickoff is event time, not publication/availability time. Neither can be substituted for source publication or original availability.

The existing PIT timestamp review case remains open. Do not infer missing timestamps from kickoff, current API state, provider HTTP Date, or a later snapshot.

## Identity and canonicalization

The database audit views distinguish source provenance from real-world identity:

- All 384 fixture source links report `PROVENANCE_VERIFIED`, but all 384 remain `SOURCE_FIXTURE_REVIEW_REQUIRED`.
- All 21 provider team links report `PROVENANCE_VERIFIED`, but all 21 remain `REAL_WORLD_IDENTITY_REVIEW_REQUIRED`.
- The one provider competition link reports `PROVENANCE_VERIFIED`, but remains `REAL_WORLD_IDENTITY_REVIEW_REQUIRED`.
- Canonical fixtures: 382 `IDENTITY_REVIEW_REQUIRED / SOURCE_ROW_ONLY`; 2 `CONFLICT / SOURCE_ROW_ONLY`.
- No human identity/fixture review event was recorded in the inspected review cases.

Therefore, provenance integrity is not equivalent to real-world identity verification or fixture reconciliation. Do not merge team aliases or mark fixtures verified based solely on provider labels.

## Outstanding review cases

The review-case inventory contains:

| Case type | Count |
|---|---:|
| TEAM_REAL_WORLD_IDENTITY_CANDIDATE | 20 |
| TEAM_ALIAS_CANDIDATE | 1 |
| COMPETITION_REAL_WORLD_IDENTITY_CANDIDATE | 1 |
| FIXTURE_DUPLICATE_CANDIDATE | 4 |
| SEASON_COVERAGE_RECONCILIATION | 1 |
| PIT_TIMESTAMP_GAP | 1 |

### Team alias candidate

Provider team IDs `1102583842` (`America MG`) and `3808811746` (`América Mineiro`) are separate source identities. The audit evidence says the first appears across 37 fixtures while the second appears only in the duplicate UNKNOWN Goiás row. CBF evidence identifies one Round 1 Goiás 3–1 América MG fixture. The proposed alias mapping and duplicate exclusion remain subject to human confirmation; preserve both immutable provider identities until then.

### Duplicate fixture candidates

1. Goiás–América MG: FINISHED fixture `3116209225` (3–1, 2026-03-22 20:58:35Z) and UNKNOWN fixture `2341822348` (same teams, 2026-03-22 21:00:00Z).
2. Fortaleza–Londrina: FINISHED fixture `1587564237` (3–0, 2026-05-23 21:30:00Z) and UNKNOWN fixture `2336910968` (same teams, 2026-08-18 15:28:11Z).
3. Fortaleza–Botafogo SP: FINISHED fixture `236839304` (1–0, 2026-07-29 00:35:00Z) and UNKNOWN fixture `933498248` (same teams, 2026-08-19 12:34:27Z).
4. Ceará–Londrina: FINISHED fixture `553958702` (2–1, 2026-08-22 21:00:00Z) and UNKNOWN fixture `1988139832` (same teams, 2026-08-20 09:49:29Z).

These are strong duplicate/stale-row candidates, not automatic deletion instructions. Keep all original provider rows and their provenance. A reviewer must confirm the official match mapping before any canonical deduplication.

### Competition and season coverage

The provider competition ID `522514093` is labelled Brazil Serie B. The existing evidence includes the official CBF 2026 Serie B schedule. Structural checks recorded in the open season-coverage case show 370 FINISHED rows, 20 provider team IDs with 37 appearances each, 370 distinct ordered home/away pairs, and all 10 Round 37 pairings matching the official schedule. This is strong structural evidence, but it is not a complete fixture-by-fixture reconciliation of all 370 FINISHED rows to CBF rounds 1–37. Competition identity and season scope still require human review.

## Model-use disposition

- The 380 FINISHED rows can remain a retrospective, provider-local research corpus, with the four UNKNOWN rows excluded as labels.
- Keep team IDs in their provider-local namespace; do not merge the America MG alias before confirmation.
- Any retrospective result must remain explicitly labelled `RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED`.
- Do not use the corpus as evidence of original-time feature availability, production predictive accuracy, or PIT-certified walk-forward performance.
- Do not enable production prediction publication or Android integration from this audit.
- Bookmaker odds remain excluded from core model inputs. The secondary value-betting system remains locked pending its separate certification.

## Next work sequence

1. Obtain and record human decisions for the 20 team identities, one alias case, one competition identity, and four duplicate cases, preserving evidence URI and checksum for every decision.
2. Complete the full 370-row official CBF schedule/result reconciliation; record each provider fixture ID against the official round/match record and preserve unresolved rows.
3. Keep the PIT timestamp gap open unless authoritative source-publication/availability evidence is found for each observation. Do not backfill.
4. Only after identity and coverage review, run a separate retrospective research evaluation using provider-local IDs and a clear non-PIT label.
5. Continue prospective collection only with complete private artifacts retaining exact raw response bytes; the previous manifest-only odds artifact remains metadata-only.

## Execution references

- Neon project: `veltrix-ai-analyst-db`
- Database: `veltrix_ai_analyst`
- Branch: default `main`
- Read-only audit date: 2026-11-18
- No database writes or provider/API calls were made for this audit.
