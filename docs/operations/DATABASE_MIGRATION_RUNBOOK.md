# Applying database migrations

The production migration path is the checksum-verified runner in
`backend/app/db/migrations.py`. Do not execute migration SQL manually and do not
set `ALLOW_REMOTE_MIGRATIONS` globally.

## Controlled production run

1. Merge the migration workflow to `main`.
2. Open **Actions → Apply checksum-verified database migrations → Run workflow**.
3. Select the default branch and enter `APPLY_CHECKSUM_VERIFIED_MIGRATIONS`.
4. Confirm the run uses the `veltrix-historical-import` environment and its
   `VELTRIX_AI_ANALYST_DATABASE_URL` secret. The workflow pins the expected DB
   name to `veltrix_ai_analyst`; it does not call any football provider.
5. The runner applies pending SQL files in lexical order, validates existing
   checksums, rejects checksum drift, and enables remote writes only for that
   one invocation.
6. The final workflow step verifies the exact SHA-256 recorded for migration 006,
   the PIT feature table, trigger function, and both table triggers.

The workflow is schema-only. It does not import data, backfill observations,
change PIT flags, create features, train models, or publish predictions.

## Expected migration 006 result

- `006_pre_match_feature_pit_gate.sql` exists in `public.schema_migrations`
  with the exact file SHA-256.
- `veltrix_ai_analyst.pre_match_feature_observations` exists.
- `veltrix_ai_analyst.enforce_pre_match_feature_pit()` exists.
- Both `pre_match_feature_pit_guard` and
  `pre_match_feature_observations_append_only` triggers exist.
- Existing retrieval-only 5Dollar observations remain ineligible.
