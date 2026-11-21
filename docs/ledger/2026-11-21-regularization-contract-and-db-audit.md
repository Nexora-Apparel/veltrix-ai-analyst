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


## Additional model-artifact registry reconciliation

A direct SELECT of the two `model_artifacts` rows confirmed:

- `attack-defence-poisson-v1` and `attack-defence-poisson-v2-nested-tuned` are the only stored model artifacts.
- Both use the 380-fixture / 20-provider-team training fingerprint `5790da5427a7029b9267778728386b8df2cd583b922a421341dc586c8d03b839`.
- Both are explicitly `RESEARCH_ARTIFACT_ONLY` and `point_in_time_certified=false`.
- Neither represents `hierarchical-poisson-shadow-v1`, whose separate research run uses 996 training-only labels and 136 teams.

Therefore the new `model_versions` registry must not bind the current hierarchical shadow run to either legacy attack-defence artifact. The migration must create a distinct quarantined version record using the archived hierarchical artifact's verified config hash, training-data hash and report hash. The config hash must be computed from canonical archived configuration bytes and independently verified before any database migration.

No rows were inserted, updated, or deleted during this reconciliation.


## Final PR #139 head and controlling CI read-back

- PR #139 latest head is `edb41a13cbaeedd11eb143c311de5e12407b0da2` (six commits ahead of main, zero behind).
- Latest controlling CI run #44893501873 completed successfully:
  - Backend tests and lint: 504 passed; Ruff passed.
  - Android debug build: success; APK assembled and uploaded.
- This run supersedes #44893189043 because it includes the one-off audit workflow file added to PR #139.
- Vercel status remains failed with `build-rate-limit`; deployment lookup returned no preview deployment for the branch. Production remains on the previously verified deployment and the production API remains quarantined/empty.
- The one-off workflow run #44893869016 completed successfully. It downloaded forecast artifact 14694089682 from run #44873166128 and Stage 6 dataset artifact 14694463354 from run #44873016040, ran the exact repository CLI, verified `FIT_REPRODUCTION_VERIFIED` for 996 labels/136 teams/seven competitions, and uploaded report artifact 14703192024 (SHA-256 `4997f0b6a93c2fc02c1a164c2daff33e2dd532b8b50b57a35a41ec609e64fab0`). Full per-team ratios and information values are present in the 136-row JSON artifact. The repository CLI output matches the independent numerical reproduction.
- PR #139 remains open and unmerged. No production deployment, migration or database write was performed.


## Candidate fitter added to PR #139

- Added `backend/app/models/hierarchical_poisson_v2.py` on PR #139 head `940ae2f025e1feb1552bdda58cef5f73d028a0d0`.
- This is a separate research-only candidate. It uses the unnormalized weighted Poisson NLL plus explicit pseudo-match precision terms, competition-scoped team attack/defence, a competition scoring effect with 2μ information scale, and competition home deviations shrunk toward a global home effect with an explicit global prior.
- The fitter requires all k values as explicit arguments; no unvalidated production defaults are supplied. The current production/research fitter is untouched and remains quarantined.
- A synthetic candidate recovery test was added; current and excessive-prior rejection controls remain. Latest standard CI run #44893869028 is pending and has not yet exposed jobs. Do not claim the candidate test passes until that exact-head run completes.
- PR #139 metadata read-back returned open, unmerged, mergeable=true. Its Vercel preview deployment `dpl_H5UX1RbMTdMaDFNygvYUKqmZD9Gq` is READY on the feature branch. Production deployment and API are unchanged.


## Post-preview production verification

At 2026-11-21 10:23:43 UTC, after the PR #139 preview became READY:

- Production `GET /v1/research/predictions`: HTTP 200; `MODEL_QUARANTINED`, `NOT_PUBLISHED`, `predictions=[]`, production promotion LOCKED, value betting LOCKED.
- Production `GET /v1/predictions`: HTTP 200; `predictions=[]`.
- Production deployment remains `dpl_4qjTXEBsVXHxJ13Ap7fjX7Zmk8b4`, READY, main commit `95445c9b7aaba045f15a97afe443211da341a2fe`.
- PR #139 preview is `dpl_H5UX1RbMTdMaDFNygvYUKqmZD9Gq`, READY, branch commit `940ae2f025e1feb1552bdda58cef5f73d028a0d0`. This is preview-only and did not replace the production deployment.
- PR #139 metadata read-back: open, unmerged, mergeable=true. Its latest standard CI run #44893869028 is still pending and has not exposed jobs. The prior #44893501873 run passed 504 tests/Ruff/Android but predates the v2 candidate fitter; it is not sufficient to certify the latest head.
- No production DB writes, migrations, role changes, provider calls or Odds API credits were used.
