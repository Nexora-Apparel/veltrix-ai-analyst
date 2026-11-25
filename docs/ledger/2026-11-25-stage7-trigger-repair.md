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


## Artifact deep inspection — Stage 7 run #32

- Downloaded artifact 15036396581 through the GitHub Actions artifact endpoint and unpacked both JSON files. ZIP digest matches GitHub artifact metadata: 04bf575701bbb92259d5d75acdc4a15d0d460dece6a6a6b0e9907855b70b62d9.
- Evaluation JSON confirms dataset READY_FOR_RESEARCH; SHA-256 414d8333f8f8bf7dd9d2318994ac64521f1448d2c5c04eee34d5297c2e50bd54; 1,442 fixture identity rows; 114 eligible prospective rows; 54 settled prospective labels over 6 kickoff dates; 1,408 historical training-only labels; 6 competitions; 3,038 feature-lineage records; zero invalid system-observed sightings.
- Critical model-scope finding: model_feature_usage is HIERARCHICAL_GOAL_RATE_ONLY; SHOT_POSSESSION_ATTACK_EVENT_FEATURES_CAPTURED_BUT_NOT_YET_USED. Thus extensive shot/possession/attack/event features are captured and lineage-tracked but do not currently contribute to model predictions.
- 1X2: model Brier 0.61522 vs research baseline 0.63044; log loss 1.02498 vs 1.04565. Paired model-minus-baseline 95% CI is [-0.03516, 0.00189] for Brier and [-0.05002, 0.00376] for log loss; both cross zero. This does not establish reliable improvement. Baseline is not bookmaker odds.
- BTTS: model Brier 0.26021 vs baseline 0.26754; log loss 0.71383 vs 0.72930. Paired 95% CIs [-0.01297, -0.00050] and [-0.02745, -0.00122], respectively, favour the model versus this research baseline only; n=54 and no bookmaker comparison.
- O/U 1.5: model Brier 0.19406 vs baseline 0.19762; log loss 0.57849 vs 0.59235. Paired 95% CIs [-0.00826, 0.00198] and [-0.03188, 0.00428] cross zero.
- O/U 2.5: model Brier 0.24931 vs baseline 0.25297; log loss 0.69179 vs 0.69974. Paired 95% CIs [-0.01221, 0.00593] and [-0.02610, 0.01214] cross zero.
- O/U 3.5: model Brier 0.21754 vs baseline 0.21667; log loss 0.62560 vs 0.62358. Paired 95% CIs [-0.00848, 0.01131] and [-0.01816, 0.02397] cross zero; point estimates slightly favour baseline.
- Fold diagnostics: folds validate 25, 25 and 4 fixtures. Optimizers converged in all three. Dixon-Coles rho was set to zero in folds 1 and 2 due insufficient inner out-of-fold evidence (0 and 2 inner OOF fixtures); fold 3 estimated rho=0.1291 using 28 inner OOF fixtures. The 4-fixture third validation block is particularly small.
- Certification artifact explicitly records: 54/300 settled prospective fixtures; 6/90 settled dates; 54/1000 walk-forward fixtures per market; timestamped odds coverage NOT_EVALUATED; ROI and lower 95% bound NOT_EVALUATED; 1X2 bookmaker Brier/log-loss NOT_EVALUATED because current baseline is not bookmaker odds. All gates fail closed.
- Bootstrap intervals are descriptive only (200 paired competition-stratified replicates, seed 20261118), not release tests. No calibration or market confidence claim should be extrapolated from these intervals.
- Integrity check: evaluation and dataset JSON both identify the same source dataset hash. No dataset mismatch observed.

### Engineering implications

1. Preserve all current admission and forecast-workflow locks.
2. Inspect model feature pipeline and admission review to determine whether the captured shot/possession/attack/event features are intentionally excluded pending validation or are a pipeline integration gap. Do not add them to the model without a separate leakage-safe feature-ablation and walk-forward evaluation.
3. Improve prospective sample accumulation and date diversity using existing capture schedule; keep the PIT observation cutoff and rights checks intact.
4. Investigate fold construction and minimum inner-OOF sample sufficiency for rho estimation; do not force nonzero rho when evidence is insufficient.
5. A later 1X2 certification attempt must use timestamped bookmaker odds; current research baseline cannot satisfy that gate. Odds API credits remain protected; first inventory available licensed odds history and coverage before any paid calls.
6. Continue to keep app display, public publication, production promotion, certification and Value Betting locked.


## Follow-up — Android research-display contract and quarantine-path audit (2026-11-25)

- Re-read the current mainline research API, model admission record, Stage 7 inference workflow, builder, concentration monitor, and 21 November integration ledger.
- Corrected interpretation of the API admission contract: `app_display_enabled=false` in the committed model record is intentional for this SHADOW-only model. The API requires that exact value alongside tier SHADOW, certification RETROSPECTIVE_NOT_PIT_CERTIFIED, production promotion LOCKED, and Value Betting LOCKED. A separate deployment environment switch, `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true`, is the explicit app-display control. Do not change the admission record to true; that would cause the current model-admission check to reject it.
- The hard `if: false` quarantine belongs to the separate legacy `.github/workflows/prospective-shadow-predictions.yml` path. It is not the active selected Stage 7 inference path.
- The active `.github/workflows/research-shadow-inference.yml` is enabled for successful Stage 6 `workflow_run` events (workflow ID 423623285, main branch, success conclusion) and explicit manual dispatch with `confirm_research_ledger_write=true`. It builds selected Newton v2 forecasts and persists only through the isolated research-ledger writer.
- Stage 7 v2 applies the concentration monitor to all fitted fixtures before team-history abstentions. For slates >=15 it quarantines on P(home) population SD outside [0.08, 0.22], any 1X2 top-pick share >0.85, BTTS-Yes pick share >0.90, or Over-2.5 pick share >0.90. Smaller slates are not concentration-gated. A quarantined run returns no prediction rows and a non-ready status.
- The 21 November Stage 7 integration ledger confirms the monitor was part of the selected v2 design; it also records a 5-match-per-team abstention rule. It does not document a particular 21 November concentration violation value in the reviewed excerpt. Do not infer a specific failed threshold without the corresponding run summary/artifact.
- Existing model probabilities use historical goal outcomes only. Captured auxiliary features are intentionally excluded because the source eligibility policy says post-match corners/cards/statistics and non-PIT availability proxies are not valid pre-match features without verified availability timestamps and rights. Feature integration must wait for eligible evidence; adding these fields now would introduce temporal leakage risk.
- Existing Android research feed wiring is present. The API's two-part display gate is intentional: SHADOW admission record remains false for production display eligibility, while the deployment env switch controls whether the research-only endpoint is exposed. Existing Android parser/screens need no redesign.
- No code, admission flag, workflow quarantine, production setting, provider credential, or Odds API usage was changed in this audit.

### Next actions
1. Retrieve the most recent run/artifact for the active `research-shadow-inference.yml` workflow associated with Stage 6 run #22 and inspect its sanitized summary: fitted/shown/abstained counts, concentration violations, model version, dataset hash, training cutoff, forecast cutoff and fixture identities.
2. If the run is non-ready or quarantined, diagnose the actual per-run monitor values before proposing threshold/model changes. Do not bypass the monitor.
3. If a fresh non-quarantined report was persisted, verify isolated ledger read-back and direct research API response while the deployment display switch remains off.
4. Then correct/verify any API admission or display-path defects with tests; only after a reviewed first-run summary may the separate deployment display switch be enabled for research-only app visibility.
5. Keep the legacy forecast workflow quarantine, production publication, model promotion, certification, Telegram delivery and Value Betting locks unchanged.


## Production research-display deployment check — 2026-11-25

- Vercel project `veltrix-ai-analyst-api` belongs to team `team_Lj9bVie6YVKgrQTBNNwj1ieu`.
- Read the Production environment variable inventory without decrypting secrets. `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED` exists with plain value `true`, Production target only. Its owner-authored comment says it is for supervisor-approved RESEARCH ONLY shadow forecast display and does not unlock production publication or Value Betting. No environment value was changed.
- Latest Production deployment after this ledger update: `dpl_D23GricxVJXu1dWjbmmpiNowm1Fq`, state READY, commit `ea6f8e3f6d2a75d2b78b03a6753468aec16e111f` (documentation-only ledger clarification).
- A 30-minute Vercel runtime-log query filtered to `/v1/research/predictions` returned no matching records. This means no matching API request was logged in that window; it does not prove the endpoint is broken or that the app cannot fetch it.
- Direct endpoint inspection through the available web reader was not supported. A live API payload, Neon research-ledger row count, and physical Android display therefore remain unverified.
- Important separation: the deployment display switch is already true, but that alone does not create forecasts. The active Stage 7 inference workflow must successfully produce a non-quarantined report and persist it to the isolated research ledger before the API can return fixtures.
- No new deployment was triggered by this check; the READY deployment is the Git-linked production deployment for the latest documentation commit.

### Immediate verification sequence
1. Retrieve the run triggered by Stage 6 run 45638434818 for workflow `research-shadow-inference.yml`; inspect the job result and `veltrix-stage7-shadow-run-summary` artifact.
2. If the summary is `SHADOW_FORECASTS_READY`, verify it has nonzero shown fixtures, zero concentration violations, fresh cutoffs, verified canonical identities, and the expected v2 model version.
3. Read back the isolated research ledger and call the live research API; confirm the same fixture set and all research-only / NOT_PUBLISHED / LOCKED fields.
4. Verify the existing Android app on-device. Do not redesign it; retain the research label and existing published-fixture precedence.


## Follow-up — Stage 7 zero-forecast diagnosis (2026-11-25)

- Retrieved active inference run [45640909666](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45640909666), triggered by successful Stage 6 run #22. Job 139298952312 completed successfully; artifact 15036481511 (veltrix-stage7-shadow-run-summary) was downloaded and inspected.
- Artifact SHA-256 from GitHub metadata: 5a3d74310704ea103911877128c2c0393f5f315c3cf9f43ba5b92a33efbad311. Report dataset SHA matches Stage 6: 414d8333f8f8bf7dd9d2318994ac64521f1448d2c5c04eee34d5297c2e50bd54.
- Actual report status: NO_FRESH_UPCOMING_SNAPSHOTS; forecast_count=0; abstention_count=0; predictions=[]; database_writes=0; provider_calls=0; odds_used=false. Concentration monitor PASS with zero fitted fixtures; this was not a concentration quarantine.
- Independent inspection of Stage 6 artifact 15034519300 (prospective-dataset.json) confirms 114 rows: 54 settled and 60 unsettled. All 60 unsettled rows have prediction_cutoff_at=2026-11-25T08:40:05.859675Z; Stage 7 generated at 2026-11-25T15:15:02.210501Z. They were ~6h35m old, exceeding the configured six-hour freshness limit. All 54 other rows are labelled/settled. The exact target selector in backend/app/research/stage7_shadow.py correctly returned zero.
- Stage 6 run #22 logs confirm immutable persistence inserted 0 snapshots and marked all 114 unchanged; it reused the old PIT snapshot payloads. This is consistent with the Stage 7 freshness rejection and does not justify relaxing the six-hour cutoff.
- Upstream capture run [45578789004](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45578789004) succeeded at 08:43 UTC. It ran the approved rolling capture, reported all six competitions validated and no failures; import statuses were SKIPPED_ALREADY_VALIDATED, with request accounting shown in its batch summary. The automatically triggered Stage 6 run [45578874211](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45578874211) failed at immutable persistence with IMMUTABLE_SNAPSHOT_IDEMPOTENCY_CONFLICT. The later owner-dispatched Stage 6 #22 succeeded after the repair, but its dataset still reused the original 08:40 snapshots. The later Stage 7 workflow therefore had no fresh target cutoffs.
- Confirmed Stage 6 is automatically triggered by successful completion of the capture workflow, while the capture workflow is scheduled daily at 00:17 UTC and may start later (the observed scheduled run began at 08:43 UTC). The successful Stage 6 #22 was manually dispatched hours after that capture.
- No freshness threshold, immutable snapshot, rights, identity, model, or concentration gate was changed. No additional provider/Odds API calls were made during this diagnosis. No forecast rows were persisted; only the zero-forecast run record was inserted by the isolated ledger writer. App display remains unverified because the live API has no verified forecasts to return.

### Next steps

1. Obtain a fresh approved 5DollarFootballAPI capture on main, then let its workflow_run trigger Stage 6 and Stage 7 in sequence. Do not rerun Stage 7 against the stale dataset or weaken the six-hour cutoff.
2. Connected GitHub actions tools expose no workflow-dispatch operation. A fresh capture dispatch is therefore a manual GitHub Actions operation unless a reviewed trigger mechanism is added; no such dispatch is claimed here.
3. After fresh capture, verify Stage 6 creates new immutable snapshot keys with fresh system-observed prediction cutoffs (rather than reusing the 08:40 snapshots), then inspect Stage 7 report for nonzero shown forecasts and all gate fields.
4. Verify isolated research-ledger forecast rows, live GET /v1/research/predictions payload, and physical Android rendering in that order. Preserve the existing Android design.
5. Keep public publication, production model promotion, certification, Telegram delivery and Value Betting locked.
