# Provider HTTP reservation gate — validated

**Date:** 2026-11-16  
**Project:** VELTRIX AI ANALYST  
**Repository:** `Nexora-Apparel/veltrix-ai-analyst`  
**Validated commit:** `92e9249602492889b60178fdc8f688f769da3ce3`  
**CI:** [#43922283499](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43922283499)

## Change

- `PostgresRequestBudget.callback_for_run(import_run_id)` creates the callback used by the provider adapter.
- `FiveDollarFootballProvider.fetch_fixtures` now accepts `request_reserver` and `require_request_reservation`.
- When historical collection sets `require_request_reservation=True`, the adapter refuses to start without a reservation callback.
- Before every page HTTP request, the adapter requests a durable reservation with deterministic run-local key, UTC window, page number, endpoint and sanitized query parameters.
- If the reservation is already present (`created=false`), the adapter raises before sending HTTP. It never retries a previously reserved page automatically.

## Integration test

Against ephemeral PostgreSQL and a mock HTTP transport:
1. Create a running import run with budget 1.
2. The first page reservation is committed and permits exactly one mocked HTTP request.
3. Replaying the same date window/page returns the existing reservation with `created=false`.
4. The provider stops before a second HTTP request.
5. Database counter remains exactly 1.

## Full CI validation

Run [#43922283499](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43922283499) completed successfully:
- 76 backend tests passed.
- Ruff lint passed.
- Android debug build passed.
- APK artifact upload passed.

The run includes the planner, request-budget, checkpoint recovery, 40-request hard ceiling, provider stop-condition and provider HTTP reservation-gate tests.

## Production database blocker

Neon organization `Vercel: Nexora Apparel` is managed by Vercel. Direct Neon project creation is rejected by the provider. The Neon Marketplace integration is installed on the Vercel team, but resource provisioning must use the Vercel Marketplace/CLI flow, which is not exposed by the available connector actions. No existing database was reused or modified.

## Execution status

- Ephemeral PostgreSQL safeguards: validated.
- Independent Neon production project/database: not provisioned.
- Production migrations: not applied.
- Production database identity: not verified.
- Live historical collection: not started.
- Provider requests made by this dry-run: zero.
