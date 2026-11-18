# VELTRIX AI ANALYST — Migration Validation Addendum

**Date:** 2026-11-18  
**Base commit:** a94ce596d7c70345bda71a1ef5c330125be2ce58

## Verified production state

- Latest production deployment is READY at commit `a94ce596d7c70345bda71a1ef5c330125be2ce58`.
- Production alias: `https://veltrix-ai-analyst-api.vercel.app`.
- `GET /health` returned HTTP 200.
- `GET /v1/predictions` returned HTTP 503 with `PREDICTIONS_UNAVAILABLE`, which is the expected fail-closed result while the runtime database connection and eligible published predictions are absent.
- Vercel environment inspection returned zero configured variables and zero hidden production variables. `DATABASE_URL` is not configured.

## Production migration ledger integrity

All 12 migration files already recorded in `public.schema_migrations` were fetched from the repository and hashed using PostgreSQL's built-in SHA-256 function. Every repository checksum exactly matched the production ledger checksum.

Verified migrations:
- 001–007
- 008_canonical_identity_link_uniqueness
- 008_model_artifacts
- 009_canonical_identity_review_cases
- 010_system_observed_pit
- 011_import_run_competition_scope

**Result: 12/12 match. No checksum drift detected.**

The two migrations beginning with `008_` are separate filenames and are both present in the ledger.

## Isolated pending-migration test

A separate Neon branch was created from production:

- Branch: `veltrix-pending-migrations-test-2026-11-18`
- Branch ID: `br-floral-tooth-bau3vl8f`
- Parent: production default branch `br-jolly-darkness-balgmi2t`

Migrations 012, 013 and 014 were executed on that isolated branch. The SQL files were split into individual statements while preserving quoted strings and dollar-quoted PL/pgSQL bodies. All 41 statements completed successfully.

### Migration outcomes

- **012 — database observation timestamps:** added database-generated timestamp columns to provider responses, source observations and source sightings. Historical records remained unchanged: 1,243 source observations and 2,884 sightings had zero non-NULL values in the new timestamp columns.
- **013 — target fixture pre-match gate:** added the target fixture relationship and strict cutoff enforcement.
- **014 — prediction publication storage:** created four prediction storage/publication tables and two publication views.

### Boundary checks

Two isolated negative tests passed:
1. A feature observation with a cutoff exactly equal to target kickoff was rejected with `PRE_MATCH_TARGET_CUTOFF_NOT_BEFORE_KICKOFF`.
2. A prediction feature snapshot with a cutoff exactly equal to kickoff was rejected with `PREDICTION_SNAPSHOT_CUTOFF_NOT_BEFORE_KICKOFF`.

No production migration was applied. No production records were modified.

## Code compatibility inspection

The current ingestion implementation in `backend/app/db/store.py`:
- obtains `system_observed_at` from the captured provider-response row;
- rejects caller-supplied system-observed timestamps;
- propagates the database-derived instant into observation and sighting records;
- rejects a system-observed availability claim if the response timestamp is missing or mismatched.

This is compatible with migration 012's new columns and the strict PIT checks.

## Remaining blockers and next actions

1. **Vercel database secret:** configure the existing production Neon connection as encrypted `DATABASE_URL` in the Vercel project. Do not expose the connection string in chat, logs, source control or documentation.
2. **Production migrations:** after the secret/runtime setup is ready, apply only 012–014 using the repository's checksum-verifying migration runner, with the expected database name set and remote migration writes explicitly enabled for the intended production database. Recheck the ledger immediately before execution.
3. **Runtime verification:** confirm database connectivity, ingestion writes and fail-closed prediction reads on the current production alias.
4. **Prospective PIT capture:** resume genuine pre-kickoff capture. Historical observations remain non-certified.
5. **Model release:** keep artifacts research-only and publication locked until admissible PIT data and chronological validation support promotion.
6. **Android:** configure `VELTRIX_API_BASE_URL` and perform a physical-device runtime test only after the live API has eligible real prediction records.

The isolated validation branch remains available for audit. Do not apply its schema changes to production merely because the branch test passed.
