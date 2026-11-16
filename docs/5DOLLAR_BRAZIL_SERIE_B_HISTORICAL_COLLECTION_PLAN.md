# 5Dollar Brazil Serie B — bounded historical collection plan

**Document ID:** VAA-INGEST-PLAN-001  
**Version:** 1.2  
**Date:** 2026-11-16  
**Status:** LIVE COLLECTION BLOCKED — the persistent budget/checkpoint controls and ephemeral PostgreSQL dry-run are verified; the independent Neon database is not yet provisioned.

## 1. Objective and strict scope

Prepare a resumable, quota-bounded fixture/result collection for one competition only:

- Provider: 5DollarFootballAPI Community.
- Competition: Brazil Serie B, provider ID `522514093`.
- Candidate interval: `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`.
- Endpoint: `GET /v1/leagues/522514093/fixtures`.
- Page size: 100.
- Fields: fixture identity, competition, teams, kickoff, status, goals, corners and cards where returned.
- No odds endpoints, no other competitions, no model training, no prediction publication, and no cross-provider automatic joins.

The candidate interval aligns with the observed AI Midas Brazil Serie B snapshot dates. That does not imply 5Dollar has the same coverage or that AI Midas rows are the expected 5Dollar count.

## 2. Evidence supporting the plan

- Community plan account and Brazil competition catalogue verified in Actions run [#43884649616](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43884649616).
- Brazil Serie B competition ID `522514093` confirmed.
- One-request endpoint sample returned HTTP 200 and 8 rows for 2026-11-07 through 2026-11-08 UTC in run [#43916841159](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43916841159).
- The sampled page reported `count=8` and `has_more=false`. Treat `count` as observed page metadata only; do not assume it means a season total.
- Existing adapter and provider qualification record support the league-specific start/end route and pagination parameters. The two-day probe is still the only new-repository fixture-response sample.
- Community quota reported as 300 requests/hour and 20 requests/minute burst. Prior VELTRIX historical qualification used a 40-request ceiling; retain that conservative ceiling for this isolated pilot.

## 3. Hard request budget

**Maximum fixture-endpoint requests for the entire pilot: 40.**

- 34 initial date-window requests are budgeted.
- Up to 6 additional page requests are reserved for windows reporting `has_more=true`.
- Each request uses one competition, one date window, one page, and `per_page=100`.
- No automatic retries. A transient failure is recorded and the run stops for review.
- Throttle to no more than 5 requests/minute, comfortably below the Community burst limit.
- PostgreSQL enforces `request_budget <= 40` with a schema constraint. Each request must first acquire a durable reservation in `import_request_reservations`; a row lock on the import run serializes workers and atomically increments `requests_used` before the HTTP call. Request 41 is rejected by the database-backed budget service.
- Each reservation has a unique `(import_run_id, request_key)` and a canonical request-parameter hash. A repeated identical key returns `created=false`; the caller must not issue HTTP for that reservation again. Reusing a key with different request data is a hard conflict.
- `FiveDollarFootballProvider.fetch_fixtures` now accepts a request-reserver callback and a `require_request_reservation` mode. The historical path must set the requirement to true. The callback runs immediately before every page request; a missing callback or an existing reservation blocks the HTTP call.
- Do not make status, competition-discovery, odds, or other provider calls inside this collection run.

If the required pages exceed the 40-request ceiling, stop with a resumable incomplete run. Do not silently raise the ceiling or widen the plan.

## 4. Date-window strategy

Split the half-open candidate interval into contiguous seven-day windows:

- Window 1 starts 2026-03-21T00:00:00Z.
- Each window ends exactly seven days after its start, exclusive.
- The final window is clipped at 2026-11-09T00:00:00Z.
- No overlaps or gaps are permitted.
- Convert boundaries to UTC Unix seconds exactly as the adapter does.

A seven-day window is a collection-planning choice, not a claim that every seven-day interval is complete after one page. For each window:
1. Request page 1.
2. Validate HTTP status, response envelope, row schema and pagination object.
3. Persist response provenance, checksum, row counts and checkpoint before advancing.
4. If `has_more=false`, mark that window page-complete.
5. If `has_more=true`, request the next page only if the global 40-call budget has capacity.
6. Continue until `has_more=false` or the hard ceiling/stop condition is reached.

The league endpoint's wider date-window support is documented in the provider API review; this pilot still validates every actual response and stops on unexpected behaviour.

## 5. Checkpoint and idempotency requirements

Every run must have:
- immutable run ID and plan version;
- provider, competition ID, date interval and page size;
- hard request ceiling and actual request counter;
- current window start/end and next page;
- last successful request ID, retrieval timestamp, HTTP status and response checksum;
- row count, pagination metadata, duplicate count, invalid count and quarantine count;
- terminal state: COMPLETED, INCOMPLETE_BUDGET, STOPPED_PROVIDER_ERROR, STOPPED_SCHEMA_DRIFT, or STOPPED_RIGHTS.

A page checkpoint is durable and can be recovered in deterministic window order after process interruption. Persist response evidence and normalized records before marking a window complete. Replaying a page must be idempotent by provider + provider record ID + observation identity; do not create duplicate fixture identities or overwrite immutable source sightings. A reservation already created before a crash is never refunded; if its response/checkpoint is missing, stop for reconciliation rather than silently issuing a duplicate request.

No cross-provider fixture merge is allowed during ingestion. Provider-local IDs remain authoritative until a separately reviewed crosswalk exists.

## 6. Validation and stop conditions

Stop the run immediately on:
- HTTP 401, 403, 301, unexpected redirect, or other non-success status;
- HTTP 429 (record Retry-After, but do not retry in this run);
- invalid JSON or unexpected `success` envelope;
- missing/non-list `data`;
- malformed pagination or non-boolean `has_more`;
- fixture rows missing required IDs, teams, league, or timezone-aware kickoff;
- invalid score/stat values or contradictory settled-score semantics;
- repeated fixture IDs with conflicting immutable identity/score data;
- page count or response behaviour inconsistent with the page request;
- request counter reaching 40;
- database transaction, rights approval or checkpoint failure.

Every rejected record must be retained in a quarantine record with a reason code. Never silently coerce invalid scores or treat unknown statuses as settled.

## 7. Rights and point-in-time controls

- Use the approved 5Dollar Community source scope for Brazil Serie B fixtures/results only.
- Community terms permit internal caching and use in the user's own product; raw response resale/redistribution is prohibited.
- Keep raw response evidence private. Do not commit provider payloads or API credentials.
- If these fields are ever displayed in a public-facing product, include the required attribution: **Football data by 5DollarFootballAPI** with the provider link.
- The API does not expose the original result-publication timestamp. Store the documented four-day post-kickoff availability proxy with `point_in_time_certifiable=false`; never claim it is an exact source publication timestamp.
- Settled scores may be used as target labels subject to rights and integrity checks. Post-match statistics are descriptive-only unless independent point-in-time evidence is obtained.
- No 5Dollar Community odds are included; the historical odds endpoint is not CLV-qualified.

## 8. Database and execution gate

The repository now contains migration `003_import_request_reservations.sql`, the atomic `PostgresRequestBudget` service, and deterministic checkpoint recovery reads. CI run [#43922283499](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43922283499) passed all 76 backend tests, Ruff lint, Android debug build and APK artifact upload. Its PostgreSQL-backed dry-run simulated the 34 windows with 40 reservations (34 first pages plus six second pages), recovered all 34 checkpoints, and rejected reservation 41 without making external provider calls. A separate integration test proved the actual provider HTTP boundary uses the persisted budget: first reservation sent one mocked HTTP request; replay of the same page was blocked before a second request. Additional tests cover duplicate-key concurrency, paused runs, provider stop conditions, and the database-level `request_budget <= 40` constraint.

**Live execution remains blocked because the separate Neon resource does not exist yet.** The only Neon organization available to the connected account is `Vercel: Nexora Apparel`, which is managed by Vercel. Direct Neon project creation was rejected by the provider. The Neon Marketplace integration is installed on the Vercel team, but resource provisioning is exposed through Vercel Marketplace/CLI rather than the available Neon project-creation action. The existing `VELTRIXFOOTBALL` database/project is not to be reused.

Before live collection:
1. Provision a separate Neon resource/project through the Vercel Marketplace integration for VELTRIX AI ANALYST; do not attach or reuse the legacy VELTRIXFOOTBALL database.
2. Obtain its connection string securely and configure it as a secret; never commit it or paste it into source files.
3. Apply the checksum-verified migrations with the explicit expected database name and remote opt-in; verify `current_database()` is exactly `veltrix_ai_analyst` and inspect the migration ledger.
4. Register and verify the effective 5Dollar source approval for this exact competition, data types, use and terms evidence.
5. Run the controlled DB dry-run against the new independent database, including checkpoint recovery, duplicate reservation behaviour, 40-request ceiling and stop conditions.
6. Execute the historical pilot only after all preceding checks pass.

## 9. Acceptance criteria

The pilot is accepted only if:
- all 34 date windows are accounted for as complete or explicitly incomplete;
- actual API calls do not exceed 40;
- every successful page has a checksum, retrieval time, request metadata and durable checkpoint;
- every fixture has stable provider-local identity and timezone-aware kickoff;
- settled-score semantics are enforced and anomalies quarantined;
- duplicates/conflicts and missingness are quantified;
- no raw provider data or credentials enter the public repository;
- no source-publication timestamp or PIT eligibility is inferred from kickoff time;
- the final report clearly distinguishes observed coverage from unqueried dates.

## 10. Current execution state

- Plan written: yes; v1.1.
- Provider requests made for this plan: zero (the only provider call was the earlier bounded two-day probe, not this collection).
- Ephemeral PostgreSQL dry-run: passed; 34 checkpoints recovered, exactly 40 simulated reservations accepted, request 41 rejected.
- CI: run #43922283499 passed 76 backend tests, Ruff, Android debug build and APK upload.
- Independent Neon database provisioned: no; Vercel-managed organization requires Marketplace resource provisioning.
- Historical import: not started.
- Models/predictions changed: no.
