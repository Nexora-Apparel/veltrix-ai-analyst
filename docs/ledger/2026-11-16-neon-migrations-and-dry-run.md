# Neon migration and dry-run evidence — 2026-11-16

## Database
- Vercel project: `veltrix-ai-analyst`.
- Neon resource: `young-wind-27772160`.
- Dedicated database: `veltrix_ai_analyst`, PostgreSQL 18.7.
- `current_database()` was verified before schema work. The separate `neondb` database was not used.

## Migrations
Migrations 001–003 were applied in order through the authenticated Neon SQL connector. SHA-256 checksums were computed from the repository migration files and verified against `public.schema_migrations`:

| Migration | SHA-256 |
|---|---|
| `001_provenance_ingestion.sql` | `11516fc36e78cca9d0a47f677e2ab451fc1beb6b899d74f9f007b979c98ebf07` |
| `002_source_observation_sightings.sql` | `a5389d81f7816837c0dfedd35784f8834c4484c13a946ea166dd6d55615c4285` |
| `003_import_request_reservations.sql` | `fa841cf34fe836f3d7d7251edd36e4d5e619d185f6adf4585ac851ebcdc0560e` |

The repository Python migration runner was not executed: Vercel CLI environment pull substituted `[SENSITIVE]` for the sensitive `DATABASE_URL`. No credential was exposed or substituted.

## Source approval
Registered the repository's reviewed 5Dollar Community approval for the documented competition/data scope, non-commercial use, attribution requirement and no raw redistribution.

## Neon-backed dry-run
No provider HTTP requests were made.

- Rehearsal run 1 was marked FAILED after detecting that its idempotency keys included milliseconds not emitted by the provider adapter.
- Corrected rehearsal run 2 used the adapter's exact ISO-8601 key format.
- Candidate interval: `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`.
- 34 contiguous seven-day checkpoints were created and recovered.
- 40 reservations were recorded: 34 first pages plus six second pages.
- Request 41 produced no reservation.
- A repeated page key resolved to its existing reservation.
- Run 2 was finalized PAUSED with `DRY_RUN_ONLY_NO_PROVIDER_HTTP`.
- No fixture rows were imported.

The CI suite separately validates the Python reservation service, concurrency, idempotency conflict behaviour and provider HTTP gate.

## Remaining gate
Live collection remains blocked until the resumable importer/orchestrator is implemented and the dedicated database connection is securely configured for its GitHub Actions runner. Do not reuse the integration-generated URL variables without verifying the database path: they currently target `neondb`, not `veltrix_ai_analyst`. Do not expose credentials or raise the 40-request ceiling.

## Impact
- 5Dollar historical API calls: 0.
- Odds calls: 0.
- Fixture rows imported: 0.
- Model training/predictions: none.
