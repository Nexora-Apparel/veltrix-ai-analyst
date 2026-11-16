# 5Dollar Brazil Serie B — bounded historical collection plan

**Document ID:** VAA-INGEST-PLAN-001  
**Version:** 1.3  
**Date:** 2026-11-16  
**Status:** IMPORTER MERGED — dedicated Neon database and migrations are verified; the resumable, rights-aware importer and manual GitHub Actions workflow are merged. Live collection remains locked pending secure GitHub database-secret configuration and final preflight.

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
- The live importer enforces a 12-second minimum interval between request starts (maximum 5 requests/minute), comfortably below the Community burst limit.
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
- terminal state: COMPLETED or PAUSED; a sanitized reason code records quota, provider, schema, rights or reconciliation stops.

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

**Database prerequisites are now verified.** A dedicated Vercel/Neon resource `young-wind-27772160` contains database `veltrix_ai_analyst` (PostgreSQL 18.7); the legacy `neondb` and VELTRIX FOOTBALL database were not used. The exact database identity was queried before schema work. Migrations 001–003 were applied transactionally through the Neon SQL connection after computing SHA-256 from the repository migration files; the resulting `public.schema_migrations` ledger was read back and matched all three checksums. The repository's Python migration runner was not executed because Vercel's CLI deliberately substituted `[SENSITIVE]` for the sensitive `DATABASE_URL` during environment pull. No credential was exposed or substituted.

The approved 5Dollar Community source record is registered in this database for the documented competition/data scope, non-commercial use and attribution terms. A Neon-backed database dry-run then created 34 contiguous seven-day checkpoints and simulated 40 reservations (34 first pages plus six additional pages). It verified the hard 40 ceiling, rejected reservation 41, recovered all 34 checkpoints in deterministic order, and confirmed the provider adapter's exact ISO-8601 idempotency-key format. An initial rehearsal exposed a millisecond-format mismatch in generated keys; that rehearsal was marked FAILED and superseded by the corrected run. Both rehearsals made zero 5Dollar HTTP requests and imported zero fixture rows. The corrected run is PAUSED with 40/40 simulated reservations.

**Live collection is not started.** The database gate is passed, but the repository still needs a production-safe historical import orchestrator and a secure GitHub Actions `DATABASE_URL` secret configured for that runner. The Vercel integration-generated connection variables point to `neondb`, not the dedicated database, and the sensitive custom variable cannot be pulled by the CLI. Do not weaken secret visibility or put credentials in source code/artifacts to bypass this. Do not reuse the legacy `VELTRIXFOOTBALL` database.

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

- Plan written: yes; v1.3.
- Provider requests made for this historical plan: zero; the earlier two-day probe is separate.
- Neon database: `veltrix_ai_analyst` on project `young-wind-27772160`, PostgreSQL 18.7; identity verified.
- Migrations 001–003: applied; recorded SHA-256 checksums are `11516fc36e78cca9d0a47f677e2ab451fc1beb6b899d74f9f007b979c98ebf07`, `a5389d81f7816837c0dfedd35784f8834c4484c13a946ea166dd6d55615c4285`, and `fa841cf34fe836f3d7d7251edd36e4d5e619d185f6adf4585ac851ebcdc0560e`. Applied through Neon SQL transactions; the Python migration runner itself remains unexecuted because the Vercel CLI does not pull sensitive variables.
- Source approval: registered for the 5Dollar Community scope in the database.
- Neon-backed dry-run: corrected run ID 2; 34 contiguous checkpoints recovered, 40/40 simulated reservations recorded, request 41 rejected, duplicate key found as an existing reservation; zero provider HTTP calls and zero fixture rows.
- An earlier rehearsal (run ID 1) was marked FAILED because its generated idempotency keys included milliseconds not emitted by the provider adapter; it made no provider calls. Corrected run ID 2 is PAUSED and retained as the valid rehearsal.
- CI: run #43922283499 passed 76 backend tests, Ruff, Android debug build and APK upload.
- Historical import: not started. The resumable importer is merged in PR #3; live execution remains gated on secure GitHub Actions database-secret configuration and final preflight.
- Models/predictions changed: no.


## 11. Neon database verification update — 2026-11-16

The dedicated Neon resource `young-wind-27772160` now contains database `veltrix_ai_analyst` (PostgreSQL 18.7). Database identity was verified with `current_database()`; the integration's separate `neondb` was not used. Migrations 001–003 were applied in order through the authenticated Neon SQL connector and the SHA-256 values were recorded and read back in `public.schema_migrations`. Evidence is in `docs/ledger/2026-11-16-neon-migrations-and-dry-run.md`.

The reviewed 5Dollar Community source approval is registered in the database. Corrected Neon-backed dry-run run ID 2 created 34 contiguous checkpoints, recorded 40 simulated reservations (34 first pages plus six second pages), recovered all 34 checkpoints, and rejected request 41. The provider-compatible ISO-8601 idempotency key was verified. Run 2 is PAUSED with `DRY_RUN_ONLY_NO_PROVIDER_HTTP`. An earlier rehearsal run ID 1 was marked FAILED after its idempotency keys included milliseconds not emitted by the adapter; it made no provider requests. Neither rehearsal imported fixture rows or contacted 5Dollar.

The repository Python migration runner was not executed because Vercel CLI environment pull substituted `[SENSITIVE]` for the sensitive `DATABASE_URL`. Migrations were applied directly through Neon SQL and their checksums verified; do not claim the Python runner passed.

**Live historical collection has not started.** Remaining requirements are a tested resumable import orchestrator and secure availability of the dedicated database connection to its GitHub Actions runner. The Vercel integration-generated connection variables currently target `neondb`, not `veltrix_ai_analyst`. Keep the 40-request cap; no odds, retries, or other competitions.


## 12. Resumable importer implementation — 2026-11-16

PR [#3](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/3) was merged to `main` at `889cb26e9f97ad18efdf38fb478b7b2877344f63`. CI run [#43941999882](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43941999882) passed 80 backend tests, Ruff lint, Android debug APK build and artifact upload.

The merged implementation adds:
- page-level provider response evidence for successful, schema-valid pages, including raw response bytes, safe response headers, request parameters, request IDs and pagination metadata;
- a fixed-scope Brazil Serie B importer for the exact candidate interval, with 34 deterministic seven-day checkpoints;
- atomic request reservation before every provider HTTP call, a hard 40-request ceiling, and 12-second minimum request spacing;
- per-page transaction persisting raw response, request event, competition/team/fixture observations, provider projections and checkpoint together;
- resume from the next page when the preceding page response and checkpoint committed;
- a CLI requiring both `--execute` and `VELTRIX_ENABLE_HISTORICAL_COLLECTION=true`, plus exact database identity;
- a manual-only GitHub Actions workflow requiring explicit `COLLECT_BRAZIL_SERIE_B` input and a dedicated GitHub environment.

The PostgreSQL end-to-end test uses `httpx.MockTransport`; all 34 pages are simulated. It verifies 34 persisted response records, 34 fixture rows, 34 completed checkpoints, and 34/40 reserved requests. CI made no real provider requests.

**Failure boundary:** non-success HTTP responses, invalid JSON and malformed page schemas stop before normalized page persistence. Their durable reservation is not refunded, and the run pauses rather than retrying. A reservation without a committed response/checkpoint requires manual reconciliation. PR #4 now captures raw HTTP responses before validation and quarantines failed pages. Runs with unresolved quarantined pages cannot be resumed automatically.

**Live execution remains locked.** Configure `VELTRIX_AI_ANALYST_DATABASE_URL` as a GitHub Actions environment secret containing the dedicated `veltrix_ai_analyst` database URI, not the integration-generated `neondb` URI. The existing Community API key secret is consumed at runtime and is not embedded in source. Complete final preflight; do not start historical collection until the raw-error evidence/quarantine gate is addressed.

The importer uses immutable approval ID `approval-5dollar-ai-analyst-historical-2026-11-16`, derived from the reviewed Community approval with the same scope and evidence. It is synchronized by the importer before a new run is created; the earlier approval row remains unchanged.


## 13. Failed-page evidence and quarantine — 2026-11-16

PR #4 merged at `cabdf8c2cfd831ad67cf9979ddb783b77906b5a4`. CI run #43944083287 passed 82 backend tests, Ruff, Android debug build and APK artifact upload.

Migration `004_ingestion_quarantine.sql` was applied to the dedicated Neon database. SHA-256: `567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf`. The migration ledger, five added columns and unique request-key constraint were verified. Existing quarantine rows: zero.

Raw HTTP response evidence is now persisted before status, JSON and schema validation. Normalized observations and checkpoints are committed separately. Failed pages are quarantined with response ID/checksum/status when available; the request reservation is never refunded. Runs with unresolved quarantined pages cannot be resumed automatically and require manual reconciliation.

Live collection remains locked pending secure configuration of GitHub Actions secret `VELTRIX_AI_ANALYST_DATABASE_URL`. No 5Dollar historical requests or fixture rows have been created.


## 14. Importer and quarantine implementation update — 2026-11-16

PR #3 (resumable importer) and PR #4 (failed-page evidence/quarantine) are merged. The current implementation is in `backend/app/providers/historical_import.py`, invoked by `scripts/collect_brazil_serie_b_history.py` and the manual workflow `.github/workflows/historical-brazil-serie-b.yml`.

PR #4 captures raw HTTP response bytes and request events before response validation. Failed or malformed pages are recorded in `veltrix_ai_analyst.ingestion_quarantine` with request key and available response ID, checksum and HTTP status. Request reservations are not refunded. A run containing unresolved quarantined pages is rejected by the resume path and requires manual reconciliation.

Migration 004 is applied to the dedicated Neon database; SHA-256:
`567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf`.

CI run [#43944083287](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43944083287) passed 82 backend tests, Ruff, Android debug build and APK artifact upload. These tests use mocked HTTP and do not represent live 5Dollar collection.

### Final infrastructure gate

The importer is implemented, but live collection is still locked until GitHub Actions environment `veltrix-historical-import` has the secret `VELTRIX_AI_ANALYST_DATABASE_URL` configured with the dedicated Neon database URI for `veltrix_ai_analyst`. The Vercel integration-generated `neondb` connection must not be used.

See `docs/GITHUB_ACTIONS_DATABASE_SECRET_SETUP.md` for secure configuration instructions. After setup, run a separate preflight that checks exact database identity, migrations 001–004, source approval and quarantine state while making zero provider requests and zero fixture writes. Do not use the collection workflow as a connection test.

**Current live-collection state: LOCKED.** Historical provider requests under this plan: 0. Imported fixture rows: 0. Odds requests: 0. Model training and prediction publication: not started. The 40-request ceiling, no-retry rule and 12-second spacing remain unchanged.
