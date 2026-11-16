# Persistent request budget and controlled ingestion dry-run — executed

**Date:** 2026-11-16  
**Project:** VELTRIX AI ANALYST  
**Repository:** `Nexora-Apparel/veltrix-ai-analyst`  
**CI run:** [#43921580933](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43921580933)  
**Validated commit:** `70cb3b9a35996b5da1f781e72e0773b34fe09b62`

## Implemented

- Migration `003_import_request_reservations.sql` adds a durable per-run request reservation ledger.
- PostgreSQL schema constraint caps every import run at 40 reserved provider requests.
- `PostgresRequestBudget` locks the import-run row, validates status and remaining budget, increments the durable counter and inserts the unique reservation in one transaction.
- Reservation commits before the caller sends HTTP; a process crash does not refund it.
- Idempotency key reuse with identical request parameters returns the existing reservation with `created=false`; callers must not send HTTP again. Reusing the key with changed request parameters is rejected.
- Terminal run updates cannot lower/refund the durable request counter.
- `PostgresIngestionStore.load_checkpoints` reads window checkpoints in deterministic resume order.
- Tests cover distinct-key concurrency, same-key concurrency, idempotency conflict, paused-run refusal, hard ceiling, provider stop conditions, and checkpoint recovery.

## Controlled dry-run — ephemeral PostgreSQL

The integration test constructed the actual 34 seven-day windows for the candidate interval and simulated the request ledger without contacting 5DollarFootballAPI:

| Check | Result |
|---|---:|
| Planned windows | 34 |
| Page-one reservations | 34 |
| Additional page reservations | 6 |
| Accepted reservations | 40 |
| Recovered durable checkpoints | 34 |
| Attempted reservation 41 | Rejected |
| External provider requests | 0 |

The dry-run persisted and reloaded all 34 completed checkpoints. It verified the database counter remained at the 40-request ceiling and that the next reservation failed closed.

## Stop-condition verification

- HTTP 401, 403 and 500: stop after one request; no retry.
- HTTP 429: preserve Retry-After signal and stop; no retry.
- Retired/moved competition ID: raise a hard stop; no automatic ID substitution.
- Malformed score/schema data: reject rather than coerce.
- Paused import run: cannot reserve a new request.
- Duplicate reservation key: no second HTTP permit.
- Database request budget above 40: rejected by schema constraint.

## CI evidence

Run [#43921580933](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43921580933) completed successfully:
- 72 backend tests passed.
- Ruff lint passed.
- Android debug build passed.
- APK artifact upload passed.

## Neon provisioning blocker

The connected Neon organization is `Vercel: Nexora Apparel` and is managed by Vercel. Direct Neon project creation was rejected with an organization-managed-by-Vercel restriction. The Neon Marketplace integration is installed for the Vercel team, but the available connector actions do not expose Vercel Marketplace resource provisioning. The existing `VELTRIXFOOTBALL` project is explicitly excluded and has not been modified.

A separate Neon resource must be provisioned through the Vercel Marketplace/CLI flow. After it exists:
1. Obtain its connection string securely and configure it as a secret.
2. Apply the checksum-verified migrations with explicit expected database name and remote opt-in.
3. Verify `current_database()` equals `veltrix_ai_analyst` and inspect the schema migration ledger.
4. Run the same controlled dry-run against that independent database.
5. Only then dispatch the 34-window live collection.

## Collection state

- 5Dollar provider calls made by this dry-run: **0**.
- Production Neon database provisioned: **no**.
- Production migrations applied: **no**.
- Historical collection started: **no**.
- Model training/prediction changes: **none**.

This ledger supersedes the prior planner-only CI-pending checkpoint for the planner, request-budget and Android validation state. It does not authorize live collection.
