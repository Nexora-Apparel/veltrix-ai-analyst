# 2026-11-21 — Android research forecast delivery repair

## Findings
- The installed Android client is configured to call `https://veltrix-ai-analyst-api.vercel.app/v1/research/predictions`.
- Vercel project `veltrix-ai-analyst-api` had SSO protection set to `all_except_custom_domains`. Its only attached domain is the Vercel-managed `veltrix-ai-analyst-api.vercel.app`, not a custom domain; therefore the installed app's API host was inside the protected scope.
- Vercel project SSO protection was changed to `preview`. Read-back verified `ssoProtection.enabled=true`, `deploymentType=preview`; Production API host is intended to be publicly reachable while Preview deployments remain protected.
- The research endpoint SQL also expired reports after six hours. Daily capture/inference is generated around 06:00 WAT, so that cutoff could hide still-upcoming fixtures later on matchday. This is independent of the SSO access problem.

## Code repair
- PR #130: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/130
- Branch: `fix/android-research-prediction-delivery`
- Changes: increase research report maximum age from 6 to 36 hours; preserve upcoming-kickoff, research-only, NOT_PUBLISHED, production-promotion LOCKED and value-betting LOCKED predicates; add regression test for the 36-hour window.
- No model, capture, provider, Odds API, production publication, settlement or certification logic changed.
- Existing Android APK already points to the production API hostname; the SSO configuration repair does not require an APK rebuild by itself.

## Verification boundary
- Vercel project setting update succeeded and was read back.
- The latest production deployment remained READY on main commit `de34c8c05d563f465e8784a5c7a5050d6b016c53`.
- The direct API response could not be independently fetched through the available external page fetch; Vercel runtime logs showed no API requests in the 15-minute observation window. Do not claim endpoint response or physical app display verified.
- PR #130 is open. Vercel preview deployment was reported READY; GitHub Actions CI had not yet reported a completed run at this checkpoint.
- The production API currently still runs the six-hour SQL guard until PR #130 is merged and deployed. Therefore the access-protection repair is applied, while the full-day freshness repair awaits CI/merge/deployment.

## Next steps
1. Wait for and verify backend tests/lint and Android debug build on PR #130.
2. Merge only after required checks pass; confirm production deployment READY on the merge commit.
3. Verify live `GET /v1/research/predictions` HTTP response and payload count.
4. Have the user force-close/reopen the installed app and refresh; no APK replacement should be needed for the project-level SSO change or backend SQL-only change.
5. If the app still shows no forecasts, capture Android Logcat entries for tag `VeltrixPredictions` and correlate request paths/status with Vercel runtime logs.
6. Keep all research forecasts unpublished; production promotion, certification and value betting remain locked.

## Follow-up verification — 2026-11-21 08:00 WAT
- PR #130 merged successfully by squash merge as commit `bf6986d03d3687f36dbd7e84de7adb148e93c64d`.
- Required CI run #44882438326 completed successfully. Both jobs passed: backend tests and lint; Android debug APK build and artifact upload.
- Vercel production deployment was created for the merge commit and was still in `BUILDING` state at the last read-back. Do not claim production deployment ready until a subsequent deployment status check confirms it.
- Existing automatic daily chain verified in repository workflow definitions:
  - `prospective-5dollar-daily-capture.yml` runs daily at 03:00 UTC (04:00 WAT), capturing yesterday's settlements plus a rolling seven-day forward fixture window. It is limited to four provider requests per run.
  - Successful capture triggers Stage 6 daily snapshot/outcome materialization.
  - Successful Stage 6 completion triggers `prospective-shadow-predictions.yml`; that workflow also has a daily 05:00 UTC (06:00 WAT) schedule and manual dispatch. It generates up to 25 research forecasts and persists them only to the isolated research ledger.
  - Stage 7 evaluation follows Stage 6; certification gates remain closed unless independent criteria are actually met.
- This means tomorrow's upcoming fixtures are intended to be included automatically: the seven-day capture window covers them, then the daily shadow run refreshes the next forecast set. The 36-hour API freshness change prevents the newly generated report from expiring after six hours.
- The inference workflow's max snapshot age remains six hours; this is an input-quality guard, not the API response expiry. Do not widen it without evidence that it blocks valid snapshots.
- The inference workflow can be triggered both by Stage 6 completion and its daily cron. Its concurrency group prevents overlap but does not necessarily eliminate sequential duplicate runs; inspect tomorrow's run history for this behavior before changing it.
- Verification still outstanding: production deployment readiness; live unauthenticated production endpoint response; Android screen display after app restart. No provider/Odds API credits were spent by this repair.
- Safety unchanged: research forecasts remain unpublished; production promotion and value betting remain LOCKED.
- Final production deployment read-back: deployment `dpl_AAya7HfvdnabnZfZnwPpHtRFALsn` reached `READY` on production alias `veltrix-ai-analyst-api.vercel.app`, commit `bf6986d03d3687f36dbd7e84de7adb148e93c64d`.
- Attempted direct external GET of `/v1/research/predictions`; the available page-fetch path returned an internal access error. Vercel runtime logs for the deployment showed no requests in the 30-minute window. Therefore HTTP status/payload and physical Android rendering remain unverified.

## Android feed diagnostics — 2026-11-21
- PR #131 merged: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/131
- Squash merge commit: `841d4e9864a49b76a98a10b420b5e1eea78b0ce5`.
- Android research feed now returns a structured result separating a successful empty forecast list from request failure.
- Failure diagnostics preserve cancellation semantics and report safe detail for missing API base URL, HTTP status, empty response, malformed payload/URL, and transport exceptions. Successful responses log the loaded forecast count using the `VeltrixPredictions` tag.
- Existing Home, BTTS, and Over/Under screens show a compact research-feed warning when the research request fails. Existing visual design and prediction merge/deduplication logic are unchanged.
- Research payload validation remains strict: `research_only=true`, `publication_status=NOT_PUBLISHED`, production promotion `LOCKED`, and value betting `LOCKED`.
- CI run #44883387460 passed on PR head `f96932e0b982315d26d94a7fff75adf9cb3e0512`: backend tests/lint and Android debug build both succeeded.
- Debug APK artifact #14698089512 (`veltrix-ai-analyst-debug-apk`) uploaded successfully; size 16,461,003 bytes. This is the diagnostic build and should be installed to expose the new in-app warning and Logcat evidence.
- Post-merge CI run #44883524472 was queued at ledger update time; do not claim post-merge CI success until verified.
- This PR changed Android client diagnostics only. No backend routes, model, training data, provider calls, Odds API credits, schedules, production publication, settlement, or certification gates were changed.
- Outstanding: install and physically verify this APK on the user's device; then correlate any displayed HTTP/network error with production endpoint/runtime evidence. Public endpoint response and actual Android rendering remain unverified.

## Research feed HTTP 503 diagnosis and repair — 2026-11-21
- User reported the Android app displays `research feed HTTP 503`.
- Verified post-merge GitHub Actions run #44883524472 completed successfully: backend tests/lint and Android debug build both passed.
- Confirmed latest Vercel production deployment is READY on main commit `3c726e342fa339efe83575a72391dc2eceac94b2`, aliased to `veltrix-ai-analyst-api.vercel.app`.
- Read-only Neon verification confirmed the latest research run exists: 25 forecast rows, 996 training fixtures, status `SHADOW_FORECASTS_READY`.
- Reproduced the endpoint SQL failure against the production Neon database. The `latest_run` CTE selected run_key, generated_at, training_fixture_count, model_version and report, but omitted `status`; the outer WHERE clause referenced `latest_run.status`. PostgreSQL raises SQLSTATE 42703 (undefined column), which the route converts to HTTP 503.
- This is a backend query defect, not missing forecasts, Android parsing, or an empty feed. No database writes, provider calls, Odds API credits, or publication changes were made.
- Repair branch `fix/research-feed-http-503`: include `status` in the CTE projection and add a regression assertion that the selected CTE columns include status before filtering.
- All research-only, NOT_PUBLISHED, production-promotion LOCKED, value-betting LOCKED, release_eligible=false and 36-hour freshness gates remain unchanged.

## PR #132 production verification — 2026-11-21
- PR #132 merged after both required CI jobs passed. Squash merge commit: `0c0628bcc2f419b6baf488179cf327059c0160e5`.
- Vercel production deployment `dpl_3uE7ahucYiB9AiqX35pkisoXxws6` reached `READY` on `main` with the exact merge commit; production alias includes `veltrix-ai-analyst-api.vercel.app`.
- Performed an actual unauthenticated HTTPS GET from an isolated Vercel sandbox to `https://veltrix-ai-analyst-api.vercel.app/v1/research/predictions`.
- Observed HTTP 200 and `Content-Type: application/json`. Response status `SHADOW_FORECASTS_READY`; 25 predictions returned; `research_only=true`; `publication_status=NOT_PUBLISHED`; `production_promotion=LOCKED`; `value_betting=LOCKED`; generated_at `2026-11-21T05:59:20.681143+00:00`.
- This verifies the live production API query repair and confirms the existing 25-row research report is readable through the public production hostname. No provider calls, Odds API credits, or database writes were made for the HTTP check.
- The sample forecast in the response was Man City vs Fulham, kickoff `2026-11-21T12:30:00Z`; sample only, not a production-published prediction.
- Android physical display remains unverified until the user refreshes the installed diagnostic APK. Because PR #132 is backend-only, no APK reinstall is required for this SQL correction; force-close/reopen or refresh the existing diagnostic app.
- Research predictions remain isolated and unpublished; production promotion and value betting remain locked. Certification criteria were not changed or waived.

## Published-feed isolation check — 2026-11-21
- Performed live unauthenticated GETs to both production endpoints from the same isolated Vercel sandbox.
- `GET /v1/predictions`: HTTP 200, zero published prediction rows. This confirms the 25 research forecasts are not being exposed through the production-only feed.
- `GET /v1/research/predictions`: HTTP 200, 25 research rows; `SHADOW_FORECASTS_READY`, `research_only=true`, `NOT_PUBLISHED`, production promotion `LOCKED`, value betting `LOCKED`.
- This is a read-only HTTP verification. No odds-provider calls, Odds API credits, or database writes were used.


## Android device confirmation — 2026-11-21
- User confirmed the research forecasts are visible in the Android app after the production API repair.
- This closes the previously outstanding physical display check for the current research feed. The confirmation is user-observed; no independent screenshot or device telemetry was supplied.
- Combined with the live production GET verification (HTTP 200, 25 research rows) and the published-feed isolation check (HTTP 200, zero published rows), this confirms the repaired backend delivery path and user-visible Android rendering.
- Research rows remain NOT_PUBLISHED; production promotion and value betting remain LOCKED. This device confirmation is not model-performance certification.
- Next: inspect scheduled prospective capture, Stage 6, shadow inference and Stage 7 runs; identify any sequential duplicate inference caused by both Stage 6 completion and the 06:00 WAT cron. Do not alter schedules until actual run history is verified.


## Prospective pipeline verification — 2026-11-21
- Inspected GitHub Actions run history and job logs for capture, Stage 6, shadow inference and Stage 7. All four runs in the 21 Nov chain completed successfully:
  - Capture #44872062807 (run 4, event `workflow_dispatch`, not `schedule`): six approved competitions validated; 18 records inserted; 12 provider requests total (two per competition); no Odds API calls. France Ligue 1 remained excluded because its mapping/identity issue was unresolved.
  - Stage 6 #44873016040: `DAILY_MATERIALIZATION_VERIFIED`; 54 snapshots across 54 distinct fixtures; zero latest label events; dataset SHA-256 `80148b3f0f42e70d94391d9283c42f35b5b92e1631a9a1cb7baee899373dad0c`.
  - Shadow inference #44873166128 (event `workflow_run`, after Stage 6): `SHADOW_FORECASTS_READY`; 25 forecasts; 996 training fixtures; zero abstentions; zero provider calls and zero database writes in inference; production promotion and value betting both LOCKED.
  - Stage 7 #44873166148: `INSUFFICIENT_PROSPECTIVE_DATA`; zero settled labels, zero evaluated fixtures, zero distinct settled-label dates and zero walk-forward fixtures in every market; production certification BLOCKED, promotion/value betting LOCKED.
- The recent Actions run listing contained one shadow inference run for this chain, triggered by successful Stage 6 completion. No sequential duplicate inference run was observed in the inspected run history. The 06:00 WAT cron path was not independently observed as a second run; do not infer its behavior beyond this history.
- Important schedule distinction: the 21 Nov capture run was manually dispatched at 05:41 UTC, not triggered by the 04:00 WAT schedule. The preceding scheduled capture run #44725750217 (20 Nov) failed its validation stage: multiple competitions reported fixture-sighting/import-counter reconciliation mismatches and France Ligue 1 reported `PROVIDER_FIXTURE_IDENTITY_CONFLICT`. The successful 21 Nov manual run validated six competitions and is not evidence that the cron itself fired successfully.
- No schedule change made. Next scheduled capture is expected at 03:00 UTC / 04:00 WAT on 22 Nov; inspect the actual event and result before treating automation as healthy. Continue to protect provider budgets and do not use Odds API for this capture path.
- Research forecasts remain unpublished. Stage 7 evidence is far below certification requirements; no production promotion or value betting unlock is justified.


## Forecast artifact integrity audit — 2026-11-21
- Downloaded and inspected the actual GitHub Actions artifact `veltrix-prospective-shadow-forecasts` (artifact ID 14694089682), rather than relying only on the workflow summary.
- Artifact JSON confirms: 25 predictions; 25 fresh upcoming fixture snapshots; 54 candidate snapshot rows; 996 historical training label rows; 136 teams; 7 competitions; model family `HIERARCHICAL_POISSON_DIXON_COLES`; status `SHADOW_FORECASTS_READY`.
- Independently counted prediction rows: 25 rows, 25 distinct canonical fixture IDs, zero repeated fixture IDs, zero repeated (fixture ID, kickoff) signatures, and zero missing fixture IDs. Thus this artifact contains no duplicated forecast fixture rows.
- Every forecast row reports team-history calculation mode `TEAM_AND_COMPETITION_HISTORY`; home/away history counts are nonzero for all 25 (observed range 9–13 matches per side). All rows cite the same 996-fixture training set and its SHA-256 `d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262`.
- Model inputs explicitly identify `HISTORICAL_GOAL_OUTCOMES_ONLY`. Odds were not used. Snapshot features were audited (46 non-null fields and lineage records per forecast) but explicitly NOT used in probabilities pending prospective feature validation. Inference made zero provider calls and zero database writes.
- Conclusion: these are model-generated forecasts for real captured upcoming fixture records, not random/sample placeholders or duplicate rows. This does not establish forecast accuracy or calibration; the model is still shadow-only and Stage 7 currently has no settled prospective labels. Production promotion and value betting remain LOCKED.


## 1X2 home-favourite concentration audit — 2026-11-21
- Follow-up prompted by user observation that the Android forecasts appeared to favour home teams almost universally. Queried the production Neon database read-only, project `veltrix-ai-analyst-db`, database `veltrix_ai_analyst`, default branch `main`, run key `8313d814c870845f1fa08fe2810529f6c26bde9feaa71f1d6d748218098fef89` (generated 2026-11-21 05:59:20 UTC).
- SQL aggregation over all 25 report predictions found: HOME was the highest 1X2 outcome probability in **25/25 (100%)**; DRAW was highest 0/25; AWAY was highest 0/25. Mean probabilities: HOME 46.2%, DRAW 24.4%, AWAY 29.4%. Each market's three probabilities summed to 100% on average.
- Joined all 25 report rows to canonical fixtures, teams and competitions. Expected home goals ranged approximately 1.54–1.73, while expected away goals ranged approximately 1.20–1.37; every fixture had higher expected home goals than away goals. Several substantially different team matchups nevertheless had tightly clustered expected-goal estimates and similarly clustered 1X2 probabilities. This is a material diagnostic warning that the current model may be imposing an overly strong/generalized home advantage or insufficiently differentiating team strengths.
- Important distinction: this does not prove that the 25 individual outcomes are wrong, nor does this small slate alone prove statistical bias; however, it invalidates any casual claim that the current forecast distribution has demonstrated balanced team-side discrimination. Prior artifact evidence still shows historical-goal inputs, no odds inputs, and auxiliary snapshots not yet used in probabilities.
- **Action/status:** treat the current 1X2 probability distribution as suspect pending source-level model audit and historical backtest. Do not use these forecasts for betting or production decisions. Keep research-only status, production promotion LOCKED, and value betting LOCKED. No code, schedules, provider calls, Odds API credits, or database data were changed by this audit.
- Next: trace home/away goal-rate construction, competition/team attack and defence shrinkage, feature normalization and probability conversion at the exact inference commit; test on held-out historical fixtures and report favourite distribution, home/draw/away calibration, Brier score and log loss by competition and season. Fix only with leakage-safe walk-forward evidence.


## Cross-market outcome concentration audit — 2026-11-21
- Extended the read-only production Neon audit to all five forecast markets in report run `8313d814c870845f1fa08fe2810529f6c26bde9feaa71f1d6d748218098fef89` (25 fixtures).
- In all 25/25 fixtures, BTTS YES probability exceeded 50% (range 55.4–60.8%, mean 57.5%); Over 1.5 exceeded 50% in 25/25 (76.3–81.1%, mean 78.3%); Over 2.5 exceeded 50% in 25/25 (52.2–59.2%, mean 55.1%); Under 3.5 exceeded 50% in 25/25 (63.2–70.0%, mean 67.3%). Over 3.5 was therefore not the most likely side in any fixture (range 30.0–36.8%, mean 32.7%).
- Combined with the prior 1X2 audit (HOME most likely 25/25; mean HOME/DRAW/AWAY 46.2%/24.4%/29.4%) and narrow expected-goal estimates, this is a pronounced cross-market concentration pattern. These are not identical probabilities, but the same side of every market threshold is selected in every fixture. This is a model-discrimination / possible parameterization or data-coverage problem requiring investigation, not a valid reason to force artificial outcome variety.
- Do not patch by balancing counts, randomizing outcomes, or imposing quotas for away/draw/BTTS NO/unders. The correct fix must come from verified team/competition attack and defence estimates, shrinkage, temporal data integrity, venue effects, goal-rate generation and Poisson probability conversion, then leakage-safe historical walk-forward evaluation and calibration. Check whether competition/team histories are truly discriminative; artifact metadata says historical goal outcomes only and snapshots/odds are not used in probabilities.
- **Status:** current 25-row report is not suitable for betting or production promotion. Keep research-only, NOT_PUBLISHED, production promotion LOCKED and value betting LOCKED. Read-only SQL only; no model code, forecasts, schedules, provider calls, odds credits, or DB data changed.
- Next engineering action: inspect the exact inference commit and trace the full model path from historical labels to per-team attack/defence strengths, expected goals and market probabilities. Build a reproducible diagnostic on the current 25 plus held-out historical fixtures, reporting cross-market favourite counts, expected-goal spread, probability distributions, calibration, Brier score and log loss by competition and season before any model modification.



## Current model quarantine — 2026-11-21
- User explicitly rejected retaining a model that generates the observed repeated market-side pattern unless it is fixed or removed. Decision: quarantine the current `hierarchical-poisson-shadow-v1` forecast path immediately while preserving raw historical data, capture, feature snapshots, evaluation infrastructure, database records, API contract and Android UI.
- Read-only source audit located the inference chain: `backend/app/research/prospective_shadow.py` fits `fit_hierarchical_poisson` with `HALF_LIFE_DAYS=365.0`, `TEAM_RIDGE=0.5`, `COMPETITION_RIDGE=0.5`; `backend/app/models/hierarchical_poisson.py` estimates global intercept, competition effects, one shared home-advantage parameter, and team attack/defence effects; `hierarchical_scoreline.py` converts those goal rates into all markets. A strong penalty may be shrinking team effects, but this is a hypothesis pending controlled reproduction and validation, not a proven root cause.
- Created branch `quarantine-current-shadow-model` from the audited main commit. Proposed immediate containment: API research route returns explicit `MODEL_QUARANTINED` with an empty prediction list and unchanged safety locks; scheduled/manual shadow inference job is hard-disabled. This keeps the existing Android screens and API contract intact while stopping this model's forecasts from being served or regenerated after deployment. The published-only endpoint remains unchanged and empty.
- Do not delete historical data or model-evaluation code. Do not force artificial outcome diversity or alter market probabilities by quotas. Candidate models must be independently benchmarked and must demonstrate fixture-level discrimination, calibrated market probabilities and chronological out-of-sample improvement before any reactivation.
- **Status:** quarantine implementation is proposed on a branch and must pass CI and production deployment before being considered active. Until that is verified, the previous deployed API/workflow may still be serving the last research report. No claim of production quarantine is made before merge/deploy/read-back verification.
- Next: CI on quarantine PR; inspect exact model fitting diagnostics and historical fixture-by-fixture held-out outputs; compare against independent Poisson, Dixon-Coles, Elo and market-specific baselines; replace or repair only after controlled evidence. Re-enable shadow forecast generation only through a reviewed release change.


## PR #133 production quarantine verification — 2026-11-21
- PR #133, “Quarantine current shadow model pending probability integrity review”, passed CI run #44889457167: Android debug build succeeded; backend tests and lint succeeded. The PR was squash-merged as commit `f7f91281328e410447105bb79fe4b5af55e1d3f3`.
- Vercel production deployment `dpl_8G17KLRj1337k47sT69WYtM8epbX` reached `READY` on target `production`, branch `main`, exact commit `f7f91281328e410447105bb79fe4b5af55e1d3f3`. Production aliases include `veltrix-ai-analyst-api.vercel.app`.
- Live production GET to `/v1/research/predictions` returned HTTP 200 JSON: `status=MODEL_QUARANTINED`, `research_only=true`, `publication_status=NOT_PUBLISHED`, `production_promotion=LOCKED`, `value_betting=LOCKED`, `predictions=[]`. This verifies the live API no longer serves the prior 25-row report.
- Live production GET to `/v1/predictions` returned HTTP 200 JSON with `predictions=[]`. Published-only feed remains empty.
- The inference workflow's `shadow-forecasts` job has `if: false` on main, disabling scheduled and manual executions of this model job. No new forecasts should be generated by this path while quarantined.
- Quarantine preserves historical database records, source artifacts, capture and feature materialization workflows, evaluation code, API response shape, and Android UI. The app is expected to receive a valid empty research feed; no new APK or UI redesign is part of this backend containment.
- Verification was read-only after deployment. No provider requests, Odds API credits, database writes, or model retraining were performed.
- **Status:** production quarantine is ACTIVE and live-verified. The current model is not admitted for research or production forecasting. The 25-row concentration audit remains the triggering evidence; it is not a claim that each individual outcome was incorrect.
- **Next engineering work:** reproduce the model's historical outputs from the exact training set and trace the full fitting path, parameter estimates, team/competition coverage, and market conversion. Build leakage-safe chronological held-out evaluation against simple independent baselines before considering a repair or replacement. Do not re-enable inference until a reviewed admission change is backed by measured results.


## Exact reproduction and shrinkage diagnostic — 2026-11-21
- Downloaded the actual Stage 6 artifact `veltrix-stage6-daily-materialization-audit` (artifact 14694463354) and the matching inference artifact `veltrix-prospective-shadow-forecasts` (artifact 14694089682). Stage 6 dataset SHA-256 is `80148b3f0f42e70d94391d9283c42f35b5b92e1631a9a1cb7baee899373dad0c`; it contains 54 prospective rows and 996 training-only rows across 162 kickoff dates and 7 competitions. The 996 training rows are explicitly `validation_eligible=false`; they are training-only historical imports, not prospective validation evidence.
- Independently recomputed the exact training-data fingerprint from all 996 rows using the source function's canonical fields and sort order. Computed SHA-256 `d70ee34940c8fc6681f3cd5751d4fdcc2e876b307fe388d9f3a792c73e34b262`, exactly matching the inference artifact's `training_data_sha256`. This confirms the reproduction used the exact original training set, not an approximate corpus.
- Reimplemented the source objective and analytical gradient using the artifact's exact 365-day half-life, team ridge 0.5, competition ridge 0.5 and training cutoff. Independently optimized the same penalized Poisson likelihood. The reproduced home/away expected-goal rates for all 25 forecasts match the original artifact to maximum absolute errors of approximately `4.91e-8` and `1.24e-7` goals respectively. This is an exact numerical reproduction of the deployed model's fitted prediction path.
- Reproduced parameter diagnostics: global intercept approximately 0.20436; global home-advantage log coefficient approximately 0.26414 (rate multiplier 1.3023); team attack-effect standard deviation 0.01367 (range -0.04683 to 0.06154); team defence-effect standard deviation 0.01255 (range -0.05734 to 0.03634). This directly establishes that the current fit has very small team-level effects relative to the shared home-advantage term. The output concentration is therefore consistent with over-shrunk team differentiation; this is no longer merely a source-code hypothesis.
- Original 25-forecast 1X2 means are HOME 46.24%, DRAW 24.36%, AWAY 29.40%, with across-fixture standard deviations 0.98, 0.51 and 0.92 percentage points respectively. In the exact 996-row training pool, empirical outcomes are HOME 46.49%, DRAW 23.80%, AWAY 29.72%. The forecast means closely track pooled training frequencies while fixture-level variation is narrow. This supports the finding that the model is insufficiently discriminating among fixtures.
- **WITHDRAWN — invalid historical evaluation:** an exploratory ridge comparison was computed over 846 fixtures in 25 kickoff-ordered blocks, but the split used kickoff time without enforcing each label's actual availability timestamp. The 996 training-only labels were imported only between 2026-11-16 and 2026-11-19 (610 on Nov 18, 370 on Nov 16, 10 on Nov 17, 6 on Nov 19). Those labels were not known at the historical March–November validation cutoffs. Therefore the reported Brier/log-loss scores and bootstrap intervals from that comparison are invalid as out-of-sample evidence and must not be used for model selection. The numbers are retained only as a record of a failed diagnostic attempt and are explicitly retracted.
- **No market-level model comparison is currently valid.** Any previous statements about lower ridge improving 1X2 while degrading totals are withdrawn with the invalid kickoff-only split. No alternative ridge value has been selected or validated.
- **Correct evaluation boundary:** the 996 imported labels have `validation_eligible=false` and `point_in_time_certifiable=false`. Their import-run completion timestamps are 2026-11-16 through 2026-11-19, not their historical match dates. The Stage 6 artifact contains 54 prospective rows but zero settled prospective labels; the prospective feature snapshot label table also contains zero rows. Consequently there are currently zero valid prospective validation folds. The previous 846-row kickoff-only split is invalid and withdrawn. None of these records count toward certification.
- **Confirmed fitted-model behaviour:** the exact reproduction verifies very small team attack/defence parameter dispersion alongside a global home-advantage multiplier of 1.3023, and verifies that the 25 forecast probabilities closely track pooled training frequencies. This establishes the parameter-compression/output-concentration mechanism. Whether the penalty is quantitatively too strong, and what replacement value is appropriate, remain unproven because valid out-of-sample evaluation is not yet available.
- **Next:** add reproducible regression diagnostics for parameter dispersion and fixture-level probability spread; expand development comparisons across chronological blocks and all five markets; assess team/competition identity coverage and the global home-effect assumption; compare independent Poisson, Dixon-Coles and Elo-based candidate families. Keep the current model quarantined until a candidate demonstrates improvement without degrading other markets and later passes genuinely prospective certification.


## Correction: retrospective ridge comparison withdrawn — 2026-11-21
- The earlier 846-fixture/25-block ridge comparison recorded above was found to have a validation-timestamp flaw. Its folds were split by kickoff date but did not require every training label to have been available before the validation block's prediction cutoff.
- The source dataset marks all 996 imported historical rows as training-only and non-PIT-certifiable. Their `label_observed_at` values range from 2026-11-16T22:04:43Z to 2026-11-19T05:40:39Z; counts by import date: Nov 16 = 370, Nov 17 = 10, Nov 18 = 610, Nov 19 = 6. Their March–November kickoff dates cannot be substituted for the later import/availability timestamps.
- The Stage 6 dataset contains 54 prospective fixtures with zero settled labels. The `prospective_feature_snapshot_labels` table has zero rows. Stage 7 previously returned `INSUFFICIENT_PROSPECTIVE_DATA`, zero evaluated fixtures and zero folds. These facts agree: there is no valid chronological validation sample yet.
- All ridge-grid Brier/log-loss values and bootstrap intervals from the kickoff-only split are **retracted** and must not be used for model selection, performance claims, or engineering decisions. The only retained results from the analysis are exact training fingerprint verification, independent reproduction of all 25 expected-goal rates, fitted parameter values and descriptive probability concentration.
- No hyperparameter change, candidate selection, or reactivation is authorized by the withdrawn comparison. The model remains quarantined.
- **Next evaluation rule:** every fold must enforce both (1) source fixture kickoff strictly before validation start and (2) each training label's actual `label_observed_at` strictly before the earliest prediction cutoff in that validation block. Training-only labels may never become validation observations. If no rows satisfy these conditions, emit zero folds and `INSUFFICIENT_PROSPECTIVE_DATA`; do not substitute event time for availability time.


## Reproducible archived-fit audit tooling — 2026-11-21
- PR #137 adds `backend/app/research/shadow_model_audit.py`, CLI `backend/scripts/audit_shadow_model_fit.py`, and `backend/tests/test_shadow_model_audit.py`. The command is database-free and consumes the immutable Stage 6 dataset artifact plus the archived shadow forecast artifact.
- The audit verifies the Stage 6 training-pool fingerprint, exact inference training-data fingerprint, training cutoff and training-only/non-PIT label classification; it refits the same hierarchical Poisson model using archived hyperparameters and compares every expected-home/away-goal rate with the archived forecasts. It reports fitted parameter dispersion and 1X2 forecast concentration, while explicitly marking itself as fit reproduction only, not out-of-sample evaluation or certification.
- CI run #44890957965 passed: backend tests 494 passed, Ruff lint passed, Android debug build passed. Earlier run #44890743039 and #44890845091 exposed and corrected lint issues; final run #44890957965 is the passing verification.
- Vercel preview for head `386baf8c7cb6e92375ffe78d33d155f521b2f72e` was not created because GitHub status reported `Deployment rate limited — retry in 24 hours`. No retry was attempted. This PR adds an offline research utility and tests only; it does not change API routes, scheduled inference, production behavior, or Android code. Preserve Vercel build capacity until the rate limit resets.
- The new script has synthetic regression coverage. The archived 25-forecast model reproduction described above was independently performed during this audit; do not claim the new CLI has itself been run against the archived production artifacts until that execution is recorded separately.
- Current model quarantine remains active. The offline audit utility does not change model admission, forecast generation, publication, value-betting locks, or certification gates.


## Additional source/data-path audit — 2026-11-21
- Independently recomputed all seven reported markets for each of the 25 archived forecasts from the stored expected-home/away-goal rates using independent Poisson score matrices, the archived `max_goals=12`, and `rho=0`. Across 175 probability values, the maximum absolute difference from the archived 1X2, BTTS, O/U 1.5, 2.5 and 3.5 probabilities was `9.99e-16`. The scoreline-to-market conversion is therefore numerically consistent with the stored goal rates for this run; the observed concentration originates upstream in the fitted goal rates, not an arithmetic error in market aggregation.
- Stage 6 feature coverage: 54 upcoming target rows; 45 rows contain 46 non-null pre-match feature fields each (83.3%); 9 rows contain only 7 basic history/coverage counters because no qualifying team history was available. The 45 feature-rich rows include last-five points, goals for/against, goal difference, shots, possession, attacks, dangerous attacks, cards, corners, substitutions, late goals, rest days and competition last-20 rates. The current shadow model explicitly declares `HISTORICAL_GOAL_OUTCOMES_ONLY` as probability inputs and does not use these features. This is a verified capability gap, not evidence that the feature fields themselves are defective.
- The 25 forecast targets span five competitions: England Premier League 7, Spain La Liga 4, Italy Serie A 5, Germany Bundesliga I 6, Brazil Serie A 3. All 25 have HOME as the top 1X2 outcome; competition-average home probabilities are tightly grouped from 45.61% to 46.91% despite different competitions.
- Descriptive home-goal/away-goal ratios in the 996 imported training-only labels vary by competition: Brazil Serie B 1.317 (n=380), Brazil Serie A 1.500 (n=122), England Premier League 1.275 (n=100), France Ligue 1 1.235 (n=90), Germany Bundesliga I 1.564 (n=81), Italy Serie A 1.060 (n=110), Spain La Liga 1.209 (n=113). The fitted model uses one global home-advantage multiplier of 1.3023 and has no competition-specific home-advantage parameter. This is a structural modelling assumption to test on valid future folds; the descriptive ratios are not validation evidence and do not by themselves prove the global coefficient is wrong.
- The above data and source audits are descriptive only. No new predictive-performance claim, hyperparameter selection, model reactivation, provider request, odds request, or database write resulted from them.
