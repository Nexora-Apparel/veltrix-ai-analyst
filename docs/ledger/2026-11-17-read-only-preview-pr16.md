# Read-only canonical materialization preview workflow — 2026-11-17

## PR #16 merged

- PR [#16](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/16), "Add read-only production canonical materialization preview", merged into `main`.
- Squash merge commit: `7cf34b5f0541667b2ebcd2ddaabff13cfc738a6c`.
- Head commit validated: `d1ebe60997e2023681de3b8f826ebd1f39b84971`.
- CI run [#44080635104](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44080635104) passed:
  - Android debug build.
  - Backend tests.
  - Ruff lint, including `scripts/preview_canonical_materialization.py`.

## Patch safety review

- Workflow is manual-only (`workflow_dispatch`) and requires explicit choice `PREVIEW_BRAZIL_SERIE_B_RUN_3`; default is `NO`.
- Uses the GitHub Actions environment `veltrix-historical-import`, secret `VELTRIX_AI_ANALYST_DATABASE_URL`, and expected DB name `veltrix_ai_analyst`.
- Runner rejects a missing URL, wrong expected DB setting, or actual database-name mismatch.
- PostgreSQL read-only mode is enforced at connection startup (`default_transaction_read_only=on`) and transaction level (`SET TRANSACTION READ ONLY`).
- Runner calls only `build_brazil_serie_b_materialization_plan`; it does not invoke `materialize_brazil_serie_b_canonical_entities` or pass `execute=True`.
- Planner implementation inspected: candidate loading and plan construction use SELECT queries; the write path is a separate function.
- Workflow has read-only contents permission, concurrency protection, and a ten-minute timeout.
- No provider HTTP calls, canonical writes, identity review events, or PIT promotions are part of this preview.

## Current production state

- Migration 008 is applied and independently verified; checksum:
  `bbd3276a85d7e6d9c8293379b173b15753fb96c3f2877c6488229f5a011c8130`.
- Live Neon checks confirmed the migration record, corrected provenance function, and both source-identity unique indexes.
- All seven canonical tables remain empty. No canonical materialization has been executed.
- Source scope remains Brazil Serie B, 5DollarFootballAPI competition `522514093`, import run 3: 374 fixtures, 21 teams, one competition; four fixtures remain UNKNOWN and scoreless.
- All 396 scoped source observations remain non-PIT-certifiable. Canonical materialization, if later approved, will preserve them as source-row-only records; it will not make them eligible as pre-match features.

## Required next action

A human must manually dispatch the merged workflow:

[Preview canonical materialization](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/preview-canonical-materialization.yml)

Select **Run workflow** and set `confirm_preview=PREVIEW_BRAZIL_SERIE_B_RUN_3`.

The workflow dispatch is not exposed by the connected GitHub actions, so it cannot be launched from this session. This is a manual UI blocker only; no credentials or SQL need to be supplied in chat.

After the run completes:
1. Inspect the JSON plan and full job logs.
2. Confirm team, competition and fixture counts reconcile with 21, 1 and 374 respectively; provenance-complete counts match; four UNKNOWN fixtures remain scoreless; the two known collision fixtures remain explicitly conflicted.
3. Review every blocker and the reported non-PIT count. A ready plan is permission to consider a separate materialization operation, not authorization to train models or promote PIT evidence.
4. If blocked, fix the underlying evidence or code and repeat the read-only preview. Do not call the writer or insert canonical rows until the preview has been reviewed and the separate controlled write path is validated.

## Safety conclusion

PR #16 is merged and CI-verified. The read-only production preview is implemented but has **not yet been run**. Canonical tables remain empty; no production materialization, model training, prediction API, or prediction publication has occurred.

## Production preview execution — successful, 2026-11-17

- Manual workflow run [#44085484843](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44085484843), job `134046688821`, completed with conclusion `success`.
- The runner checked out main commit `ab0dc0a50af6cbde66431ad7e872c2e4e8b8f41a` and connected to the expected dedicated database `veltrix_ai_analyst`.
- Planner emitted `CANONICAL_MATERIALIZATION_PLAN_READY`, `ready=true`, and an empty blockers list.
- Exact report: provider `5DollarFootballAPI`; source `5dollarfootballapi`; competition `522514093`; import run 3; competition count 1; team count 21; fixture count 374.
- Provenance-complete counts: 1/1 competitions, 21/21 teams, 374/374 fixtures.
- Fixture states: 370 finished, four unknown. Conflict fixture IDs: `2341822348`, `3116209225`.
- Non-PIT observation count: 396. This remains a hard model-feature eligibility boundary; preview readiness does not certify publication/availability timestamps or authorize pre-match feature use.
- Independent post-run read-only Neon query confirmed all seven canonical tables still contain zero rows:
  - `canonical_teams`: 0
  - `canonical_competitions`: 0
  - `canonical_fixtures`: 0
  - `provider_team_identity_links`: 0
  - `provider_competition_identity_links`: 0
  - `canonical_fixture_sources`: 0
  - `canonical_identity_review_events`: 0
- No provider requests, canonical writes, identity reviews, PIT promotions, model training or prediction publication occurred.
- **Decision:** read-only plan passes structural/provenance readiness. Proceed to a separate controlled materialization implementation/review stage. Production writer must remain manual-only, default-deny, database-identity-checked, transactional, idempotent and auditable. Do not dispatch it automatically as a consequence of preview success.
