# Deferred manual database action — 2026-11-18

## Status
The protected production database migration action is intentionally deferred while prediction-model implementation and validation are completed.

## Manual action to resume later
- Workflow: `.github/workflows/apply-database-migrations.yml`
- Migration: `backend/migrations/010_system_observed_pit.sql`
- Required workflow_dispatch confirmation: `confirm_migrations=APPLY_CHECKSUM_VERIFIED_MIGRATIONS`
- Current production status recorded at deferral: migration 010 is **not applied**; migrations 001–009 were previously reported applied.
- Do not bypass the workflow confirmation gate or apply the SQL through an alternate route.

## Resume condition
Return to this action only after the prediction-model work is complete and reviewed. Before dispatching, inspect the current workflow definition, migration checksums, production migration ledger, and current database state. Confirm that the workflow still targets the intended production database and that the migration has not already been applied.

## Scope boundary
This is an operational reminder only. It does not authorize a migration, modify the database, or certify the new SYSTEM_OBSERVED_AT capture mode in production.
