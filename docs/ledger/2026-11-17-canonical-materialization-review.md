# Canonical materialization implementation and Migration 008 review — 2026-11-17

## Migration 007 actual application

- Controlled workflow [#44072112212](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44072112212), job `134000664117`, succeeded against the exact database `veltrix_ai_analyst`.
- Migration 007 was applied. SHA-256 `5503622ac57bd1875e08cf40cf1d87220cec99deb79e8fc23dd4ec6ebbffc30b` matched `public.schema_migrations`.
- Seven canonical tables, four functions and ten triggers were verified. Migration 006 checksum also re-verified.
- PR #14 merge commit: `759f2fa80b9c05551e278af7eb306760875a0063`.

## Production read-only scope audit

- Import run 3: `COMPLETED`; 34/34 date windows, 34 requests used of the 40-request cap, 374 records inserted, zero quarantines.
- Scoped canonical source rows: 374 fixtures, 21 team identities and one competition identity.
- Fixture states: 370 FINISHED with both goals; four UNKNOWN and scoreless.
- Exact fixture source observation/sighting/response provenance: 374/374 complete. Source approval `approval-5dollar-community-fixtures-2026-11-12` is APPROVED, covers competition `522514093`, and includes STORAGE and INTERNAL_ANALYSIS permitted uses.
- Scoped source observations: 396 total (374 fixtures + 21 teams + 1 competition); 0/396 PIT-certifiable.
- Canonical entity and identity-link tables were empty at the time of audit. No canonical rows have been inserted.

## Canonical materialization PR #15

- PR [#15](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/15) merged at `f7a73046be1b3ab0459815c636adfa202ba41e9f`.
- Final CI [#44075667064](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44075667064) passed on `42cd5c8b311d5c96c56e2cf733a74a6f6ae04dd4`: 113 backend tests passed, Ruff passed, Android debug build and APK artifact upload passed.
- Implementation is read-only by default. Explicit `execute=True` is required to write. It uses the exact run-3 response reservations and exact source observation/sighting/response/hash/rights evidence, plus transaction advisory locking and replay-drift checks.
- All identity links start `REVIEW_REQUIRED`; canonical entities are source-local placeholders; fixture completeness is `SOURCE_ROW_ONLY`. It creates no review events, makes no provider requests, and promotes no PIT observations.
- Known conflict pair: provider fixture IDs `3116209225` and `2341822348`, kickoff 2026-03-22 20:58:35Z and 21:00:00Z, both versus Goiás provider ID `3126624865`. The America provider IDs remain separate; both canonical fixture identities will be flagged `CONFLICT`.

## Defect discovered and Migration 008 correction

- First materializer CI run [#44074379638](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44074379638) failed in PostgreSQL integration testing with `record "new" has no field "canonical_fixture_id"`.
- Root cause: Migration 007's generic provenance trigger combined a trigger-table condition and fixture-only `NEW.canonical_fixture_id` reference in one boolean expression. PostgreSQL evaluated the record field on team-link insert rows, where it does not exist.
- Migration 008 now redefines `enforce_canonical_link_provenance()` with a nested `IF TG_TABLE_NAME = 'canonical_fixture_sources' THEN` block so fixture-only fields are referenced only for fixture-source rows.
- The same function now verifies exact observation data type per link class: `team_catalogue`, `competition_catalogue`, or `fixtures_and_results`.
- Migration 008 adds unique indexes for `(provider, source_id, provider_team_id)` and `(provider, source_id, provider_competition_id)` to enforce one source-local identity link per provider identity.
- The controlled migration workflow now verifies Migration 008's function and both indexes.
- CI after correction [#44075667064](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44075667064) passed, including the integration test that inserts team, competition and fixture links and verifies idempotent replay.

## Remaining blocker and next action

- Migration 008 is **not applied to Neon**. The only permitted route is the manual workflow [Apply checksum-verified database migrations](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/apply-database-migrations.yml), with `confirm_migrations=APPLY_CHECKSUM_VERIFIED_MIGRATIONS`.
- The current GitHub integration does not expose workflow dispatch. Manual dispatch is required; do not bypass the workflow by running SQL directly.
- After Migration 008 succeeds, verify its exact SHA-256, the replacement function and both unique indexes. Then run the production planner in read-only mode and inspect its report. Only after a clean report should a separately controlled production materialization be executed.
- No production canonical materialization, provider HTTP requests, PIT promotion, model training or prediction publication occurred during this work.

