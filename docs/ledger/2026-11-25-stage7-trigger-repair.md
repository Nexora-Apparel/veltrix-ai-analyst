# 2026-11-25 — Stage 7 automatic inference trigger repair

## Change

- Repository: `Nexora-Apparel/veltrix-ai-analyst`
- Branch: `fix/stage7-inference-trigger-mainline-sync`
- Mainline base: `3a301f6b5f92120c25c5722038b5172dde4a6c12`
- Workflow: `.github/workflows/research-shadow-inference.yml`
- Workflow change commit: `b28389b5362da6accdf391f2014c560a14d9b68e`
- PR ledger commit: `f628ada8980c81d7c743648c745050fd3f071cdb`
- PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/176
- Removed only the predicate `github.event.workflow_run.event == 'workflow_run'`. A successful Stage 6 run may originate from `workflow_dispatch` while the downstream workflow event remains `workflow_run`.
- Retained all other gates: downstream event must be `workflow_run`; upstream workflow ID must be `423623285`; upstream branch must be `main`; upstream conclusion must be `success`. Manual Stage 7 dispatch still requires explicit `confirm_research_ledger_write=true`.
- Existing inference limits, six-hour snapshot freshness check, 25-fixture cap, database environment and isolated research-ledger write step are unchanged.

## Verification and CI correction

- Read back the branch workflow file after the update; restrictive predicate is absent and all other conditions remain.
- PR #176 remains open and targets `main`. Latest branch head after regression-test correction: `1a5380b820e84c00e4c7eaef9742ec9937be26a4`.
- CI run `45636926794` was executed against the prior PR revision/merge ref `c0103ae712834de4bc78c4a4803bd2fc054faa02` (containing head `a1308b0f14d52e1e66c0fd1841ac109aa03075b9`).
- Android debug build and APK upload passed in job `139284963866`.
- Backend job `139284964650`: actionlint passed; backend compilation passed; test suite reported 580 passed and 1 failed. Failure was a stale assertion in `backend/tests/test_stage7_shadow.py` requiring the intentionally removed `github.event.workflow_run.event == 'workflow_run'` predicate. Lint was skipped because tests failed.
- Corrected the regression test to assert the predicate is absent and document that the downstream `workflow_run` event is independent of the upstream Stage 6 trigger type, while retaining checks for workflow ID, main branch, success conclusion, manual confirmation, freshness and fixture cap.
- Test correction committed as `1a5380b820e84c00e4c7eaef9742ec9937be26a4`; read-back confirms the updated assertion.
- A fresh exact-head CI run for `1a5380b...` has not yet been verified. PR currently reports non-mergeable during update/CI recalculation. Do not merge.
- Vercel Preview for the previous revision was Ready; the latest test commit triggered a new Preview build, which was Building at last observation. Vercel is not a substitute for backend CI.
- No workflow dispatch, production database write, provider/Odds API request, forecast publication, promotion, certification or Value Bet unlock occurred.

## Next gates

1. Verify a new CI run for exact head `1a5380b...`.
2. Require backend tests, lint, actionlint/workflow validation, Android debug build and APK upload to pass.
3. Recheck PR mergeability and merge only after all required exact-head checks pass.
4. Manually dispatch Stage 6 on `main` only; verify the successful Stage 6 run automatically starts Stage 7.
5. Inspect the Stage 7 report and isolated research ledger for fresh nonzero forecasts, timestamps, fixture identities and eligibility decisions.
6. Then validate research API exposure and the existing Android feed/parser/screens. Do not redesign the app.

Production publication, model promotion, certification and Value Betting remain locked until their independent evidence gates pass.


## Merge and exact-head verification

- PR #176 was merged successfully by squash after all exact-head CI jobs passed.
- Exact PR head: `f829c9cd858b6d01367f43d49e2ea3bacc4f23bd`.
- Exact-head Actions run: `45637339585`; Android debug build job `139286410139` succeeded, including APK upload; backend job `139286411108` succeeded, including actionlint, compilation, tests and lint.
- GitHub reported PR mergeable before merge. Merge commit: `b6c8fead3d59fbe4865a9e797e0ed2e5dd67a5d5`.
- Vercel Preview status context was successful/Ready for the PR revision.
- Read back `.github/workflows/research-shadow-inference.yml` from `main` after merge. The incorrect upstream event-type predicate is absent; workflow ID `423623285`, `main` branch and successful conclusion guards remain. Manual Stage 7 still requires explicit confirmation.
- Connected GitHub tools expose no workflow-dispatch action. Stage 6 production dispatch therefore remains a manual blocker; no dispatch or production research-ledger write is claimed.
- No Odds API/provider request, publication, model promotion, certification or Value Betting unlock occurred during this repair.

## Current next gates

1. Manually run **Stage 6 daily immutable snapshot and outcome materialization** on `main` through GitHub Actions.
2. Verify Stage 6 completes successfully and automatically triggers Stage 7 via the corrected `workflow_run` condition.
3. Inspect the Stage 7 artifact and isolated research ledger: dataset/snapshot freshness, fixture IDs, timestamps, nonzero forecasts, write counts and eligibility/rejection reasons.
4. If Stage 7 fails or emits no eligible forecasts, diagnose from its artifact/logs before any retry; do not bypass freshness or validation gates.
5. Only after fresh research forecasts are verified, validate the research API route and connect its response to the existing Android UI/parser. Preserve current design.

Production publication, model promotion, certification and Value Betting remain locked until their independent evidence gates pass.


## Post-merge API and Android integration audit

- Confirmed Stage 6 workflow file is `.github/workflows/stage-6-daily-snapshot-materialization.yml`, named exactly `Stage 6 daily immutable snapshot and outcome materialization`. Manual dispatch accepts no custom inputs and is gated to `refs/heads/main`; its pipeline retains closed release/promotion/value-betting gates and database identity checks.
- Confirmed `backend/app/main.py` registers both published and research prediction routers.
- Confirmed `GET /v1/research/predictions` is read-only, uses only the admitted shadow model, requires `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true` plus an admission record with `app_display_enabled=true`, and filters to fresh (36-hour) upcoming forecasts with publication/promotion/value-betting locks intact.
- Current admission record remains `SHADOW`, `RETROSPECTIVE_NOT_PIT_CERTIFIED`, `app_display_enabled=false`, `production_promotion=LOCKED`, and `value_betting=LOCKED`. Do not flip this flag before the first fresh Stage 7 report is inspected and approved.
- Confirmed Android already has `PredictionApi.fetchResearchUpcoming()`, validates research-only/unpublished/locked response fields, and fetches research feed plus published feed and history on startup and every five minutes while active.
- Existing dashboard already stores research feed state and passes it into Home, BTTS and Over/Under screens. No UI redesign or premature app wiring change is required; first-run data verification and display-admission review are the remaining prerequisites.
- Android source files inspected: `PredictionApi.kt` and `VeltrixDashboard.kt`. Existing design is preserved.

## Follow-up — 2026-11-25 Stage 6 run #22 and Stage 7 orchestration verification

- Owner-dispatched Stage 6 run: [45638434818](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45638434818), job 139290105035, completed successfully on main at b875cd3f71fc18e8021c76a9f1c0dabb3690f294.
- Stage 6 independently reported DAILY_MATERIALIZATION_VERIFIED: 114 immutable snapshots for 114 distinct fixtures; 54 latest settled-label events; dataset SHA-256 414d8333f8f8bf7dd9d2318994ac64521f1448d2c5c04eee34d5297c2e50bd54.
- Corrected automatic workflow_run orchestration fired. Stage 7 evaluation run 45640909794, run #32, started from the successful Stage 6 event on main. At latest inspection (2026-11-25 15:07 UTC), evaluation job 139298951956 remained in_progress at the read-only expanding-window evaluation step; certification and artifact-upload steps had not started, and no artifact was present. GitHub Actions job-log download returned BlobNotFound, so no log-level cause is asserted. Do not rerun/cancel until status is refreshed and active execution is understood.
- Sibling prospective forecast workflow 45640909772, run #22, was skipped by design. Read-back of .github/workflows/prospective-shadow-predictions.yml confirms a hard if: false quarantine, documented as a hold following the 2026-11-21 cross-market concentration audit. This is not a trigger-repair regression. Do not remove quarantine without a reviewed model-admission change and passing evidence.
- Forecast builder source inspection confirms a fresh target snapshot must be within six hours, have a pre-kickoff prediction cutoff, and use at least 30 cutoff-valid, rights-valid training labels. It emits an auditable abstention when fresh targets or sufficient eligible training data are absent. Forecast construction makes zero provider calls and zero DB writes; isolated research-ledger persistence is a separate step.
- Re-read model admission record: tier SHADOW, certification RETROSPECTIVE_NOT_PIT_CERTIFIED, app display disabled, production promotion locked, Value Betting locked. No release/display flags were changed.
- PR #176 remains the merged trigger repair (merge commit b6c8fead3d59fbe4865a9e797e0ed2e5dd67a5d5). PR #175 is an older, divergent, unmergeable duplicate of the same trigger fix and must not be merged.
- No Odds API or football-provider calls, public publication, Telegram delivery, production promotion, certification, or Value Betting unlock occurred.

### Next steps

1. Refresh Stage 7 run #32 and inspect job/step status; obtain its completed artifact and certification output once available. If it remains stuck or fails, diagnose from workflow/job evidence before retrying.
2. Treat the prospective forecast quarantine as a separate model-admission task. Review the 2026-11-21 concentration monitor, archived model-fit audit, and current prospective evaluation before proposing any change. Do not set if: false to true as a shortcut.
3. Only after a forecast report exists and passes fresh-snapshot, training-cutoff, rights, identity, concentration, and model-diagnostic checks, review isolated research-ledger persistence and then the already-built read-only API/Android display path.
4. Keep publication, app display, model promotion, certification, and Value Betting locked until their separate approvals/evidence gates are met.


## Follow-up — Stage 7 evaluation #32 completed (2026-11-25)

- Stage 7 evaluation run [45640909794](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45640909794), run #32, completed successfully on main at b875cd3f71fc18e8021c76a9f1c0dabb3690f294. Job 139298951956 completed all steps, including read-only expanding-window evaluation, independent certification gates and artifact upload.
- Evaluation output printed: 54 fixtures, 3 folds, source dataset SHA-256 414d8333f8f8bf7dd9d2318994ac64521f1448d2c5c04eee34d5297c2e50bd54, status RESEARCH_ONLY_NOT_PRODUCTION_APPROVAL, production promotion LOCKED, Value Betting LOCKED.
- Independent certification output: 54 fixtures evaluated; 54 settled labels; 6 distinct kickoff dates; walk-forward market fixture counts 54 each for 1X2, BTTS, OVER_UNDER_1_5, OVER_UNDER_2_5 and OVER_UNDER_3_5. Gate result BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE. Production promotion and Value Betting remain LOCKED.
- Artifact uploaded: veltrix-stage7-prospective-research-evaluation, artifact ID 15036396581, 531139 bytes, SHA-256 04bf575701bbb92259d5d75acdc4a15d0d460dece6a6a6b0e9907855b70b62d9, 90-day retention. Workflow logs confirm two files (prospective-model-evaluation.json and prospective-dataset.json) were uploaded. The job log itself contains the decisive gate summary; full artifact contents have not yet been independently unpacked/reviewed.
- Interpretation: workflow success means the research evaluation and certification gate executed successfully, not that the model passed certification. Current evidence is far below the required 1000 walk-forward fixtures per market, 300 prospective settled selections and 90 distinct dates. Do not infer ROI/odds/Brier/log-loss pass from the summary; inspect full artifact before any model diagnostic conclusions.
- No publication, Telegram delivery, app display enablement, production model promotion, Value Betting unlock, provider calls or Odds API calls occurred.

### Next steps

1. Retrieve and inspect both JSON files in artifact 15036396581, including per-market metrics, fold-level scores, calibration, concentration, rights/odds coverage and dataset lineage. Preserve artifact digest for integrity checks.
2. Continue prospective data accumulation through the existing approved capture/materialization pipeline; do not manufacture labels, relax PIT cutoffs, or bypass eligibility rules to accelerate sample counts.
3. Review the 2026-11-21 concentration audit using repository search/tree discovery (the assumed ledger filename was not found at that exact path); inspect the actual audit artifact before proposing any forecast-quarantine change.
4. Keep prospective forecast workflow quarantine and model admission flags unchanged until the full report and concentration audit support a reviewed change.
5. Keep app display, publication, production promotion, certification and Value Betting locked.
