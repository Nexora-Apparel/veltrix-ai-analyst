# VELTRIX AI ANALYST — Project Progress Register

> Canonical execution tracker for the VELTRIX AI ANALYST project. Update this document whenever implementation status, scope, decisions, blockers, or validation evidence changes.

**Last updated:** 2026-11-16 (5Dollar Brazil Serie B fixture endpoint probe executed successfully)  
**Repository:** https://github.com/Nexora-Apparel/veltrix-ai-analyst  
**Default branch:** `main`  
**Repository visibility:** Public  
**Product:** Personal-use, cloud-backed native Android football analysis and prediction application

## Current verified position

- **Stage:** Stage 2 — Data integrations and historical migration.
- **Completed foundations:** Stage 1; PostgreSQL provenance schema and runtime ingestion store (PR #1 and #2); hybrid ML architecture specification; AI Midas pinned snapshot verification; 5Dollar Community account/Brazil competition preflight; bounded 5Dollar Brazil Serie B fixture endpoint probe.
- **Not built:** private database connection, historical import, football feature pipeline, model training/calibration, prediction API, Android product flows, production deployment.
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
- [ ] CI run #43917944552 backend tests and Ruff passed; Android debug build was still in progress at this update.
