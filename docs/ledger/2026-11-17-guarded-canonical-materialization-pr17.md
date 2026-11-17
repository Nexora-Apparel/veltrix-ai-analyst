# Guarded first-run canonical materialization — PR #17 — 2026-11-17

## Preview evidence authorizing implementation of the write path

- Production read-only preview [#44085484843](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44085484843), job `134046688821`, completed successfully.
- Planner returned `ready=true`, zero blockers, 1 competition, 21 teams, 374 fixtures, 370 FINISHED, four UNKNOWN, 21/21 team provenance, 1/1 competition provenance and 374/374 fixture provenance.
- Conflict fixtures remain `2341822348` and `3116209225`.
- Non-PIT observation count remains 396; this is not feature-eligible evidence.
- Independent read-only Neon verification after the preview confirmed all seven canonical target tables had zero rows.

## PR #17 implementation

- PR [#17](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/17) merged by squash at `60e24970c2dd847773d685ba903238e99c5c3da8`.
- Validated head: `8d8da012bd705a0f42f7c844a671c72560c59a70`.
- CI run [#44086260165](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44086260165) passed:
  - Backend test suite.
  - Ruff lint, including the materialization runner.
  - Android debug build and APK artifact upload.
- Added `backend/scripts/materialize_canonical_entities.py` and manual workflow `.github/workflows/materialize-canonical-entities.yml`.
- Workflow defaults to `NO`, requires `MATERIALIZE_BRAZIL_SERIE_B_RUN_3`, uses only the dedicated `veltrix-historical-import` environment secret, checks actual database name, and is protected by a concurrency group.
- Runner re-builds the plan against live production data and fails closed unless exact scope/counts/conflict IDs and the 396 non-PIT count match the reviewed preview.
- The plan, empty-target check, write and post-write reconciliation run in one SERIALIZABLE transaction. Lock timeout is 15 seconds; statement timeout is 180 seconds.
- First-run-only guard requires all seven canonical target tables to be empty. This intentionally prevents accidental second execution.
- The runner invokes the existing materializer with `execute=True`; verifies exact counts before commit: 21 canonical teams, 1 competition, 374 fixtures, 21 team links, 1 competition link, 374 fixture-source links, zero identity-review events.
- The runner also asserts zero identity reviews, zero PIT promotions and zero provider requests. Existing materializer semantics retain source-local identity, `REVIEW_REQUIRED` links, `SOURCE_ROW_ONLY` fixtures and explicit collision flags.
- Any failed assertion inside the transaction raises and rolls back all writes.

## Current production state and next action

- PR merge did not execute the workflow.
- All seven canonical tables were last independently verified empty immediately after the preview. No production materialization has yet been run.
- The manual write workflow is now available:
  [Materialize canonical entities](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/materialize-canonical-entities.yml)
- Dispatch requires selecting branch `main` and `confirm_materialization=MATERIALIZE_BRAZIL_SERIE_B_RUN_3`. This is an irreversible production data write (though transactionally atomic); the GitHub integration in this session does not expose workflow dispatch. A repository user must launch it manually.
- Do not launch until the user explicitly chooses to execute the production write. Do not paste database credentials or SQL into chat.
- After the workflow runs, inspect its JSON report and independently verify all seven live table counts. If successful, preserve the report and counts in this ledger and progress register.
- Canonical materialization does not certify PIT eligibility. The 396 observations remain excluded from pre-match feature engineering and model training until valid source publication/availability evidence and rights review are established.
