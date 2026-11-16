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

## Materialization sequence

1. Apply migration 006 through the checksum-verified runner and verify its exact ledger checksum,
   table, function and triggers.
2. Add canonical tables and append-only identity-review events in a new checksum migration.
3. Create provider-native placeholder entities and source-identity links from exact provider IDs,
   retaining `REVIEW_REQUIRED` for real-world resolution.
4. Create one canonical fixture per provider fixture row with source links and explicit unresolved
   identity states; preserve all 4 UNKNOWN records without scores.
5. Record a reviewed conflict for the America MG / América Mineiro pair; do not merge.
6. Reconcile season completeness against an authoritative schedule before asserting coverage.
7. Keep canonical identity, source rights, and PIT feature eligibility as independent gates.
