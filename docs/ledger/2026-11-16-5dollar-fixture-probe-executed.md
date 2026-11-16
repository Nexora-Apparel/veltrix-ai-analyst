# 5Dollar Brazil Serie B fixture endpoint probe — executed

**Date:** 2026-11-16  
**Workflow:** `5Dollar Brazil Serie B fixture endpoint probe`  
**Run:** [#43916841159](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43916841159)  
**Commit:** `c6be115cf278c3466ee1d6c30b05efc80e2c3359`  
**Conclusion:** success

## Scope and controls

- Provider: 5DollarFootballAPI Community.
- Competition ID: `522514093` (Brazil Serie B).
- Endpoint: `GET /v1/leagues/522514093/fixtures`.
- Date interval: `[2026-11-07T00:00:00Z, 2026-11-09T00:00:00Z)`.
- Page: 1; page size: 100.
- Maximum requests: 1; retries: 0; pagination follow-ups: 0.
- No odds calls, database writes, bulk history pull, or model operations.
- Raw response and API credential were not printed or uploaded.

## Execution evidence

- Job: “One-request fixture endpoint probe”; job conclusion success.
- HTTP status: 200.
- Returned rows: 8.
- Pagination: count 8; page 1; per_page 100; `has_more=false`.
- Response bytes: 3,872.
- Response SHA-256: `76009f299a3d4a42e9df54d8d9cf6682a43b7e3f36c12713a7cc940d41fc88d8`.
- Top-level keys: `data`, `pagination`, `success`.
- Fixture field union: `cards`, `corners`, `goals`, `id`, `kickoff_ts`, `kickoff_utc`, `league`, `status`, `status_code`, `status_reason`, `teams`.
- First fixture sample: ID 3728617699; kickoff `2026-11-08T22:15:00+00:00`; status `finished`.
- Timestamp candidate observed: `kickoff_ts`; this is event/kickoff time, not source publication or availability time.
- Sanitized artifact: `5dollar-brazil-serie-b-fixture-probe`, artifact ID 14250910940, 704 bytes, 7-day retention.

## Interpretation

The fixture endpoint is reachable using the existing Community credential, and its response schema was sampled successfully for the exact two-day interval above. This does **not** establish full-season or historical completeness, all result-field semantics, source publication timestamps, point-in-time feature eligibility, odds access, CLV qualification, or model eligibility. The sample status is SAMPLED, not VERIFIED for the season.

The 8-row result and `has_more=false` apply only to this bounded query. They must not be generalized to other dates or the full competition season.

## Next steps

1. Compare observed fields and pagination semantics with the existing 5Dollar adapter; add offline contract tests without spending another API request.
2. Establish settled-score/result semantics and missingness from the existing captured response evidence where available.
3. Design a date-windowed, resumable historical collection budget with a hard request ceiling.
4. Only after budget and DB target review, provision the independent private database and test the ingestion orchestrator against ephemeral PostgreSQL before any import.

No bulk ingestion, database mutation, odds request, or prediction/model operation was performed.
