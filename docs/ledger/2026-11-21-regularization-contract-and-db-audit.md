# 2026-11-21 — Regularization contract tests and database admission audit

## PR #139 implementation

- PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/139
- Branch: `research/regularization-contract-tests`
- Latest branch head: `6ac289436af299887143ed124ed10e5e9ab40413`.
- PR remains open and unmerged.
- Changes:
  - `docs/ML_REGULARIZATION_CONTRACT.md`: unnormalized weighted Poisson NLL plus explicit pseudo-match priors; team attack/defence use one shared k; competition effect uses two-goal information scale; per-competition home effects shrink toward a global home effect with explicit global prior; numeric k values remain untuned and unapproved.
  - `backend/app/models/regularization_contract.py`: common pseudo-match precision helper.
  - `backend/tests/test_regularization_contract.py`: verifies team scale, 2μ competition scale, competition/global home priors and fail-closed invalid inputs.
  - `backend/tests/test_hierarchical_poisson_recovery.py`: deterministic synthetic known-strength data; verifies the current quarantined configuration is rejected by recovery/shrinkage gates and an excessive-prior negative control is also rejected.
- No model-fitting code, inference, schedules, APIs, database, Android UI, or release status changed.

## CI

Latest controlling workflow run #44893189043 on head `6ac289436af299887143ed124ed10e5e9ab40413`:
- Backend tests and lint: success; 504 tests passed; Ruff passed.
- Android debug build: success; debug APK assembled and uploaded.
- Earlier run #44893057532 was cancelled when the synthetic test was revised to remove an unnecessarily expensive near-unpenalized reference fit. It is not the controlling run.
- Vercel preview deployment lookup returned no deployment for this branch. Production deployment remains the previously verified READY deployment at `dpl_4qjTXEBsVXHxJ13Ap7fjX7Zmk8b4`, commit `95445c9b7aaba045f15a97afe443211da341a2fe`. No deployment was promoted or created by this work.

## Production database read-only audit

Project `young-wind-27772160`, branch `br-jolly-darkness-balgmi2t`, database `veltrix_ai_analyst`. Queries were SELECT-only; no database writes or migrations were run.

- The domain tables are under schema `veltrix_ai_analyst`, not `public`.
- `predictions`: 0 rows.
- `research_shadow_forecast_runs`: 1 row.
- `model_artifacts`: 2 rows.
- The one research run is `SHADOW_FORECASTS_READY`, training_fixture_count=996, model_version=`hierarchical-poisson-shadow-v1`, report_sha256=`e34d6e3459301cbfc8692d90691b0b48572166f338cefd484c2def8850c60d93`, forecast_count=25, abstention_count=0.
- `research_shadow_forecast_runs.model_version` is nullable. There is no `model_versions` table in the current schema and no FK from the research run to a model-version registry. `report_sha256` is NOT NULL and has a format check, but it is not bound to an admitted model-version row.
- `research_shadow_forecast_runs` has append-only UPDATE/DELETE rejection triggers but no INSERT admission trigger.
- `predictions` has an FK to `model_artifacts` and a pre-match inference INSERT trigger; it has no admission-status validation or read-time model-admission join in the current schema.
- Table grants show direct INSERT on both forecast tables for `neondb_owner`; no dedicated application role with the requested restricted-write/controlled-function boundary is present in the visible grants. Current non-system roles are cloud_admin, neon_service, neon_superuser, neondb_owner and token_roles.
- These findings confirm the supervisor's concern: the current database schema does not yet implement the required two-tier model-version admission boundary. Do not use the existing tables as proof of admission enforcement.

## Production API read-back

At 2026-11-21 10:13:40 UTC:
- `GET /v1/research/predictions`: HTTP 200; `MODEL_QUARANTINED`; `NOT_PUBLISHED`; zero predictions; production promotion and value betting locked.
- `GET /v1/predictions`: HTTP 200; zero predictions.
- Production API remained on deployment commit `95445c9b7aaba045f15a97afe443211da341a2fe`; no PR #139 code was deployed.

## Current conclusions

- The current configuration rejection and excessive-prior negative control pass as explicit fail-closed tests. The CI suite passes because it verifies that these candidates are rejected; it does not admit them.
- The helper computes scales but is not yet wired into a replacement fitter. The existing quarantined fitter remains unchanged.
- No numeric k values, admission thresholds, MDE, or power cutoffs have been selected or frozen.
- SHADOW/PUBLISHED admission, model_versions, hash immutability, DB role separation, controlled writes, admission-aware API joins and evaluation-run logging remain unimplemented.
- 5Dollar Community history is limited to 12 months; no historical backfill or provider request was made. The 28 unresolved identity/reconciliation cases remain a hard precondition to cross-season identity stitching.

## Next steps

1. Implement the candidate fitter using the unnormalized objective and the tested scales; add a passing synthetic recovery configuration without changing the quarantined production model.
2. Extend synthetic tests to assert the corrected candidate passes, sparse teams shrink appropriately, home deviations shrink toward global, and promotion/relegation identity boundaries abstain.
3. Build the independent 1X2 log-loss evaluator, MDE/power calculation, tuned team-aware baseline, league climatology baseline, date-block bootstrap and immutable evaluation-run ledger.
4. Draft thresholds and send them for explicit user approval before freezing any threshold hash.
5. Design and implement model_versions plus SHADOW/PUBLISHED admission, immutable hashes, controlled DB writes, restricted application role, append-only audit events, and read-time API admission joins.
6. Resolve or explicitly quarantine the 28 identity cases before season backfill. Community history is limited to 12 months; do not buy or upgrade.

## Release state

Model remains QUARANTINED. No production forecasts. Value betting LOCKED. Android UI preserved. No DB writes, provider calls, Odds API credits, or production deployment.
