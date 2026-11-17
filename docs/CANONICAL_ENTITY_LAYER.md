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

## Schema implementation — Migrations 007/008 applied; Migration 009 review queue prepared

Migration `007_canonical_entity_layer.sql` was merged in PR #14 and applied to the dedicated Neon database through the controlled migration workflow. Workflow [#44072112212](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44072112212) verified SHA-256 `5503622ac57bd1875e08cf40cf1d87220cec99deb79e8fc23dd4ec6ebbffc30b`, all seven canonical tables, four functions and ten triggers.

Integration testing then exposed a latent defect in the generic provenance trigger: a fixture-only `NEW.canonical_fixture_id` field reference was evaluated for team-link inserts. Migration 008 replaces that function with a branch-scoped fixture check, enforces exact source-observation data types (`team_catalogue`, `competition_catalogue`, `fixtures_and_results`), and adds unique provider/source/team-ID and provider/source/competition-ID indexes. It was applied to Neon through the checksum-verified workflow and its checksum/indexes were independently verified.

## Materialization implementation — merged and production materialization independently verified

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

Canonical materialization has been executed and independently verified. Production contains 21 canonical teams, one competition, 374 canonical fixtures, 21 team identity links, one competition link, 374 fixture-source links and zero review events. All links remain `REVIEW_REQUIRED`; all fixtures remain `SOURCE_ROW_ONLY`.

## Materialization sequence

1. **Completed:** apply Migration 007 through the controlled checksum-verified workflow; checksum and all seven tables, four functions and ten triggers verified.
2. **Pending:** apply Migration 008 through the same controlled workflow. It repairs the generic provenance trigger and adds unique indexes; verify its exact checksum, function and both indexes.
3. Run the materialization planner in read-only mode against production and confirm 21 teams, one competition, 374 fixtures, 370 finished, four UNKNOWN, complete provenance, and the expected America identity conflict pair.
4. Only after the dry-run reports ready, execute the materializer in a separate explicit production write operation. The service must create source-local placeholders, all links `REVIEW_REQUIRED`, and fixture rows `SOURCE_ROW_ONLY`.
5. Reconcile inserted counts, provenance, status/score invariants, and idempotent replay. Do not create human review events or mark identities verified.
6. Reconcile season completeness against an authoritative schedule before asserting coverage.
7. Keep canonical identity, source rights, and PIT feature eligibility as independent gates. No existing run-3 observation may enter pre-match features.



## Evidence-backed identity and duplicate review — 2026-11-17

A read-only audit of the materialized records and independent official CBF match pages identified four UNKNOWN provider rows that duplicate already imported FINISHED records by exact provider team IDs:

| Duplicate provider ID | Primary FINISHED provider ID | Official CBF match | Official result |
|---|---|---|---|
| 2341822348 | 3116209225 | [Goiás–América, 22 Mar, Round 1](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/goias-x-america/832843) | 3–1 |
| 2336910968 | 1587564237 | [Fortaleza–Londrina, 23 May, Round 10](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-londrina-saf/832976) | 3–0 |
| 933498248 | 236839304 | [Fortaleza–Botafogo, 28 Jul, Round 20](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/fortaleza-saf-x-botafogo/833076) | 1–0 |
| 1988139832 | 553958702 | [Ceará–Londrina, 22 Aug, Round 24](https://www.cbf.com.br/futebol-brasileiro/jogos/campeonato-brasileiro/serie-b/2026/ceara-x-londrina-saf/833116) | 2–1 |

Three UNKNOWN rows share exact ordered home/away provider team IDs with their corresponding FINISHED rows. The Goiás–América row uses a different away provider team ID, but official CBF evidence identifies that label as the same América MG club. All four carry different provider fixture IDs and stale/incorrect kickoff timestamps. The official CBF records identify one actual match per pair. Recommended disposition is to exclude the duplicate source row after human confirmation, retaining both immutable provider records and their provenance.

The America team collision has the same pattern: provider ID `1102583842` (`America MG`) appears in 37 fixture rows; provider ID `3808811746` (`América Mineiro`) appears only in the duplicate UNKNOWN Goiás row. CBF identifies the actual Round 1 match as Goiás 3–1 América MG. This is strong evidence that the second provider ID is an alias/duplicate identity, but canonical placeholders and source IDs must remain unchanged until a human reviewer confirms the mapping.

The run-3 date boundary ends 2026-11-09. CBF's basic 2026 schedule places Round 37 on 6–8 November and Round 38 on 14 November; the detailed CBF match page records Botafogo SP–Londrina on 5 November, also within run 3. The 370 FINISHED rows cover 20 teams × 37 appearances, with 370 distinct ordered home/away pairs and no repeated ordered pairs. All 10 Round 37 pairings match the official CBF schedule. The final 10 Round 38 fixtures are outside run 3's scope. Full 370-pair schedule reconciliation remains the certification gate.

### Migration 009 — review queue and provenance audit (prepared; not applied)

Merged PR [#18](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/18) at `0d069138aad8ce4e25a2339cce3056f00431b9f0` adds:
- Immutable `canonical_identity_review_cases` and `canonical_identity_review_case_events` tables. Automated recommendations are explicitly tagged `AUTOMATED_SYSTEM`; only `HUMAN` events can confirm or reject a case.
- Seeded cases for the 20 distinct source-local team candidates, America alias candidate, competition/season identity, four duplicate fixtures, official schedule coverage reconciliation, and PIT timestamp gap.
- Provenance audit views separating source-local provenance integrity from real-world identity review.
- No updates to provider rows, source observations, canonical teams, canonical fixtures or existing links. No identity is marked human-verified by this migration.

CI [#44092601005](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44092601005) passed backend tests, Ruff, Android debug build and APK upload. Migration 009 was also prepared and tested on an isolated Neon branch copied from production: 28 cases, 28 automated recommendations, 21/1/374 provenance rows verified, four duplicate cases, zero activated aliases/dedup exclusions, and no canonical/PIT row-count changes. Migration 009 has not been applied to production. It must be applied through the existing manual checksum-verified workflow after explicit user approval. Production verification must confirm the review-case seed counts and audit-view results before any human review decisions are recorded.

### Current release gates

- Team and competition real-world identity links require explicit human evidence-backed review.
- Four duplicate fixture candidates require explicit human confirmation before downstream deduplication.
- All 370 FINISHED fixtures require exact comparison with CBF's official rounds 1–37 schedule.
- The final 10 Round 38 fixtures are outside import run 3; they require a separately bounded, rights-approved import.
- All 374 fixture observations and sightings remain non-PIT-certifiable. No source publication or availability timestamps are present. No model feature engineering or training is permitted from this data.
