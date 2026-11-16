# 2026-11-16 — 5Dollar Brazil Serie B fixture coverage and integrity audit

## Scope and method

Read-only SQL audit of the dedicated `veltrix_ai_analyst` database, import run 3, provider `5DollarFootballAPI`, source `5dollarfootballapi`, competition ID `522514093`. No provider calls, data updates, inserts, deletions, or migrations were performed during the audit.

Import scope: `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`; 34 contiguous half-open date windows.

## Coverage

- Import run status: `COMPLETED`.
- Competition identity: provider competition `522514093`, display name `Brazil Serie B`.
- Imported fixtures: **374**; provider fixture IDs: **374 distinct**; internal fixture rows: **374 distinct**.
- First/last observed kickoff: `2026-03-21T20:00:00Z` to `2026-11-08T22:15:00Z`.
- All **34/34** checkpoints are `COMPLETED`; every window contains at least one fixture; per-window checkpoint inserted counts equal database fixture counts.
- Each window used one request; total 34/40 budgeted requests.
- Observed window fixture counts in chronological order: **11, 10, 11, 9, 12, 8, 10, 10, 11, 9, 11, 10, 10, 11, 10, 11, 11, 16, 10, 2, 11, 20, 13, 10, 17, 12, 10, 13, 15, 12, 9, 10, 11, 8**.
- The 2-fixture window is 2026-08-01 through 2026-08-08 UTC; the highest is 20 fixtures for 2026-08-15 through 2026-08-22 UTC. These are observed counts, not proof of missing data or completeness.
- The provider competition catalogue row has no country code/name, no season metadata and no last-fixture timestamp. The import scope is known from the configured competition ID and approval, but the catalogue row itself cannot independently certify the 2026 season or national competition context.
- **Coverage conclusion:** all planned windows are accounted for and internally reconcile. Completeness against the actual league schedule is **not established**: the API returned one page per window, and there is no independent authoritative season fixture manifest in this database to prove that all fixtures were returned.

## Team identity

- **21 provider team IDs** and 21 distinct trimmed/case-folded provider-team names are present. Names are non-empty; every fixture's home/away team foreign keys resolve; no fixture uses the same provider team ID on both sides.
- Fixture display names differ from the provider-team projection in **6 home-side** and **3 away-side** comparisons. The inspected differences are diacritic/transliteration variants (for example, `Ceará` vs `Ceara`, `Goiás` vs `Goias`, `Náutico` vs `Nautico`, `Criciúma` vs `Criciuma`). Treat these as presentation-string variance, not proof of different clubs. Preserve both exact strings and provider IDs.
- **Unresolved identity warning:** two distinct provider IDs are represented as `America MG` (`1102583842`) and `América Mineiro` (`3808811746`). Both occur against Goiás on 2026-03-22 within approximately 85 seconds; one record is `FINISHED 3–1`, the other `UNKNOWN`. This is a strong duplicate/alias candidate, but not sufficient evidence to merge IDs or discard either record. Keep both provider records immutable and flag this pair for manual entity/fixture resolution.
- The 21st team entity is therefore not accepted as a clean 21-club competition roster. No team aliases or canonical team mappings have been created.

## Score and status completeness

| Provider status | Fixtures | Final scores present |
|---|---:|---:|
| `FINISHED` | 370 | 370 |
| `UNKNOWN` | 4 | 0 |
| **Total** | **374** | **370** |

- 100% of `FINISHED` rows have both goals; 0 finished rows have missing scores.
- All 4 `UNKNOWN` rows have no final score; no non-finished row carries a final score.
- Three additional `UNKNOWN` rows have provider status codes/reasons `37/result_unconfirmed`, `half/result_unconfirmed`, and `kickoff_unconfirmed`. They must not be treated as settled outcomes.
- No score/status contradiction was found. The DB constraints enforce the finished-score invariant.
- Optional corners/cards are not used to determine final-score completeness and need a separate field-level missingness audit before those features are considered.

## Duplicate and collision risks

- Exact provider fixture ID uniqueness: **374/374**.
- Exact duplicate key scan on competition + kickoff + unordered provider team IDs: **0 groups / 0 extra rows**.
- Near-time duplicate scan using identical raw home/away display names within two hours: **0 candidates**.
- The `America MG` / `América Mineiro` ID pair described above evades those exact-key checks because the provider uses two different team IDs and display strings. It remains an unresolved likely alias/duplicate collision. Cross-source and fuzzy matching must not auto-merge it.
- No fixture rows were deleted, rewritten, or merged.

## Provenance and point-in-time status

A direct join of all 374 fixtures to their source observations found:
- 374/374 have a linked source observation and captured provider response.
- 0/374 have `source_published_at`.
- 0/374 have `available_at`.
- 0/374 have `point_in_time_certifiable = true`.

The 1,031 retrieval sightings for this provider/source all have `availability_basis=RETRIEVED_AT_ONLY`, `point_in_time_certifiable=false`, and no source-published or available timestamp.

The validator's `non_pit_observations=0` counter must not be interpreted as PIT certification; the direct observation/sighting timestamp audit is authoritative for this question. **None of the 374 records can currently enter pre-match feature inputs.** Settled match scores may be separately evaluated as post-match target labels, subject to rights and match-identity checks; that is not feature eligibility.

## Canonical fixture design decision

The provider-local ingestion layer remains immutable in identity terms. Canonical records will be a separate layer, not an overwrite of `provider_fixtures`:

1. `canonical_teams` and `canonical_competitions`: internal stable IDs, normalized display labels, country/competition context, lifecycle state and audit timestamps.
2. `provider_team_identity_links` / `provider_competition_identity_links`: provider + source + provider-local ID to canonical ID; include mapping status, method, evidence URI/hash, reviewer and verification timestamp. Names alone never produce a verified mapping.
3. `canonical_fixtures`: canonical competition/team IDs, season context, UTC kickoff, neutral venue where known, fixture lifecycle and settled score only when source status is verified finished.
4. `canonical_fixture_sources`: link each provider fixture row to a canonical fixture with the original provider fixture row ID, source observation ID, exact provider fixture ID, source approval and mapping evidence. One source row may map to at most one canonical fixture; multiple provider rows may map to one canonical fixture only after explicit review.
5. No canonical fixture is eligible for model use until competition, home team, away team and source fixture links are verified; conflicting kickoff/result evidence creates a quarantine/review case rather than a merge.
6. Keep original provider strings, IDs, response IDs, observation IDs, payload hashes, rights approval IDs and sightings accessible through the source link. Never replace provider IDs with canonical IDs in raw/source tables.

The current 21 provider-team IDs and the Goiás/America MG collision are unresolved inputs; no crosswalk rows are seeded by this audit.

## Point-in-time feature gate implementation

Migration `006_pre_match_feature_pit_gate.sql` adds a dedicated append-only `pre_match_feature_observations` table and a database trigger. A row is accepted only when the selected exact source sighting:
- is explicitly `point_in_time_certifiable=true` and `availability_basis=SOURCE_PUBLISHED_AT`;
- has source publication and availability timestamps, with availability no earlier than publication;
- has a captured successful provider response for the same provider/source;
- has a payload hash matching the referenced immutable source observation;
- was published and available no later than the prediction cutoff;
- has a source approval valid and not revoked at that cutoff.

Retrieval time, kickoff/event time, source update time, and a post-kickoff proxy cannot satisfy this gate. Existing historical rows are not backfilled or upgraded. The 5Dollar records remain excluded.

## Next actions

1. Keep the 4 `UNKNOWN` records and America MG alias pair in a review queue; do not infer results or merge identities.
2. Obtain an authoritative league schedule or an independently approved fixture feed before claiming full season completeness.
3. Implement canonical team/competition mapping review before canonical fixture linking.
4. Apply and test migration 006 through the normal checksum-verified migration path; do not apply it manually to production.
5. Integrate the Python eligibility policy and database trigger into the eventual feature pipeline; no feature pipeline or prediction model is currently implemented.
