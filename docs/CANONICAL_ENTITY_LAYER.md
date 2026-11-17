# Canonical football entity and fixture layer

## Purpose and boundary

The canonical layer is a provenance-preserving identity layer above immutable provider ingestion.
It does not rewrite provider IDs, observations, sightings, response payloads, approvals or fixture rows.
It does not make a record PIT-eligible. The migration 006 feature gate remains a separate prerequisite.

The first materialization scope is the single approved 5DollarFootballAPI Brazil Serie B import
(run 3, competition ID `522514093`). It must not imply full league-schedule completeness.

## Entity model

### `canonical_teams`

Stable internal UUID, canonical display label, country/association context when independently
evidenced, lifecycle state, and created/updated timestamps. A row may initially be a
provider-identity placeholder rather than a confirmed real-world club.

### `canonical_competitions`

Stable internal UUID, canonical label, country/association, competition level, season model,
and lifecycle state. Missing country/season metadata must remain null; do not infer it from a
competition name or fixture dates.

### `canonical_fixtures`

Stable internal UUID, canonical competition/team references, UTC kickoff, venue/neutral-site
facts only when evidenced, fixture state, and settled score only when provider status is
verified FINISHED with both goals. Include an explicit identity/completeness state. A fixture
whose team or competition identity is unresolved remains `IDENTITY_REVIEW_REQUIRED` and is
not eligible for model use.

## Provider identity links

### `provider_team_identity_links`

Unique key: provider + source + provider-local team ID. Store canonical team UUID, exact source
observation ID, source response/sighting references where available, payload hash, mapping
method, mapping status, evidence URI/hash, reviewer ID, reviewed timestamp, and notes.

A source-native provider ID can be linked to a dedicated provider-identity placeholder after
checking the exact provider team row and its immutable source observation. This confirms only
the source-local identity, not the real-world club identity. Cross-provider or real-world
identity equivalence requires independent evidence and explicit human review.

### `provider_competition_identity_links`

Same provenance/review contract as team links. The current provider catalogue row has no country,
season or last-fixture metadata. The initial canonical competition therefore remains a
source-scoped competition placeholder; no country or season should be filled by inference.

### `canonical_fixture_sources`

Link one immutable provider fixture row to one canonical fixture, retaining the provider fixture
row ID, provider fixture ID, exact source observation, source approval, response/sighting
provenance, payload hash and mapping evidence. A source fixture row can link to at most one
canonical fixture. Multiple provider rows may link to one canonical fixture only after explicit
duplicate/identity review with evidence.

## Review states

- `SOURCE_IDENTITY_REVIEWED`: exact provider-local ID and source row have been checked; this is
  not a real-world identity assertion.
- `REAL_WORLD_IDENTITY_VERIFIED`: independent evidence supports the actual club/competition
  identity; reviewer and evidence are mandatory.
- `REVIEW_REQUIRED`: candidate only; no cross-provider mapping or canonical merge.
- `CONFLICT`: evidence conflicts; keep separate source records and block canonical fixture
  verification.
- `REJECTED`: reviewed evidence disproves the proposed mapping; retain the audit record.

No fuzzy matching, accent-stripping auto-merge, same-name inference, or cross-provider auto-link
is permitted. Mapping decisions are append-only review events; corrections supersede rather than
erase earlier decisions.

## Brazil Serie B run 3 disposition

- 374 provider fixture rows are available with exact provider fixture IDs and source links.
- 370 are FINISHED with both goals; four are UNKNOWN and must remain scoreless/unsettled.
- 21 provider team IDs are present. Exact source-native identities can be recorded independently.
- `America MG` (provider ID `1102583842`) and `América Mineiro` (provider ID `3808811746`)
  remain separate. The near-simultaneous Goiás fixture pair is a conflict requiring independent
  evidence; do not merge, discard or normalize one ID into the other.
- Diacritic/transliteration differences such as Ceara/Ceará and Goias/Goiás are preserved as raw
  provider labels. They are not sufficient evidence for a cross-provider canonical merge.
- The provider competition catalogue does not establish country or season metadata. The
  canonical competition remains source-scoped until reviewed evidence is available.
- 0/374 observations are PIT-certifiable. Canonicalization cannot promote any of them into
  pre-match features.

## Schema implementation — Migration 007 applied; Migration 008 pending

Migration `007_canonical_entity_layer.sql` was merged in PR #14 and applied to the dedicated Neon database through the controlled migration workflow. Workflow [#44072112212](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44072112212) verified SHA-256 `5503622ac57bd1875e08cf40cf1d87220cec99deb79e8fc23dd4ec6ebbffc30b`, all seven canonical tables, four functions and ten triggers.

Integration testing then exposed a latent defect in the generic provenance trigger: a fixture-only `NEW.canonical_fixture_id` field reference was evaluated for team-link inserts. Migration 008 replaces that function with a branch-scoped fixture check, enforces exact source-observation data types (`team_catalogue`, `competition_catalogue`, `fixtures_and_results`), and adds unique provider/source/team-ID and provider/source/competition-ID indexes. PR #15 is merged and CI passed; Migration 008 has not yet been applied to Neon.

## Materialization implementation — merged, production writes not executed

PR [#15](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/15) adds `backend/app/canonicalization.py` with a read-only-by-default planner and an explicit `execute=True` writer. It is pinned to 5DollarFootballAPI Brazil Serie B import run 3, competition `522514093`.

The implementation:
- Uses the exact import-run response reservations, source observations, sightings, successful provider responses, rights approval IDs and payload hashes.
- Chooses a deterministic successful sighting for each source identity and preserves the source-local provider ID.
- Creates `SOURCE_LOCAL_ONLY` canonical team/competition placeholders; all identity links remain `REVIEW_REQUIRED`.
- Creates one canonical fixture per provider fixture row, preserving kickoff, status and score; completeness remains `SOURCE_ROW_ONLY`.
- Marks the known America MG / América Mineiro fixture pair as `CONFLICT` without merging either team or fixture.
- Keeps UNKNOWN fixtures scoreless and creates no review events, no PIT promotions, and no provider HTTP requests.
- Uses transaction-scoped advisory locking, uniqueness constraints and strict replay comparisons to make execution idempotent and fail on provenance drift.

Final CI [#44075667064](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44075667064) passed: 113 backend tests, Ruff, Android debug build and APK artifact upload.

## Production source-scope audit — read-only

The exact run-3 scope contains 374 fixture observations, 21 team observations and one competition observation: 396 in total, with 0 PIT-certifiable. There are 370 FINISHED fixtures with both scores and four UNKNOWN fixtures with no scores. All 374 fixture rows have exact source observation/sighting/response provenance. The source approval is APPROVED and permits storage/internal analysis for this competition.

The unresolved pair is provider fixture IDs `3116209225` and `2341822348`, at 2026-03-22 20:58:35Z and 21:00:00Z, respectively. Both list Goiás provider ID `3126624865` as home side and differ only in the America provider ID (`1102583842` versus `3808811746`). Keep both source fixtures and both provider teams separate, and flag both fixture identities CONFLICT. Do not infer full season schedule completeness.

No canonical rows have been inserted into production. All seven canonical tables and source identity-link tables remain empty.

## Materialization sequence

1. **Completed:** apply Migration 007 through the controlled checksum-verified workflow; checksum and all seven tables, four functions and ten triggers verified.
2. **Pending:** apply Migration 008 through the same controlled workflow. It repairs the generic provenance trigger and adds unique indexes; verify its exact checksum, function and both indexes.
3. Run the materialization planner in read-only mode against production and confirm 21 teams, one competition, 374 fixtures, 370 finished, four UNKNOWN, complete provenance, and the expected America identity conflict pair.
4. Only after the dry-run reports ready, execute the materializer in a separate explicit production write operation. The service must create source-local placeholders, all links `REVIEW_REQUIRED`, and fixture rows `SOURCE_ROW_ONLY`.
5. Reconcile inserted counts, provenance, status/score invariants, and idempotent replay. Do not create human review events or mark identities verified.
6. Reconcile season completeness against an authoritative schedule before asserting coverage.
7. Keep canonical identity, source rights, and PIT feature eligibility as independent gates. No existing run-3 observation may enter pre-match features.

