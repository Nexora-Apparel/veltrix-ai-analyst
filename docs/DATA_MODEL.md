# Stage 2 data model

The initial PostgreSQL schema is a provenance-first ingestion store. It is deliberately separate from the prediction engine and does not attempt to merge provider identities.

## Core records

| Table | Purpose | Mutability |
|---|---|---|
| `source_approvals` | Exact source/scope rights approval, evidence hash, allowed uses and attribution. | Append-only |
| `source_approval_status_events` | Approval/revocation events without mutating the original approval. | Append-only |
| `provider_responses` | Raw provider response bytes, SHA-256, endpoint, request metadata and response headers. | Append-only |
| `provider_request_events` | Request status, rate-limit metadata and response link. | Append-only |
| `provider_entitlement_observations` | Historical plan, competition access and quota observations. | Append-only |
| `source_observations` | Immutable normalized payloads with provider IDs, timestamps, rights and PIT status. | Append-only |
| `provider_competitions` / `provider_teams` | Latest provider-local entity projections. | Upsertable |
| `provider_fixtures` | Latest normalized provider-local fixture/result projection. | Upsertable |
| `import_runs` / `import_checkpoints` | Bounded import execution, request budgets and resumable windows. | Controlled updates |
| `sync_watermarks` | Optimistic versioned cursor per provider/data class/scope. | Controlled updates |
| `ingestion_quarantine` | Invalid, ambiguous or rights-rejected records and their resolution. | Controlled updates |
| `import_run_events` | Append-only import audit events. | Append-only |

## Identity rules

- Provider fixture, team and competition IDs remain provider-local.
- No cross-provider fixture merge is performed by this schema.
- A canonical football identity layer will be added only after Stage 3 entity-resolution rules and evidence are validated.
- A source row with an ambiguous team, fixture or competition mapping must be quarantined rather than guessed.

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

## Current boundary

This migration defines the storage foundation only. No database has been provisioned, no production connection has been made, no provider history has been imported, and no prediction code is stored in these tables.
