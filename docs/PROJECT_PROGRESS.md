# VELTRIX AI ANALYST — Project Progress Register

> Canonical execution tracker for the VELTRIX AI ANALYST project. Update this document whenever implementation status, scope, decisions, blockers, or validation evidence changes.

**Last updated:** 2026-11-16 (run 3 completed and automatic validator passed; historical dataset remains non-PIT)nd read-only Neon preflight passed; manual historical-import dispatch is the remaining blocker)  
**Repository:** https://github.com/Nexora-Apparel/veltrix-ai-analyst  
**Default branch:** `main`  
**Repository visibility:** Public  
**Product:** Personal-use, cloud-backed native Android football analysis and prediction application

## Current verified position

- **Stage:** Stage 2 — Data integrations and historical migration.
- **Completed foundations:** Stage 1; PostgreSQL provenance schema and runtime ingestion store (PR #1 and #2); hybrid ML architecture specification; AI Midas pinned snapshot verification; 5Dollar Community account/Brazil competition preflight; bounded 5Dollar Brazil Serie B fixture endpoint probe; deterministic date-window planner; persistent request-budget enforcement; checkpoint recovery; controlled ephemeral-PostgreSQL dry-run.
- **Infrastructure verified:** dedicated Neon database, GitHub Actions environment secret, source approval, four migrations, request reservations, checkpoints and bounded importer are configured. No live historical import has yet completed.
- **Not built:** football feature pipeline, model training/calibration, prediction API, Android product flows, production deployment.
- **No prediction model has been trained or certified.**
- **Project isolation:** no legacy VELTRIX FOOTBALL 2.0 prediction logic, weights, priors, calibration or decision rules are reused.

## Historical import attempt #1 — BLOCKED BEFORE PROVIDER HTTP

- Workflow run [#43954509888](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43954509888), job [#133605398471](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43954509888/job/133605398471), was manually dispatched on 2026-11-16 and failed in `PostgresIngestionStore.sync_source_approval()` with `SOURCE_APPROVAL_ID_ALREADY_EXISTS_WITH_DIFFERENT_EVIDENCE`.
- Root cause: `scope_values`, `data_types`, and `permitted_uses` are semantic sets in `SourceApproval`, but are stored as JSONB arrays. The comparison sorted the in-memory sets but compared them to persisted arrays in their original order. The registered approval values were semantically identical; ordering alone caused the false conflict.
- Read-only Neon verification confirmed the registered approval's provider, source, scope, seven competition IDs, data types, approved status, terms evidence hash, permitted uses, non-commercial restriction and attribution/raw-redistribution flags match the code grant.
- Failure occurred while creating the import run, before the fixture request loop. Read-only counters after failure: 0 fixture request events, 0 fixture response records, 0 imported provider fixtures. The two existing import runs, 80 request reservations and 68 checkpoints are the prior DB-only dry-run/rehearsal records; they are not provider HTTP calls.
- PR [#10](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/10) canonicalizes the three stored JSONB arrays before comparing them and adds a PostgreSQL regression test that reverses all three arrays. It does not modify or broaden the rights grant.
- At the time of this incident record, collection was paused pending CI, merge and read-only preflight. Those gates have since passed on 2026-11-16; see the latest verification section below. The import still requires a manual `workflow_dispatch` launch.

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


### Historical importer — 2026-11-16
- [x] PR #3 merged: resumable Brazil Serie B importer, response provenance, fixture persistence, 34 checkpoints, page resume, 40-request cap and 12-second request spacing.
- [x] Manual-only workflow requires explicit collection confirmation and an optional paused run ID.
- [x] CI #43941999882 passed 80 backend tests, Ruff, Android debug build and APK artifact upload. Tests use mocked HTTP; no 5Dollar calls were made.
- [ ] Live import remains locked until `VELTRIX_AI_ANALYST_DATABASE_URL` is securely configured as a GitHub Actions environment secret.
- [ ] Add raw-response capture and quarantine for non-success or malformed responses before live collection. Existing importer stops safely and does not retry a reserved request.
- [x] No historical 5Dollar requests, odds calls, fixture imports, model training or prediction publication occurred.


### Failed-page capture and quarantine — 2026-11-16
- [x] PR #4 merged at `cabdf8c2cfd831ad67cf9979ddb783b77906b5a4`: raw HTTP responses captured before validation; request events persisted; failed pages quarantined with linked response ID/checksum/status; automatic replay blocked for unresolved quarantines.
- [x] CI #43944083287 passed 82 backend tests, Ruff, Android debug build and APK artifact upload. Malformed JSON test verifies raw body retention and quarantine.
- [x] Migration 004 applied to Neon database `veltrix_ai_analyst`; SHA-256 `567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf`; five columns and unique request-key constraint verified.
- [ ] Live collection remains locked until `VELTRIX_AI_ANALYST_DATABASE_URL` is securely configured as a GitHub Actions secret.
- [x] No 5Dollar historical requests, odds calls, fixture imports, model training or prediction publication occurred.


---

## 14. Latest authoritative checkpoint — 2026-11-16

This section supersedes older queue entries above where they describe the importer, quarantine, Neon provisioning, or migration status as incomplete.

### Implemented and merged
- PR #1 and PR #2: provenance-first PostgreSQL schema and runtime ingestion store.
- PR #3: fixed-scope, resumable Brazil Serie B historical importer and manual-only workflow.
- PR #4: raw HTTP response capture and failed-page quarantine; unresolved quarantines block automatic resume.
- Migration 004 applied to the dedicated Neon database; SHA-256 `567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf`.
- Importer implementation: `backend/app/providers/historical_import.py`.
- CLI: `scripts/collect_brazil_serie_b_history.py`.
- Workflow: `.github/workflows/historical-brazil-serie-b.yml`.
- CI #43944083287 passed 82 backend tests, Ruff, Android debug build and APK artifact upload. The importer integration tests use mocked HTTP; this is not a live provider collection.

### Database state
- Dedicated Neon resource: `young-wind-27772160`.
- Database identity: `veltrix_ai_analyst`, PostgreSQL 18.7.
- Migrations 001–004 are applied and checksum-verified.
- The Vercel CLI's sensitive environment pull redacted `DATABASE_URL`; the Python migration runner was not executed. Migrations were applied through the authenticated Neon SQL connection and verified in the migration ledger.
- Neon-backed rehearsal run 2 is PAUSED with `DRY_RUN_ONLY_NO_PROVIDER_HTTP`: 34 contiguous checkpoints, 40 simulated reservations, all checkpoints recovered, request 41 rejected, zero fixture rows and zero 5Dollar HTTP requests. This rehearsal consumed no provider quota.

### Current blocker — GitHub Actions database secret
- Required GitHub Actions environment: `veltrix-historical-import`.
- Required environment secret: `VELTRIX_AI_ANALYST_DATABASE_URL`.
- It must contain the dedicated `veltrix_ai_analyst` database URI, not the integration's `neondb` URI.
- GitHub connector does not expose repository/environment secret write APIs in this session. Do not attempt to transmit the credential through chat, source code, workflow inputs, logs, or artifacts.
- Secure setup instructions: `docs/GITHUB_ACTIONS_DATABASE_SECRET_SETUP.md`.

### Hard safety state
- Live historical import: **LOCKED**.
- Historical 5Dollar requests under this collection plan: **0**.
- Imported fixture rows: **0**.
- Odds requests: **0**.
- Model training/prediction publication: **not started**.
- Request budget remains **40 maximum**, no automatic retries, 12-second minimum request spacing.
- No use of the VELTRIX FOOTBALL 2.0 database, prediction logic, priors, or model artefacts.

### Next execution sequence
1. Configure the dedicated database URI as the GitHub environment secret.
2. Add/run a zero-provider-request preflight that checks database identity, migrations 001–004, approval scope and quarantine state without creating fixture rows.
3. Verify the secret-backed runner can connect to the exact dedicated database; output sanitized checks only.
4. Review the preflight and collection envelope before any live workflow dispatch.
5. If a provider request fails, preserve the raw response, quarantine it, pause the run and reconcile manually. Never retry a reserved request or exceed 40 calls.

### Documentation discipline
Every subsequent implementation, migration, CI result, provider call, import count, blocker, or scope decision must be recorded in this register and the relevant dated ledger. Never update status to PASSED based only on code inspection or a mocked test.


### Post-import quality gate — 2026-11-16
- [x] PR #5 merged at `c477516c804b0de4a8b825d29ded13fd5ea22f22`: read-only validator checks exact DB/source/date scope, 34 checkpoints, request budget and canonical hashes, raw response linkage/checksums, rights approval, fixture integrity and non-PIT provenance.
- [x] Manual workflow runs the quality validator automatically after successful import completion.
- [x] Operator instructions added: `docs/HISTORICAL_IMPORT_OPERATOR_RUNBOOK.md`.
- [x] CI #43946317661 passed 82 backend tests, Ruff, Android debug build and APK artifact upload.
- [ ] Live historical collection remains locked until GitHub Actions environment secret `VELTRIX_AI_ANALYST_DATABASE_URL` is configured with the dedicated `veltrix_ai_analyst` URI.
- [x] No historical 5Dollar API calls, odds calls, fixture imports, model training or prediction publication occurred.


### Read-only collection preflight — correction and secret setup confirmation (2026-11-16)
- [x] User confirmed the GitHub environment secret `VELTRIX_AI_ANALYST_DATABASE_URL` was saved in `veltrix-historical-import`. Its value remains private and is not yet validated by GitHub Actions.
- [x] Read-only Neon inspection identified the actual registered approval: `approval-5dollar-community-fixtures-2026-11-12`. The earlier PR implementation referenced a nonexistent approval ID.
- [x] Verified that approval belongs to `5DollarFootballAPI` / `5dollarfootballapi`, includes competition `522514093`, and permits fixtures/results plus competition/team catalogue data; it is non-commercial, requires attribution and disallows raw redistribution.
- [x] Corrected preflight approval binding and added a regression test.
- [x] Reconfirmed database identity `veltrix_ai_analyst`, PostgreSQL 18.7, migration checksums 001–004, zero unresolved 5Dollar quarantine rows and zero PLANNED/RUNNING 5Dollar import runs.
- [x] PR #7 merged after CI run #43949016507 passed backend tests, Ruff lint and Android debug APK build/upload. Squash merge: `34f3e27dbdf9c3ddd17e9ab4fe0f92589ff00e32`.
- [ ] Run the read-only preflight from the Actions page to verify the saved secret and runner connectivity.
- [x] No provider requests, reservation writes, fixture writes, odds calls or model operations were performed during this correction.
- [x] Historical collection remains **LOCKED**.


---

## 15. Authoritative read-only preflight result — 2026-11-16

The secret-backed GitHub Actions preflight has now completed successfully. This section supersedes the older statements above that describe runner secret validation or read-only preflight execution as pending.

- [x] Run [#43949967262](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43949967262) completed with conclusion `success`; job [#133589528998](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43949967262/job/133589528998).
- [x] Runner connected using GitHub environment secret `VELTRIX_AI_ANALYST_DATABASE_URL` and verified exact database identity `veltrix_ai_analyst` (PostgreSQL 18.7).
- [x] Project schema and migrations 001–004/checksums passed.
- [x] Registered 5Dollar approval/scope passed.
- [x] Unresolved quarantines: 0; active import runs: 0.
- [x] Side effects: provider HTTP requests 0; database writes 0; fixture rows written 0.
- [x] The Actions secret is validated; its value remains private and is not recorded.
- **Gate status:** read-only infrastructure preflight PASSED.
- **Live historical collection status: LOCKED.** The preflight is not an import authorization. A separate explicit user go-ahead is required before dispatching the historical collection workflow.
- On any later authorized collection, enforce the existing Brazil Serie B-only scope, fixtures/results only, 40-request hard ceiling, durable pre-request reservations, no retries, 12-second minimum spacing, and quarantine/pause on failures. No odds calls or model training are authorized by this preflight.

Detailed evidence: `docs/ledger/2026-11-16-read-only-preflight-passed.md`.


---

## 16. Import approval identity audit — 2026-11-16

A pre-collection code audit found that `backend/app/providers/historical_import.py` derived a second approval ID (`approval-5dollar-ai-analyst-historical-2026-11-16`) even though the database preflight had verified the existing registered grant `approval-5dollar-community-fixtures-2026-11-12`. The scope and rights fields were copied from the same reviewed Community approval, but maintaining two IDs weakened the approval chain and made the code diverge from the preflight's canonical record.

- [x] Identified the mismatch before any historical import request was made.
- [x] Correction merged via PR [#8](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/8), merge commit `71eedf3abeedcd0312d7f7038b5e9541b7af5484`: importer now uses the canonical `FIVEDOLLAR_COMMUNITY_APPROVAL` object directly; no derived approval ID.
- [x] Added regression test asserting exact approval ID, provider, source, competition scope and fixtures/results data type.
- [x] Updated collection plan to prohibit derived duplicate approval IDs.
- [x] CI #43952346445 passed backend tests, Ruff lint, Android debug build and APK artifact upload.
- [x] Read-only Neon query confirmed the canonical registered approval row matches the complete source approval definition used by the importer.
- [x] No provider HTTP calls or database writes were made during this audit/correction.
- **Live historical collection remains LOCKED** pending separate explicit user authorization.


---

## 17. Point-in-time feature eligibility policy — 2026-11-16

- [x] Drafted `docs/FEATURE_ELIGIBILITY_AND_POINT_IN_TIME_POLICY.md` before any model or feature pipeline is built.
- [x] Explicitly separates valid post-match target labels from pre-match feature eligibility.
- [x] Marks 5Dollar post-match statistics and the four-day availability proxy as non-PIT-certified.
- [x] Marks AI Midas historical CSV as descriptive-only until independent publication/availability evidence is established.
- [x] Defines required event/publication/first-observed/available/retrieved timestamps, source rights linkage, feature registry, cutoff checks, chronological splits, leakage controls and training acceptance gate.
- [x] PR [#9](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/9) merged to `main` at `9e72b4a4bf6b6e03a642237c9fe3716ee837d80c` (documentation-only; no CI workflow was triggered for this docs-only change).
- No provider requests, database writes, fixture imports, odds calls or model training were performed for this policy.


## Latest verification — 2026-11-16 — PR #10 merged; import ready for dispatch

### CI and merge
- CI run [#43956828039](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43956828039), head `266182017ffced5b4bec657a26d33f554ad2ad84`, completed successfully.
- Android debug build and APK artifact upload passed.
- Backend test suite passed; Ruff lint passed.
- PR [#10](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/10) merged by squash at 2026-11-16T21:09:10Z. Merge commit: `6e37dbf7bae782e7b75a1594b69cfa8aab80a422`.

### Read-only Neon preflight
- Dedicated database `veltrix_ai_analyst`, PostgreSQL 18.7, confirmed.
- Migrations 001–004 are present in `public.schema_migrations` with checksums matching the repository migration manifests:
  - 001 `11516fc36e78cca9d0a47f677e2ab451fc1beb6b899d74f9f007b979c98ebf07`
  - 002 `a5389d81f7816837c0dfedd35784f8834c4484c13a946ea166dd6d55615c4285`
  - 003 `fa841cf34fe836f3d7d7251edd36e4d5e619d185f6adf4585ac851ebcdc0560e`
  - 004 `567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf`
- Approval `approval-5dollar-community-fixtures-2026-11-12` remains APPROVED for 5DollarFootballAPI. Competition `522514093` is included. Data types remain fixtures/results and competition/team catalogues. Permitted uses include historical import and internal analysis/model work; commercial use is false, attribution is required, and raw redistribution is prohibited.
- Read-only counters at preflight: provider request events 0; provider responses 0; provider fixtures 0; quarantine records 0; active import runs 0; existing reservations 80; checkpoints 68. The 80 reservations and 68 checkpoints belong to prior DB-only dry-run/rehearsal records and are not provider requests.

### Historical import dispatch gate
- The original user-authorized collection scope remains Brazil Serie B competition `522514093`, interval `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`, 34 contiguous weekly windows, fixtures/results only, maximum 40 provider fixture requests, no retries, maximum 5 requests/minute, at least 12 seconds between requests.
- Workflow: [Controlled Brazil Serie B Historical Import](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b.yml).
- Workflow requires a manual `workflow_dispatch` input `confirm_collection=COLLECT_BRAZIL_SERIE_B`; optional `resume_run_id` should remain blank because no live import run has been created.
- The connected GitHub toolset exposes workflow reads and reruns but no workflow-dispatch action. Therefore the manual dispatch must be submitted through the workflow page; no provider HTTP request has been initiated in this session.
- After dispatch, verify actual request reservations and workflow logs; then run `scripts/validate_brazil_serie_b_import.py` for the resulting run. Any validation failure blocks model training. No odds collection or model training is authorized by this import step.


---

## 2026-11-16 — Live historical import interrupted; partial progress verified

### GitHub Actions evidence
- Workflow run [#43957601456](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43957601456), job [#133616186995](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43957601456/job/133616186995), was manually dispatched on `main` at 2026-11-16T21:11:59Z.
- Run conclusion: `cancelled`; job import step conclusion: `cancelled`; automatic validation step: `skipped`.
- Logs show setup and dependency installation succeeded. The bounded importer process ran until GitHub reported `The operation was canceled` at 2026-11-16T21:32:16Z. No Python traceback, HTTP error or provider schema error was emitted before termination.
- Cancellation cause/initiator is not established by the available job log; do not attribute it to the user or GitHub timeout without further evidence.

### Read-only Neon recovery inspection
- Target verified: Neon project/resource `young-wind-27772160`, database `veltrix_ai_analyst`.
- Live import run ID: `3`; database status remains `RUNNING` because the runner was terminated before normal importer finalization.
- Scope remains 5DollarFootballAPI Brazil Serie B competition `522514093`, interval `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`, 34 weekly windows, request budget 40.
- 23 of 34 checkpoints are `COMPLETED`; their totals are 247 records seen, 247 inserted, 0 duplicate, 0 rejected, 0 quarantined, and 23 checkpointed requests.
- The next checkpoint, `[2026-08-29T00:00:00Z, 2026-09-05T00:00:00Z)`, remains `RUNNING`; 10 later windows remain `PENDING`.
- The reservation ledger contains 24 reservations for run 3; run counter reports 24 requests used. Provider request and response ledgers each contain 24 entries for this run's execution period.
- The 24th request returned HTTP 200 and its raw response was persisted (response ID 24; SHA-256 `7a47acbe19ace32b0965d55a4246ff1ba87a8efad182d70d65502120a042fbfa`). Its window checkpoint was not confirmed completed before cancellation.
- Across the dedicated provider fixture table, 247 rows exist for this provider/source/competition; earliest kickoff 2026-03-21T20:00:00Z and latest 2026-08-28T23:30:00Z.
- Quarantine table count remains 0.
- Inspection queries were read-only. No database mutation, retry, or second provider request was made during recovery inspection.

### Recovery decision
- Do not start a new import run and do not restart from the beginning.
- Resume the existing import run ID `3` only, after confirming the importer safely reconciles the reserved/HTTP-200 but uncheckpointed request for the Aug 29–Sep 5 window. The existing reservation must not authorize a duplicate HTTP request.
- Workflow input on the next manual dispatch: `confirm_collection=COLLECT_BRAZIL_SERIE_B`; `resume_run_id=3`.
- The automatic post-import validator must complete successfully before this dataset can be accepted. No odds collection, model training, calibration or prediction publication is authorized by this partial import.
- Import remains **INCOMPLETE / NOT VALIDATED**.


### Recovery code audit — run 3 must not be resumed until captured-response replay is implemented (2026-11-16)
- [x] Inspected `backend/app/providers/historical_import.py` and `backend/app/providers/five_dollar.py` after confirming the 24th request has a persisted HTTP 200 response but an incomplete checkpoint.
- [x] Confirmed resume currently starts a non-completed checkpoint from `cursor_value` (page 1 for this window) and calls the provider adapter again.
- [x] The persistent reservation callback correctly refuses to repeat the already-reserved request. However, the current resume path does not replay the already-captured raw response into `FixturePagePersister`; it raises the duplicate-reservation error instead.
- [x] The exception path can then quarantine the page and mark the checkpoint FAILED. Therefore dispatching run 3 with `resume_run_id=3` before a recovery fix would turn a safely captured HTTP 200 page into a manual quarantine and would not complete the import.
- [ ] Implement a deterministic captured-response replay path keyed by the exact run/window/page reservation and linked response record. Validate response status, request parameters, checksum, JSON envelope, competition/window scope and pagination before persisting fixtures/checkpoint.
- [ ] Add regression tests proving a captured HTTP 200 page is replayed without provider HTTP, the reservation is not repeated, and malformed/missing/mismatched captured responses fail closed into quarantine.
- [ ] Re-run CI, then resume only run ID 3. Do not create a new import run or repeat the reserved request.
- **Current state:** 23/34 windows complete; 247 fixtures inserted; 24/40 requests used; one captured response awaits checkpoint reconciliation; 10 windows pending; import incomplete and not validated.


### Captured-response replay implementation pass — 2026-11-16
- [x] Added an initial replay path in `backend/app/providers/historical_import.py` in commit `200ec0e7c6816926264c8a2fbddfc45d6ea29028`.
- [x] The path validates the expected request envelope, HTTP 200 linkage, raw-body SHA-256, JSON success/data/pagination structure and fixture normalization, then uses the existing transactional page persister.
- [x] Pagination continues at the next page only when the replayed page reports `has_more=true`; the captured page itself is not fetched again.
- [ ] **Not release-ready:** response evidence is currently correlated through request-event endpoint/params/time rather than a first-class foreign-key link from the durable reservation. Add reservation-to-response identity and a safe migration/backfill for run 3 before allowing resume.
- [ ] Add database-backed regression tests for exact replay, no HTTP on replay, atomic checkpoint/fixture writes, ambiguous/missing/hash-mismatched evidence, and pagination.
- [ ] Run full CI (backend tests, Ruff, Android debug build); inspect results and fix all failures.
- **Safety state:** run 3 remains paused; no new provider calls, no new import run, no model training, and no publication. The initial code commit is not evidence that recovery is validated.


---

## 2026-11-16 — Run 3 captured-response recovery fix merged

- [x] PR [#11](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/11) merged by squash; merge commit `ff8e59c52d9ff5c189570a9a174287d0a5ec66fe`.
- [x] CI run [#43962841690](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43962841690) completed successfully: backend tests passed, Ruff passed, Android debug build and APK artifact upload passed.
- [x] Added migration `005_reservation_response_link.sql`, checksum `f890cab29b59c1dd930041ef8af760a7dfa01bf09d48e1684377436652f652b8`. It adds a foreign-key response link and unique constraint, and backfills only exact window/page HTTP 200 evidence with one unambiguous match.
- [x] Captured HTTP responses are linked to their exact durable reservation in the same transaction as response/event persistence.
- [x] Resume replays the exact reservation-bound response only after validating request window/page/hash, provider/source/approval identity, matching request event, response status, JSON envelope, and raw-body SHA-256. Fixture observations and checkpoint remain atomic.
- [x] Added PostgreSQL integration regression test `test_resume_replays_reserved_response_without_repeating_provider_http`; complete CI passed.
- [x] Updated the manual collection workflow to run the checksum-verified migration runner against the dedicated `veltrix_ai_analyst` database before importer execution. It does not log credentials.
- [x] Read-only Neon query confirmed run 3 still has 24 reservations and all 24 HTTP 200 response events uniquely match their exact reserved window/page; the interrupted Aug 29–Sep 5 page has exactly one reservation. No writes/provider calls were made by this inspection.
- **Current state:** run 3 remains RUNNING in Neon; 23/34 checkpoints complete; 247 fixtures persisted; 24/40 requests reserved; the interrupted page awaits replay; 10 later windows pending; 0 quarantine rows at last inspection.
- **Next action:** manually dispatch [Controlled Brazil Serie B Historical Import](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b.yml) with `confirm_collection=COLLECT_BRAZIL_SERIE_B` and `resume_run_id=3`. The workflow applies migration 005 first, then resumes run 3. Do not leave resume_run_id blank; that would start a new run.
- **No model training, odds collection, calibration, or prediction publication is enabled by this recovery.** The run must complete and its automatic validator must pass before the collected data is accepted.


### Neon migration 005 applied and run 3 recovery link verified — 2026-11-16
- [x] Applied `005_reservation_response_link.sql` to the dedicated Neon database `veltrix_ai_analyst` and inserted its exact checksum into `public.schema_migrations`.
- [x] Read-only verification: migration checksum matches; run 3 has 24/24 reservations linked to captured response IDs; interrupted Aug 29–Sep 5 page 1 links to response ID 24; 23 completed windows remain; 247 fixture rows remain; quarantine count is 0.
- [x] The migration backfill identified exactly one matching HTTP 200 response for every run 3 reservation. No provider HTTP calls were made and no fixture/checkpoint/run status rows were changed by the migration.
- **READY TO RESUME:** workflow [Controlled Brazil Serie B Historical Import](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b.yml), select **Run workflow**, set `confirm_collection=COLLECT_BRAZIL_SERIE_B`, and set `resume_run_id=3`. Do not leave the resume ID blank.
- The workflow migration step is idempotent: it will verify migration 005's checksum and skip reapplying it, then resume run 3. The remaining 10 windows are within the existing 40-request budget; current usage is 24/40.
- Automatic post-import validation remains mandatory. Import is not yet complete or validated; no odds collection or model training is authorized.

### 5Dollar historical import — completed and automatically validated (2026-11-16)
- [x] Recovery workflow run [#43964327879](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43964327879), job [#133639654596](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43964327879/job/133639654596), completed successfully on 2026-11-16; workflow_dispatch resumed existing import run ID 3 on commit e1b7a426158b0312f65a4f6369494a93f2c608ee.
- [x] Migration verification succeeded; no unapplied migrations were reported.
- [x] Import run 3 completed all 34/34 weekly checkpoints over [2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z).
- [x] Final validator returned `passed=true`, status `COMPLETED`, 374 fixture rows and 374 fixture sightings, 374 inserted, 0 duplicates, 0 quarantined, 0 unresolved quarantines.
- [x] 34 provider requests used against the 40-request cap; all 34 request events have raw response evidence. No budget breach.
- [x] The captured-response recovery path reconciled the previously interrupted page without repeating its reserved HTTP request.
- [ ] **Data-use boundary remains:** provider publication/availability timestamps were not established. Imported observations are not eligible as pre-match training features, CLV evidence, or point-in-time backtests. Use for descriptive/result-history work only unless separate timestamp evidence establishes eligibility.
- [ ] Next stage: build source-quality/coverage and fixture canonicalization audits, then a strictly point-in-time feature eligibility pipeline. Do not train or publish predictions from this dataset as-is.
- [ ] AI Midas snapshot remains a separate descriptive candidate source with its own anomaly quarantine; do not merge it blindly with the 5Dollar import.
