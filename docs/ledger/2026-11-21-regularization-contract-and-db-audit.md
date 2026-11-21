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


## Candidate optimizer failure and corrective validation

- Standard CI run #44893869028 on PR head `940ae2f025e1feb1552bdda58cef5f73d028a0d0`:
  - Backend: 504 tests passed, one failed. The new v2 synthetic recovery test failed because the optimizer's backtracking line search stopped before meeting its gradient tolerance.
  - Android debug build: success; APK assembled and uploaded.
  - Ruff was skipped because the backend test step failed.
- This failure is retained as evidence; the candidate was not treated as admitted or successful.
- Corrective commit `3c07aacb8fdc1dfd4832d1779d91ac4eaed98963` raises the research candidate's numerical optimizer tolerance from 1e-7 to 1e-6 and adds iteration/gradient-norm diagnostics to the line-search failure. This is an optimizer convergence setting only; no admission threshold or market gate was relaxed.
- Latest CI run #44894364730 is running on that correction commit. Its result is pending. Do not merge PR #139 until the candidate recovery test, all backend tests/lint and Android build pass on the exact current head.
- No new Vercel deployment was found for commit 3c07; the existing preview remains READY at commit 940ae2f. Production deployment remains unchanged.


## Effective shrinkage report — independently read back (2026-11-21)

Successful archived audit:
- Workflow #44893869016, job 136815242522: success.
- Artifact #14703192024, SHA-256 `4997f0b6a93c2fc02c1a164c2daff33e2dd532b8b50b57a35a41ec609e64fab0`.
- The report was downloaded and parsed independently from the GitHub artifact ZIP.
- `FIT_REPRODUCTION_VERIFIED`; 996 training fixtures, 136 teams, 7 competitions.
- Effective runtime: team_ridge=0.5; competition_ridge=0.5; half_life_days=365; total recency weight=868.581121480181; summed-objective team tau=434.2905607400905.
- Median signed attack ratio=3.0065%; median absolute attack ratio=3.1104%.
- Median signed defence ratio=3.2777%; median absolute defence ratio=3.3939%.
- Median attack tau/data information=30.5764x (P10–P90 11.4254x–34.4268x).
- Median defence tau/data information=30.3068x (P10–P90 11.4785x–34.4259x).
- Attack sign agreement with near-unpenalized estimates=90.44%; defence=91.18%.
- These are per-team retrospective fit diagnostics. They do not demonstrate out-of-sample quality and do not select new k values.

## 5DollarFootballAPI Community terms and backfill ceiling

Checked the current public Community page, Terms of Service, and fixture endpoint documentation (21 Nov 2026):
- Community Access is $0 and provides the top-five leagues plus one country pack, the last 12 months of results and odds, 300 requests/hour, and a 20 requests/minute burst ceiling.
- The Community entitlement is renewable every 12 months. It does not grant the full 130+ league catalogue or bulk odds for a whole fixture list in one call.
- The API terms allow use in commercial products and caching. Public-facing products on the $0 plan must visibly attribute/link “Football data by 5DollarFootballAPI”. Raw-data redistribution as a competing feed is prohibited.
- No plan purchase, account change, provider API call, or Odds API call was made.
- The 12-month history window cannot support unrestricted multi-season historical backfill. It can cover only the most recent 12 months, subject to competition-pack scope and actual per-league availability. No older season is to be fabricated or inferred.

Sources:
- https://5dollarfootballapi.com/community
- https://5dollarfootballapi.com/terms
- https://5dollarfootballapi.com/docs/fixtures
- https://5dollarfootballapi.com/docs

## Current identity reconciliation read-back

Read-only production DB snapshot:
- `effective_canonical_identity_review_cases`: 28 cases have effective status `AUTOMATED_CONFIRMED`; one additional case is `AUTOMATED_DEFERRED` (PIT timestamp gap).
- The 28 confirmed cases comprise 20 team real-world identity candidates, 1 team alias candidate, 5 fixture duplicate candidates, 1 competition identity candidate and 1 season-coverage reconciliation.
- The 20 team real-world identity cases use policy `cbf-2026-identity-adjudication-v1`, confidence 0.995, and decision basis `CBF_380_FIXTURE_GRAPH_19_HOME_19_AWAY_MATCHED`. The notes state the complete ordered fixture graph matches the official CBF 2026 Série B schedule; this confirms the real-world crosswalk, not alias merging or provider-label rewriting.
- `effective_provider_team_identity_links`: 20 `REAL_WORLD_IDENTITY_VERIFIED`, 116 `SOURCE_IDENTITY_REVIEWED`, and 1 `CONFLICT`.
- The conflict is provider team ID `3808811746`, labelled América Mineiro, link ID 16. Its provenance audit says `PROVENANCE_VERIFIED` but `real_world_identity_status='CONFLICT'`; it has no direct evidence URI/hash. Keep this identity link excluded from any cross-season stitching until separately adjudicated.
- The 116 `SOURCE_IDENTITY_REVIEWED` links must not be promoted to real-world cross-season identity merely because source provenance is reviewed.
- Therefore the remembered count of 28 unresolved review cases is no longer an accurate description of the current effective review view: 28 are automated-confirmed under their recorded policies. However, one provider identity conflict remains, and broad cross-season stitching is still not authorized.
- Model team keys remain competition-scoped. Do not join teams across seasons by display name. Newly promoted/unseen competition-scoped teams abstain unless a separate pre-registered prior and verified identity path are admitted.

No DB rows were changed by these queries.
