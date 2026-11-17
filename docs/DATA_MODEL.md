# Stage 2 data model

The initial PostgreSQL schema is a provenance-first ingestion store. It is deliberately separate from the prediction engine and does not attempt to merge provider identities.

## Core records

| Table | Purpose | Mutability |
|---|---|---|
| `source_approvals` | Exact source/scope rights approval, evidence hash, allowed uses and attribution. | Append-only |
| `source_approval_status_events` | Approval/revocation events without mutating the original approval. | Append-only |
| `effective_source_approvals` | Read-only view applying the latest approval/revocation event. | View |
| `provider_responses` | Raw provider response bytes, SHA-256, endpoint, request metadata and response headers. | Append-only |
| `provider_request_events` | Request status, rate-limit metadata and response link. | Append-only |
| `provider_entitlement_observations` | Historical plan, competition access and quota observations. | Append-only |
| `source_observations` | Immutable normalized payloads with provider IDs, timestamps, rights and PIT status. | Append-only |
| `source_observation_sightings` | Every retrieval/response link for a deduplicated payload, preserving later availability evidence. | Append-only |
| `provider_competitions` / `provider_teams` | Latest provider-local entity projections. | Upsertable |
| `provider_fixtures` | Latest normalized provider-local fixture/result projection. | Upsertable |
| `import_runs` / `import_checkpoints` | Bounded import execution, request budgets and resumable windows. | Controlled updates |
| `sync_watermarks` | Optimistic versioned cursor per provider/data class/scope. | Controlled updates |
| `ingestion_quarantine` | Invalid, ambiguous or rights-rejected records and their resolution. | Controlled updates |
| `import_run_events` | Append-only import audit events. | Append-only |

## Identity rules

- Provider fixture, team and competition IDs remain provider-local and are never overwritten by canonical IDs.
- No cross-provider fixture merge is performed during ingestion.
- Canonical records are a separate, evidence-backed layer. The planned entities are `canonical_teams`, `canonical_competitions`, and `canonical_fixtures`; the planned links are `provider_team_identity_links`, `provider_competition_identity_links`, and `canonical_fixture_sources`.
- Each provider identity link must retain provider, source, provider-local ID, mapping status, method, evidence URI/hash, reviewer and verification timestamp. A name-only/fuzzy match is a candidate, never a verified link.
- A canonical fixture may be marked verified only after competition, home-team, away-team and source-fixture mappings are verified and kickoff/result conflicts are resolved.
- Each canonical fixture source link retains the provider fixture row ID, exact provider fixture ID, source observation ID, source response/sighting, source approval and mapping evidence. A provider source row may map to at most one canonical fixture; multiple provider rows may map to one canonical fixture only after explicit review.
- Ambiguous team, fixture or competition mappings must remain unresolved or quarantined rather than guessed. No canonical mapping is auto-created by ingestion.

## Timestamp and point-in-time rules

The schema separates:
- `retrieved_at`: when VELTRIX fetched the record;
- `source_updated_at`: provider-declared update time, if supplied;
- `source_event_time`: event time such as kickoff;
- `source_published_at`: verified source publication/availability timestamp;
- `available_at`: an explicitly documented availability time or proxy;
- `availability_basis`: why that availability time is believed.

`point_in_time_certifiable` is false by default. It can be true only when a verified source publication timestamp is present and the availability basis is `SOURCE_PUBLISHED_AT`. A retrieval timestamp or a post-kickoff proxy is not a substitute for source publication time.

## Score settlement

The provider fixture projection enforces:
- `FINISHED` requires both final scores;
- non-finished statuses must not carry final scores;
- home and away provider-team IDs must differ.

This prevents partial/live scores from being mistaken for settled results.

## Rights and raw data

- Every persisted source response and observation references a source approval.
- Scope is exact; wildcard scope is prohibited.
- Raw provider responses are private internal evidence, not public repository assets.
- Raw redistribution remains disabled unless a separate explicit rights approval allows it.
- Community attribution requirements are stored with the approval and must be applied when data is shown publicly.
- Source approvals and source observations are append-only; revocation is represented by an event.

## Import safety

- Every import run has a bounded date window, request budget, approval ID and manifest hash.
- Checkpoints are resumable and record accepted, rejected and quarantined counts.
- Sync watermarks use a version to prevent concurrent cursor regression.
- Rate-limit responses are recorded and deferred; the ingestion worker must not spin-retry.
- Duplicate source payloads are deduplicated by provider/source/entity identity and payload hash.
- Unaccounted records prevent an import run from being marked complete.

## Runtime writer

`PostgresIngestionStore` is the application write boundary for the schema. It synchronizes immutable approval records, checks effective approval status at the record time, stores raw provider responses with sanitized headers, records immutable source observations, upserts provider-local competition/team/fixture projections, creates bounded import runs/checkpoints, and writes quarantine records. It rejects credential-like request parameters, mismatched provider/source identities, unapproved scopes and invalid point-in-time claims.

## Current boundary

The dedicated Neon database `veltrix_ai_analyst` is provisioned and contains the completed, provenance-linked 5Dollar Brazil Serie B import. Migrations 001–006 are applied and checksum-verified. Migration 007 defines the canonical entity and append-only identity-review schema on a review branch; it is not yet merged or applied to Neon. No canonical identity crosswalks, production feature pipeline, trained model, prediction service or prediction publication is active.


## Pre-match feature admission gate

Migration `006_pre_match_feature_pit_gate.sql` introduces the append-only `pre_match_feature_observations` table. Its database trigger is the final admission boundary; application checks alone are not trusted.

An input is accepted only when its exact `source_observation_sightings` row:
- is `point_in_time_certifiable = true` with `availability_basis = 'SOURCE_PUBLISHED_AT'`;
- has both `source_published_at` and `available_at`, and its availability is not earlier than publication;
- links to a captured successful provider response for the same provider/source;
- has a payload hash matching the immutable source observation;
- was published and available no later than `prediction_cutoff_at`;
- is covered by an approved source grant that permits both `FEATURE_ENGINEERING` and `MODEL_TRAINING`, and was not revoked at the cutoff.

Kickoff/event time, provider update time, retrieval time and post-event availability proxies cannot satisfy this gate. Every feature row references the exact observation and exact retrieval sighting used. The table is append-only. Migration 006 is applied and checksum-verified in the dedicated Neon database. Migration 007 is under PR review and has not yet been applied.

## Historical Brazil Serie B audit (2026-11-16)

Run 3 imported 374 Brazil Serie B fixtures across 34 completed windows. The integrity audit found 370 finished scored matches and four unresolved UNKNOWN fixtures. It found 21 provider team IDs, including an unresolved `America MG` / `América Mineiro` near-time collision. Exact provider fixture IDs and exact team/kickoff keys have no duplicates, but full season completeness is not independently proven.

All 374 source observations lack publication and availability timestamps; all 1,031 sightings are retrieval-only and non-certifiable. Therefore **none of these imported records can currently enter pre-match feature inputs**. See `docs/ledger/2026-11-16-fixture-coverage-integrity-pit-audit.md` for the full audit.

