# VELTRIX AI ANALYST — Project Progress Register

> Canonical execution tracker for the VELTRIX AI ANALYST project. Update this document whenever implementation status, scope, decisions, blockers, or validation evidence changes.

**Last updated:** 2026-11-16 (dedicated Neon database migrated; 40-request DB dry-run passed; live importer remains gated)  
**Repository:** https://github.com/Nexora-Apparel/veltrix-ai-analyst  
**Default branch:** `main`  
**Repository visibility:** Public  
**Product:** Personal-use, cloud-backed native Android football analysis and prediction application

## Current verified position

- **Stage:** Stage 2 — Data integrations and historical migration.
- **Completed foundations:** Stage 1; PostgreSQL provenance schema and runtime ingestion store (PR #1 and #2); hybrid ML architecture specification; AI Midas pinned snapshot verification; 5Dollar Community account/Brazil competition preflight; bounded 5Dollar Brazil Serie B fixture endpoint probe; deterministic date-window planner; persistent request-budget enforcement; checkpoint recovery; controlled ephemeral-PostgreSQL dry-run.
- **Not built:** independent Neon production database/connection, live historical import, football feature pipeline, model training/calibration, prediction API, Android product flows, production deployment.
- **No prediction model has been trained or certified.**
- **Project isolation:** no legacy VELTRIX FOOTBALL 2.0 prediction logic, weights, priors, calibration or decision rules are reused.

## Stage 2 — Verified evidence

### Repository and CI
- PR #1 merged (`c219b4d`); CI run #43858717326 passed 44 backend tests, Ruff lint, Android debug build and APK artifact upload.
- PR #2 merged (`f3bec93`); CI run #43860443460 passed 52 backend tests, Ruff lint, Android debug build and APK artifact upload.
- PostgreSQL migrations are tested against ephemeral PostgreSQL. Remote migration requires explicit opt-in and an expected database name; legacy VELTRIX Football DB names are blocked.

### AI Midas Brazil Serie B snapshot
- GitHub Actions run [#43882958891](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43882958891) completed successfully.
- Pinned CSV: 192,284 bytes; SHA-256 `55b0c00629abd2d4ff3c31659ada950b67ffc2752609284b32c15c99f71152ab`; Git blob SHA-1 `b6bdb94c053d2149e6232fb100e1f158e46e4533`.
- 738 team-match rows, 369 matches, 20 teams; 2026-03-21 through 2026-11-08.
- One inconsistent match (Náutico 0–3 CRB, 2026-11-07; two inconsistent team rows) was quarantined; 368 matches remain descriptive candidates.
- Raw CSV remained in runner temporary storage; only a sanitized manifest artifact was retained.
- Non-commercial only; no verified source publication timestamp; descriptive-only, not PIT-certified, not eligible as pre-match model features, and not CLV-qualified.

### 5Dollar Community account preflight
- Run [#43884649616](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43884649616) succeeded.
- Community plan; reported 300 requests/hour and 20/minute burst; Brazil Serie B visible as competition ID `522514093`.
- This proved account and competition catalogue access only.

### 5Dollar Brazil Serie B fixture endpoint probe — EXECUTED
- Run [#43916841159](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43916841159), workflow `5dollar-fixture-probe.yml`, commit `c6be115cf278c3466ee1d6c30b05efc80e2c3359`, completed successfully on 2026-11-16.
- Job: “One-request fixture endpoint probe”; all steps completed successfully.
- Actual endpoint: `GET /v1/leagues/522514093/fixtures`.
- Scope: 2026-11-07T00:00:00Z inclusive to 2026-11-09T00:00:00Z exclusive; page 1; page size 100.
- Manifest confirms HTTP 200, 8 rows, pagination count 8, `has_more=false`; one request, zero retries, zero pagination follow-ups.
- Response size 3,872 bytes; response SHA-256 `76009f299a3d4a42e9df54d8d9cf6682a43b7e3f36c12713a7cc940d41fc88d8`.
- Returned fields: `cards`, `corners`, `goals`, `id`, `kickoff_ts`, `kickoff_utc`, `league`, `status`, `status_code`, `status_reason`, `teams`.
- First fixture sample: ID 3728617699; kickoff `2026-11-08T22:15:00+00:00`; status `finished`. Timestamp evidence currently establishes kickoff/event time fields only, not source publication/availability time.
- Sanitized artifact `5dollar-brazil-serie-b-fixture-probe`, artifact ID 14250910940, 704 bytes, 7-day retention. Raw response and credential were not uploaded or printed.
- This qualifies endpoint access and the sampled response schema for this exact two-day window only. It does not establish season completeness, historical coverage, result-field completeness across the competition, source publication timestamps, odds availability, PIT eligibility or model eligibility.

## Immediate next execution queue

1. Inspect and document fixture/result field semantics and the adapter's compatibility with the observed schema. Add bounded contract tests using the captured sanitized manifest/sample shape; do not expand provider requests to solve schema questions.
2. Design a date-windowed, resumable historical collection budget using the measured pagination behaviour. Keep an explicit hard request ceiling and stop conditions.
3. Provision a separate private PostgreSQL database only after the exact target and credentials are configured; never reuse the legacy database.
4. Test the end-to-end ingestion orchestrator against ephemeral PostgreSQL before any historical import.
5. After measured source coverage and rights/timestamp review, define the Stage 3 football-intelligence feature pipeline.
6. Implement statistical models only after point-in-time data and chronological evaluation controls are established.

## Standing constraints

- No bulk history pull, odds expansion, database provisioning, import, model training or production deployment has been performed by the probe.
- Do not treat kickoff timestamps as source publication timestamps.
- Do not infer whole-season coverage from an 8-row two-day sample.
- Keep API keys, raw provider payloads and private data out of the public repository and CI artifacts.
- Preserve the independent model rebuild boundary from VELTRIX FOOTBALL 2.0.


### 5Dollar adapter contract audit — 2026-11-16
- [x] Compared the bounded fixture probe route and query parameters with `backend/app/providers/five_dollar.py`; route and request parameter names match.
- [x] Confirmed the adapter normalizes all sampled top-level fixture field families: IDs, league, teams, kickoff, status, goals, corners and cards.
- [x] Added offline tests in `backend/tests/test_five_dollar_observed_contract.py` for the observed eight-row pagination envelope, exact route/query, mapped field families and `kickoff_ts` fallback.
- [x] No additional provider calls were made; test data is synthetic and does not contain the raw provider payload.
- [ ] CI run #43917944552 is pending/in progress at the time of this update; do not treat the test addition as validated until backend tests, Ruff and Android build finish successfully.
- [ ] Next: complete CI verification, then design a request-budgeted resumable historical collection plan. Do not start a bulk pull.


### 5Dollar collection budget design — 2026-11-16
- [x] Added `docs/5DOLLAR_BRAZIL_SERIE_B_HISTORICAL_COLLECTION_PLAN.md` (VAA-INGEST-PLAN-001 v1.0).
- [x] Plan is limited to Brazil Serie B provider ID `522514093`, candidate interval 2026-03-21 to 2026-11-09 UTC, fixture/results only.
- [x] Set a hard 40-fixture-request ceiling, seven-day non-overlapping windows, page size 100, no retries, and explicit stop/checkpoint rules.
- [x] Documented source-rights, attribution, four-day result-availability proxy and non-PIT restrictions.
- [ ] Plan is design-only: no collection requests, database provisioning, imports or model operations have been performed under it.
- [x] CI run #43917944552 completed successfully: backend tests, Ruff lint, Android debug build and APK artifact upload all passed.


### Deterministic collection-window planner — 2026-11-16
- [x] Added `backend/app/providers/collection_plan.py` with timezone-aware UTC normalization and contiguous, non-overlapping half-open date windows.
- [x] Added `backend/tests/test_collection_plan.py` for the 34-window Brazil Serie B candidate interval, UTC offset normalization, clipped final window, and invalid-input rejection.
- [ ] CI run #43918522018 is running; the earlier intermediate run for the first planner commit was cancelled by the immediately following test-file commit. The current run is the validation target.
- [ ] This planner is a pure offline utility. It does not call the provider, persist data, reserve API quota, or authorize collection.



### Persistent request budget, checkpoint recovery and controlled dry-run — 2026-11-16
- [x] Added migration `003_import_request_reservations.sql` with a durable reservation ledger and a PostgreSQL-level `request_budget <= 40` constraint.
- [x] Added `PostgresRequestBudget`: serializes reservations by locking the import-run row, commits each reservation before network use, rejects request 41, and prevents duplicate idempotency keys from authorizing a second HTTP request. A repeated reservation returns `created=false`; changed request data under the same key raises a conflict.
- [x] Added deterministic `load_checkpoints` recovery to `PostgresIngestionStore`; checkpoint tests verify a fresh store can recover completed window state after interruption.
- [x] Added PostgreSQL integration coverage for concurrent distinct reservations, concurrent duplicate keys, idempotency conflicts, paused-run refusal, and a 41-request rejection.
- [x] Added provider stop-condition tests for HTTP 401/403/500, 429 without retry, moved league IDs, and malformed score/schema data.
- [x] Controlled dry-run in ephemeral PostgreSQL simulated the 34 planned windows: 34 first-page reservations plus six second-page reservations; all 34 checkpoints were recovered; request 41 was rejected. No provider HTTP requests were made.
- [x] Added a run-bound callback from `PostgresRequestBudget` into `FiveDollarFootballProvider.fetch_fixtures`; historical collection can require a reservation before every page request, and duplicate reservations block the HTTP call.
- [x] Added a PostgreSQL-backed provider boundary integration test: the first reservation permits one mocked HTTP request; replay of the same page is rejected before a second HTTP request.
- [x] CI run [#43922283499](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43922283499) passed: 76 backend tests, Ruff lint, Android debug build and APK artifact upload.
- [ ] Independent Neon production database is not provisioned. The only connected Neon organization is Vercel-managed; direct Neon project creation is restricted. The Neon Marketplace integration is installed, but resource provisioning requires the Vercel Marketplace/CLI flow. Do not reuse the legacy `VELTRIXFOOTBALL` project.
- [ ] After the separate Neon resource exists: configure its connection string as a secret, apply checksum-verified migrations with explicit database-name/remote opt-in, verify `current_database() = 'veltrix_ai_analyst'`, then run the dry-run against that database.
- [ ] Live historical collection remains blocked; no historical provider requests or DB writes have been made.



### Provider HTTP reservation boundary — 2026-11-16
- [x] `FiveDollarFootballProvider.fetch_fixtures` supports a run-bound request-reserver callback.
- [x] Historical collection can set `require_request_reservation=True`; missing callback fails before network access.
- [x] The callback runs before each page request. A duplicate reservation (`created=false`) blocks the HTTP request.
- [x] `PostgresRequestBudget.callback_for_run` binds the persistent reservation service to one import run.
- [x] PostgreSQL integration test verifies one durable reservation authorizes one mocked HTTP request and a replay is stopped before HTTP.
- [x] Final CI run [#43922283499](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43922283499) passed: 76 backend tests, Ruff, Android debug build and APK artifact upload.
- [ ] No production Neon resource exists yet. The Vercel-managed Neon organization rejects direct project creation; provisioning must be performed through the installed Vercel Marketplace Neon integration.
- [ ] No real historical collection request has been made; keep collection blocked until the separate DB is provisioned, migrated, identity-verified and dry-run tested.


### Dedicated Neon database and dry-run — 2026-11-16
- [x] Vercel CLI authorization and project linking verified.
- [x] Dedicated Neon resource `young-wind-27772160`; database `veltrix_ai_analyst`; PostgreSQL 18.7. Exact database identity verified.
- [x] Migrations 001–003 applied through Neon SQL transactions; checksums recorded and read back from `public.schema_migrations`. See `docs/ledger/2026-11-16-neon-migrations-and-dry-run.md`.
- [x] Existing reviewed 5Dollar Community approval registered for the documented competition and data scope.
- [x] Corrected Neon-backed dry-run run ID 2: 34 contiguous checkpoints, 40 simulated reservations, 34 recoverable checkpoints, request 41 rejected, provider-compatible idempotency key format, zero provider HTTP calls and zero fixture rows.
- [x] Initial rehearsal run ID 1 marked FAILED after detecting millisecond formatting in idempotency keys; no provider calls were made. Corrected run ID 2 is PAUSED with `DRY_RUN_ONLY_NO_PROVIDER_HTTP`.
- [ ] Python migration runner was not executed because Vercel CLI environment pull redacted the sensitive `DATABASE_URL`; migrations were applied directly through Neon SQL and checksums verified.
- [ ] Live historical collection remains gated on a tested resumable importer/orchestrator and secure configuration of the dedicated DB connection for the GitHub Actions runner. Vercel integration-generated URL variables currently target `neondb`, not `veltrix_ai_analyst`.
- [x] No historical 5Dollar API calls, odds calls, fixture imports, model training or prediction publication.
