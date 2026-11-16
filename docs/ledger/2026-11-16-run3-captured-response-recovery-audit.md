# 2026-11-16 — Recovery code audit: captured response replay required before resuming run 3

## Evidence reviewed

- Interrupted workflow: https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43957601456
- Job logs: https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43957601456/job/133616186995
- Importer: `backend/app/providers/historical_import.py`
- Provider adapter: `backend/app/providers/five_dollar.py`

## Finding

The latest provider request (reservation 104, run 3, window `2026-08-29T00:00:00Z` to `2026-09-05T00:00:00Z`, page 1) completed with HTTP 200. Its raw response is already persisted as provider response ID 24, SHA-256 `7a47acbe19ace32b0965d55a4246ff1ba87a8efad182d70d65502120a042fbfa`. The associated checkpoint remains `RUNNING`.

The existing resume implementation:
1. Skips only checkpoints marked `COMPLETED`.
2. For this `RUNNING` checkpoint, uses its saved cursor (page 1) and calls `fetch_fixtures`.
3. Attempts the same durable request reservation.
4. The reservation callback returns `created=false`, and the adapter correctly refuses a duplicate HTTP request.
5. The importer does not currently read/replay the previously persisted response body into `FixturePagePersister`; its exception handler can quarantine the request and mark the checkpoint `FAILED`.

Therefore **do not dispatch a resume of run 3 yet**. This is a recovery-code gap, not a reason to repeat the provider call.

## Required fix

Implement a safe captured-response replay path before provider HTTP:
- Locate the exact persisted request event and response by run ID + reservation key/window/page + endpoint + canonical request parameters.
- Verify HTTP 200, response linkage, non-empty raw body, SHA-256, and exact request/competition/window scope.
- Parse the captured JSON using the same validation and normalization contract as the live adapter.
- Replay the page through the existing persister using the original response ID and fetched timestamp, committing fixture observations and checkpoint atomically.
- Respect pagination metadata. If `has_more` is true, advance to the next page only after its own fresh reservation.
- Fail closed and quarantine on missing, ambiguous, malformed, hash-mismatched or scope-mismatched evidence.
- Never issue another HTTP request for the already-reserved page.

Regression tests must prove: no provider HTTP during captured-response replay; no duplicate reservation; successful atomic fixture/checkpoint persistence; malformed/missing/mismatched response evidence fails closed; normal page-2 pagination still observes the 40-request ceiling.

## Current import state

- 23/34 weekly windows completed.
- 247 fixture rows inserted and represented in completed checkpoints.
- 24/40 request reservations used.
- 24th HTTP 200 response captured but not checkpointed.
- One checkpoint RUNNING; 10 PENDING.
- Zero quarantine rows at time of read-only inspection.
- Import run ID 3 remains RUNNING in the database, despite its GitHub runner being cancelled.
- No odds calls, model training, calibration or prediction publication.

## Decision

Do not create a new import run. Implement and validate response replay, then resume only run ID 3 with the explicit workflow input `resume_run_id=3`. Keep the import NOT VALIDATED until the full post-import validator passes.
