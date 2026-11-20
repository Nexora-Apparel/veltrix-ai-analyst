# VELTRIX AI ANALYST — Stage 7 continuation journal

**Date:** 2026-11-19  
**Repository:** `Nexora-Apparel/veltrix-ai-analyst`  
**Verified base commit:** `1a232407ceadf2f6de7243d046d1e0fc9de3e5bf`  
**Purpose:** record the latest Stage 4–7 execution chain and establish the exact continuation point. This entry supplements, and does not replace, the Stage 5 reconciliation/handover record.

## Executive checkpoint

The project is currently at **Stage 7 prospective research evaluation and certification**. Stage 5's seven-scope production materialization has already been executed and independently verified. Do not repeat it as a continuation step. Stage 6's immutable prospective snapshots are persisted, but no settled outcome labels have yet accumulated. The latest Stage 7 workflow completed technically, while its report correctly remains `INSUFFICIENT_PROSPECTIVE_DATA`. Stage 8 publication remains locked.

## Latest execution chain — 2026-11-19

### Stage 4 — scheduled prospective capture

- Workflow run: [44514389412](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44514389412)
- Job: `135526486734` (`capture`), conclusion `success`.
- Trigger: `schedule`.
- All seven approved competition scopes completed without failed competitions.
- The collector reported 14 provider requests total (2 per competition) and import-run IDs 12–18.
- Scope statuses were `SKIPPED_ALREADY_VALIDATED`; reported record counts were Brazil Serie A 15, Brazil Serie B 2, England Premier League 10, France Ligue 1 9, Germany Bundesliga I 9, Italy Serie A 10, Spain La Liga 10. These are collector/import-run record counts, **not proof that 65 new rows were inserted by this run**.
- No Odds API use is evidenced by this capture log.

### Stage 6 — daily immutable snapshot and outcome materialization

- Workflow run: [44514513198](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44514513198)
- Job: `135526912270` (`materialize`), conclusion `success`.
- Rebuilt dataset: 59 eligible prospective rows; 0 settled label rows; 59 unsettled rows; 0 expanding folds.
- Dataset SHA-256: `60cf113db9ea055e5cbbd72c7dbbb0a26cbbad2dca2f5ca76e9eba2a41fbc91c`.
- Persistence result: 59 rows, 0 inserted, 59 unchanged; 0 labels inserted.
- Independent post-write verification: 59 snapshots, 59 distinct fixtures, 0 latest label events; status `DAILY_MATERIALIZATION_VERIFIED`.
- Production promotion and release eligibility remained false/locked; value betting remained locked.

### Stage 7 — latest prospective evaluation and certification gate

- Workflow run: [44514643781](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44514643781)
- Job: `135527357900` (`evaluate`), conclusion `success`.
- Artifact: [14524726745 — veltrix-stage7-prospective-research-evaluation](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44514643781/artifacts/14524726745).
- Evaluation output: `INSUFFICIENT_PROSPECTIVE_DATA`; 0 fixtures evaluated; 0 folds; production promotion `LOCKED`; value betting `LOCKED`.
- Independent certification output: 0 settled labels, 0 distinct settled kickoff dates, 0 evaluated fixtures, and zero walk-forward fixtures for 1X2, BTTS, O/U 1.5, O/U 2.5 and O/U 3.5.
- Certification status: `BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE`.
- A successful GitHub Actions conclusion means the evaluator and fail-closed certification gate executed successfully. It does **not** mean the model passed certification.

## Stage 5 state — explicitly not a pending task

The latest successful seven-scope apply remains run [44494508790](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44494508790), with all seven scopes applied and post-apply linkage verification completed. Its verified inventory recorded 1,063 fixture rows/links, 1,058 verified fixture identities and five fixture conflicts, plus one team identity conflict. The Brazil Serie B global review restrictions remain in force. PR #118 merged the manual-only safety correction; current workflow configuration was re-fetched and confirms only `workflow_dispatch`, with exact typed confirmation `APPLY_ALL_SEVEN_APPROVED_SCOPES`. Do not rerun bulk materialization unless a new, explicit reconciliation requirement arises.

## Continuation plan

1. Keep the scheduled Stage 4 capture operating for the seven approved scopes; monitor run conclusion and request/lineage integrity. Do not infer new data insertion from `SKIPPED_ALREADY_VALIDATED` status.
2. Continue Stage 6 daily materialization after capture. Verify whether genuinely settled fixtures produce append-only label events with exact source-observation/sighting/provider-response lineage and strict post-kickoff observation timing.
3. When labels appear, rerun Stage 7 and inspect both evaluator report and independent certification output. Do not treat snapshots or upcoming fixtures as settled samples.
4. Keep the five fixture identity conflicts, one team conflict, and the two Brazil Serie B global review restrictions excluded from any dependent feature or certification path until independently resolved with admissible evidence.
5. Assess expansion to additional competitions only through explicit rights approval and the existing provenance, canonical identity, PIT and materialization controls. Current seven-scope daily volume is insufficient for a reliable 25-fixture daily target; never pad the feed.
6. Keep Stage 8 prediction publication and Stage 9 Android runtime verification locked/pending until the required certification and release gates pass. Preserve the existing Android UI. Keep value betting independently locked.
7. Protect The Odds API budget. No odds calls are required for this capture/snapshot/evaluation continuation.

## Verification boundaries

- The latest logs prove successful workflow execution and the exact reported dataset/evaluation counts above.
- They do not prove that any production prediction has been published, that a model is certified, or that value betting is enabled.
- No Stage 5 re-apply, Android physical-device test, prediction publication, or Odds API request was performed as part of this continuation checkpoint.

## Next checkpoint trigger

The next meaningful Stage 7 checkpoint is a Stage 6 run that records one or more valid settled label events, followed by a Stage 7 evaluation over those labels. Until then, continue daily capture/materialization and retain the fail-closed publication state.

## Stage 7 acceleration — PR #119 merged

- PR: [#119 — rights-checked historical training-only pool](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/119)
- Squash merge commit: `8289c67d8d5e760c194414db449d415763ccfd85`.
- Purpose: use historical match outcomes as model-training labels when their completed import run is proven to have finished before a prospective validation kickoff. This avoids waiting for 30 new prospective results before the first walk-forward fold can be formed.
- Production Neon was queried read-only using the exact SQL embedded in the new dataset builder:
  - 996 finished fixture rows eligible after source, response, score, canonical fixture/team/competition identity, and rights checks.
  - 996/996 map to completed import runs; nine distinct import runs.
  - Every import run completed after retrieval and after its fixture kickoff, and before the first currently snapshotted prospective kickoff (2026-11-19 22:30 UTC).
  - Import completion range: 2026-11-16 22:04:43.996 UTC through 2026-11-19 05:40:39.619 UTC.
  - The 996 rows include 990 legacy rows with no certified system-observed timestamp and six newer system-observed rows. All are represented as training-only rows using the completed import-run timestamp as the conservative label-availability time.
- Safety:
  - Historical training rows have no prediction cutoff or feature lineage and cannot enter pre-match feature construction.
  - They are marked `validation_eligible=false`; the fold builder permits them only in training when import completion is strictly before validation kickoff.
  - Only prospectively snapshotted fixtures can be validation rows.
  - Historical training rows are not written to immutable prospective snapshots or append-only prospective label tables.
  - Certification counts remain based only on prospective settled labels and prospective walk-forward validation fixtures. The 300 prospective-label, 90-date and 1,000-per-market thresholds are unchanged.
  - Prospective row serialization remains compatible with existing immutable snapshot hashes.
- CI run: [44611300127](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44611300127), conclusion success.
  - Backend tests: 428 passed, 1 warning.
  - Ruff: all checks passed.
  - Android debug build: success.
- Important verification boundary: CI and the exact SQL validate the implementation and eligible training pool. The new Stage 6 builder/evaluator has not yet been run against the production database after this merge. No new fold, prospective evaluation, certification, prediction publication, or value-bet release is claimed.

## Immediate next checkpoint after PR #119

1. Keep the existing 04:00 WAT prospective capture schedule active. The two 19 November Brazil Serie A fixtures in the current snapshot have 22:30 UTC kickoffs; no post-kickoff result observation exists yet at the latest database check.
2. After the next capture, verify that Stage 6 records post-kickoff observations and append-only labels for any settled snapshot fixtures.
3. Confirm the new builder returns the 996-row historical training pool plus any newly settled prospective labels, without persisting historical rows as prospective snapshots.
4. Confirm Stage 7 forms folds using historical training-only rows and prospective validation rows, then inspect the independent certification gate. The prospective 300/90/1000 thresholds remain unchanged.
5. Keep production prediction publication, value betting and Android runtime release locked until their respective evidence gates pass.

## Stage 7 trigger correction — PR #120 merged

- PR: [#120 — rerun Stage 7 when prospective evaluation code changes](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/120)
- Merge commit: `ab5256c07667a42a726ea0c0649da6c08141502a`.
- Added the prospective dataset builder, fold logic, model evaluator and evaluation entrypoint to the Stage 7 workflow's push-path filter.
- Purpose: evaluation-code changes now trigger the read-only Stage 7 research workflow immediately rather than waiting for a later Stage 6 workflow_run.
- The workflow remains read-only; no provider calls, odds calls, database writes or publication actions are introduced.
- The Stage 7 run on the new main commit has not yet been independently observed in Actions at this journal update. The next check must verify the run and its artifact before claiming production-database execution of PR #119.

## Continuation decision — keep progressing while prospective labels accumulate

**User direction:** continue toward launch; do not treat the waiting period for settled prospective outcomes as a reason to stop engineering work.

### Current operating decision

- Keep the existing seven approved competition capture schedule active at 04:00 WAT.
- Continue the Stage 6 materialization and Stage 7 evaluation chain when its scheduled/workflow triggers run.
- Historical training-only outcomes may seed model training, but they do not replace prospective validation evidence or reduce certification thresholds.
- Do not publish predictions until the production model and release gates explicitly pass.
- Do not unlock value betting or spend The Odds API credits for this workstream.
- Preserve the existing Android application UI; Android runtime release verification remains downstream of a valid prediction publication API.

### Next engineering work identified

The next parallel work item is a coverage and rights audit of the current seven competitions, followed by a shortlist of additional competitions that could be added without weakening source approval, canonical identity, point-in-time provenance or capture reliability. The purpose is to increase genuine eligible fixture volume toward the 25-per-day target, not to manufacture volume.

**Execution status at this journal update:** this coverage/expansion audit has been identified as the next task but has not yet been run. No additional competition has been approved or added by this decision. Any proposed expansion must be checked against the provider's actual rights approval and the existing seven-scope governance process before implementation.

### Launch state

The project is still in pre-launch validation. The merged PRs #119 and #120 improve the historical training pool and ensure evaluator code changes trigger Stage 7, respectively. They do not themselves certify the model or publish predictions. The next decisive evidence remains a successful prospective walk-forward evaluation and independent certification result, followed by the gated API/app release work.

## Daily post-capture orchestration audit — prediction inference is not yet connected

**User requirement clarified:** after daily capture, the system should calculate and deliver up to 25 eligible predictions per day. Twenty-five is a daily ceiling/target, not a quota to fill with unsupported fixtures.

### Verified workflow chain on main

1. **Stage 4 capture** — `.github/workflows/prospective-5dollar-daily-capture.yml`
   - Scheduled at `0 3 * * *` UTC (04:00 WAT).
   - Collects recent settlements and upcoming fixtures in a bounded rolling window.
   - Uses the approved 5DollarFootball provider scopes and existing database PIT checks.

2. **Stage 6 materialization** — `.github/workflows/stage-6-daily-snapshot-materialization.yml`
   - Triggered by completion of the Stage 4 workflow.
   - Runs only if the capture workflow conclusion is success.
   - Builds the canonical strict-PIT prospective dataset, persists immutable pre-match snapshots and append-only post-kickoff outcome labels, and verifies persistence.
   - Explicitly asserts that release eligibility is false, production promotion is LOCKED and value betting is LOCKED.

3. **Stage 7 research evaluation** — `.github/workflows/stage-7-prospective-research-evaluation.yml`
   - Triggered by successful Stage 6 completion (and relevant code pushes).
   - Runs read-only expanding-window research evaluation and independent certification gates.
   - It evaluates model evidence; it is not a daily upcoming-fixture prediction publisher.

4. **Private model artifact training** — `.github/workflows/train-model-artifact.yml`
   - Has manual dispatch and a training-branch/path trigger.
   - It is not configured as an automatic post-capture inference/prediction workflow.

### Finding

**No verified workflow currently runs daily prediction inference after Stage 6 and publishes up to 25 predictions to the existing Android API.** The existing chain captures, materializes, and evaluates. It does not yet complete the daily inference/publication step.

### Required Stage 8 implementation

Build a gated daily prediction-generation and publication workflow that:

- Runs after successful Stage 6 materialization and only after a certified, immutable production model artifact is available.
- Loads the upcoming fixtures from the canonical approved dataset and enforces fixture identity, source rights, freshness and strict pre-kickoff PIT checks.
- Scores eligible fixtures with the certified model for 1X2, BTTS and O/U 1.5, 2.5 and 3.5.
- Applies the strict publication gate; excludes conflicts, stale/incomplete evidence and unsupported forecasts rather than using generic fallback probabilities.
- Publishes at most 25 eligible fixtures per WAT prediction date through the existing prediction API/storage contract consumed by the current Android app. If fewer than 25 pass, publish fewer and record the shortfall.
- Is idempotent by canonical fixture and prediction version, retains immutable prediction provenance, and does not overwrite prior predictions or settled history.
- Keeps bookmaker value-bet functionality separately locked until its own certification requirements pass.
- Does not redesign the Android UI or add Telegram delivery.

### Important distinction

Settled match results are needed to append prospective outcome labels and measure/validate model performance. They are not a prerequisite for scoring tomorrow's fixtures once a certified model artifact and valid pre-match inputs are available. The historical training-only pool can support training research but cannot substitute for prospective certification.

**Status:** this is a verified architecture gap, not a claim that Stage 8 has already been implemented. No production predictions were generated or published during this audit.

## Android Menu requirement — human-readable daily prediction notifications

**User-confirmed product requirement:** add a Notifications destination inside the existing Menu section. Notifications are the app's internal, user-facing daily publication updates. No Telegram or external messaging delivery is to be added.

### UX/content requirements

- Add a Notifications item within the existing Menu section and preserve the dashboard design, navigation and visual language.
- Notify the user when daily predictions have been published, including the count (up to 25).
- If fewer than 25 pass, explain briefly and naturally why the list is shorter; do not pad forecasts.
- If zero predictions are published, give a clear, human-readable reason (for example, insufficient reliable information or publication checks not passing), without inventing a cause.
- If daily processing is still underway, show a truthful pending update only if the state is useful; avoid unnecessary robotic/status clutter.
- Notifications should be written as ordinary conversational English, not JSON, raw API output, machine-status codes or robotic templates.
- Keep notifications persisted and dated so the user can review daily publication outcomes; mark/read state can be implemented if appropriate.
- Notification creation must be driven by verified daily pipeline outcomes. Never report success or a specific count before publication is verified.
- Do not create Android OS push notifications or Telegram delivery as part of this requirement unless explicitly requested later; this requirement is for the in-app Notifications destination.

### Example copy (illustrative, not actual delivery)

- Published: "Today's predictions are ready. I've found 23 matches that passed our checks and added them to your Prediction section."
- Shortfall: "I could only find 16 matches worth publishing today. Some fixtures didn't have enough reliable data, so I left them out rather than force predictions."
- Zero: "I couldn't publish predictions today. A few matches were missing the reliable data I needed, and I wasn't comfortable making guesses."

### Verified current UI gap

The main dashboard file `android/app/src/main/java/com/veltrix/aianalyst/VeltrixDashboard.kt` currently defines six tabs (Home, History, BTTS, Value Bet, Over/Under, Menu). Its MenuScreen currently shows Preferences (Odds format and App version) only. No Notifications destination, notification store or publication-notification integration was verified in the fetched main file.

### Implementation sequence

1. Add a notification model/API contract backed by the verified daily publication outcome.
2. Persist notification records with publication date, publication status, published count and a concise, human-readable explanation; keep provenance/diagnostic detail internal.
3. Add a Notifications screen reachable from Menu, retaining the current UI style and avoiding a dashboard redesign.
4. Connect notification creation to the Stage 8 publication workflow only after publication succeeds or a verified no-publication outcome is recorded.
5. Test published-count, shortfall, zero-published, pending and unavailable states, along with duplicate/idempotency and date grouping.

**Status:** requirement and implementation plan documented. No notification UI or records have been implemented yet.



## Sparse-data inference and prediction reliability tiers — user clarification

**User clarification:** do not interpret missing or sparse data as an automatic fixture rejection. The intended prediction architecture includes sophisticated, governed calculations to generate forecasts where evidence is limited; the Strong / Medium / Low reliability classification is intended to communicate the strength of the supporting evidence and calculation.

### Design requirements (not yet verified as implemented)

- Use a data-adaptive, hierarchical calculation path when team-specific data is sparse: appropriately weighted available team evidence, competition/league baselines, shrinkage and the governed goal-probability framework may be used where technically justified and tested.
- Never silently impute missing features as zero or fabricate observations. Missingness must remain explicit and influence the calculation and its reliability tier.
- **Strong / Medium / Low** must describe evidence quality, input completeness, freshness, sample size, uncertainty and validation/reliability—not simply the forecast probability or the popularity of a favourite.
- Sparse data may still produce a publishable prediction if the fallback method is scientifically defensible, adequately tested and within the release gate. A fallback is not permission to use arbitrary/generic probabilities or bypass model certification.
- Exclude fixtures when even the fallback cannot produce a defensible forecast, or where identity, rights, freshness, PIT or other mandatory gates fail.
- Natural-language daily notifications use the collective voice **“the models”** rather than first-person singular/plural, with non-robotic phrasing. Illustrative copy: “The models have finished today's analysis. 23 matches passed the checks and are now available in Predictions.”

### Reliability-tier semantics (proposed governance; requires implementation/validation)

- **Strong:** sufficiently rich, reliable, consistent inputs and a calculation path whose reliability is supported by validation.
- **Medium:** meaningful evidence remains, but notable gaps or uncertainty reduce reliability; a tested fallback/robust calculation may apply.
- **Low:** substantial data limitations or uncertainty; conservative estimates may be possible but must be explicitly flagged and must still pass the publication eligibility gate.

These tiers are not certification substitutes, not guarantees of match outcomes, and must not be assigned solely by arbitrary probability cutoffs. This clarification expands the Stage 8 design requirements; it does not assert that sparse-data fallback inference or these tier labels already exist in production.


## Stage roadmap consolidation — 2026-11-19

**User direction:** update the project stages and document the remaining work properly, distinguishing already-built components from unfinished implementation and validation.

- Created the canonical staged roadmap: [`docs/roadmap/VELTRIX-AI-ANALYST-IMPLEMENTATION-ROADMAP.md`](../roadmap/VELTRIX-AI-ANALYST-IMPLEMENTATION-ROADMAP.md).
- Roadmap commit: `042d2009ec7d0a454607d34abe4f9b9b642ce55a`.
- The roadmap consolidates Stages 1–9 and explicitly records status, exit criteria, dependencies, release blockers and immediate execution order.
- Stages 1–3 are recorded complete/applied; Stage 4 active; Stage 5 applied with unresolved conflicts/restrictions; Stage 6 implemented and accumulating prospective labels; Stage 7 evaluator/gates implemented but certification evidence insufficient; Stage 8 model capability completion and production inference not complete; Stage 9 Android integration/runtime verification pending.
- Stage 8 is split into model/feature inventory, governed calculation engine, reliability tiers, validation/artifact governance and daily inference/publication.
- Stage 9 records integration into the existing Android UI only, including prediction updates, History/settlement and in-app Notifications in Menu. No redesign, Telegram or OS push requirement is introduced.
- Explicitly retained the user's sparse-data requirement: missing data must remain explicit; governed hierarchical/shrinkage fallbacks may be used when tested; Strong/Medium/Low represent evidence reliability, not outcome probability.
- The roadmap does not claim the post-PR119/120 Stage 7 run, certified model artifact, production publisher, or Android end-to-end integration has been verified.
- No code, database records, workflows, production predictions, odds credits or Android UI were changed by this documentation update.

### Next action

Execute Stage 7 live verification, then Stage 8A source/test/workflow inventory. Record exact model paths, call sites, test coverage, and whether each intended model/feature is integrated, partial, missing or obsolete before implementing further calculations.


## Execution checkpoint — Stage 7 live verification and Stage 8A source audit

**Date:** 2026-11-19  
**Main commit at Stage 7 evaluation:** `ab5256c07667a42a726ea0c0649da6c08141502a` (PR #120 merge)

### Stage 7 — live evaluation verified; certification remains blocked

- Confirmed PR #119 merged at `8289c67d8d5e760c194414db449d415763ccfd85`. Its reviewed production read-only query found 996 eligible historical training-only rows across nine completed import runs, with permitted rights and identity joins. The rows have no PIT pre-match feature lineage and are explicitly `validation_eligible=false`.
- Confirmed PR #120 merged at `ab5256c07667a42a726ea0c0649da6c08141502a`, adding Stage 7 push-path triggers for evaluator and prospective dataset code.
- Confirmed the post-merge Stage 7 Actions run: **44611934649**, job **135870539360**, completed successfully on main commit `ab5256c07667a42a726ea0c0649da6c08141502a`.
- All seven workflow steps completed, including read-only expanding-window evaluation, independent certification gate application and artifact upload.
- Artifact: `veltrix-stage7-prospective-research-evaluation`, ID **14574020008**, SHA-256 `115126b65634eb2f3f5b4a272ea09613c10fb1e890ff2c468d2418a1f0254c8f`; downloaded and inspected both JSON reports.
- Evaluation result: `INSUFFICIENT_PROSPECTIVE_DATA`; 996 training-only historical labels were included, with training-pool hash `823fb3894d40153217cad1223808d059dd8ecaef548326b39ef19ceb1c01ecae`.
- Prospective evidence: 59 eligible snapshots across 7 competitions and 6 kickoff dates; zero settled prospective labels; zero expanding folds; zero walk-forward validation fixtures in every market.
- The evaluator confirms historical training rows are not counted as prospective validation. The prospective dataset hash is `3ce532aa731f9a9068e294fa415b1748fa187f76c44a55ada9b13fa3a6e48951`.
- All production certification gates remain false; production promotion is `LOCKED`, release eligibility is false and value betting is `LOCKED`. No ROI or bookmaker comparison was evaluated. No odds were used.
- Feature usage in this evaluation remains `HIERARCHICAL_GOAL_RATE_ONLY`; captured shot, possession, attack and event features are not yet consumed by this evaluator.

**Stage 7 conclusion:** the post-PR119/120 execution path and training-only isolation are verified. Stage 7 is **not complete/certified** because prospective labels, validation fixtures and folds are still zero. Continue daily snapshots and post-kickoff label accumulation; do not relax gates.

### Stage 8A — initial live source inventory findings

Verified current main-branch source files and directory inventories:

- Models: `elo.py`, `attack_defence.py`, `hierarchical_poisson.py`, `hierarchical_scoreline.py`, `scoreline.py`, `prediction_engine.py`, `retrospective.py`, `retrospective_report.py`, `chronology_adjudication.py`.
- Features: `admission.py`, `eligibility.py`, `evidence.py`.
- Orchestration: `hierarchical_predictions.py`.
- Research: `compare_models.py`, `retrospective_run.py`, `train_final_model.py`.
- Validation: includes hierarchical tuning, Dixon–Coles estimation, paired baselines/chronological metrics, calibration, prospective dataset/evaluator, evidence-tier calibration and certification gates.
- Relevant tests exist for attack/defence, hierarchical Poisson, scoreline/model engines, prediction engine, hierarchical orchestration, feature eligibility, tier calibration and final training.

**Confirmed status distinctions:**

1. Elo is implemented chronologically and retained as a research comparator; the final retrospective artifact explicitly does not select it for an ensemble.
2. Recency-weighted attack/defence Poisson is implemented and is the model deserialized by the separate production inference boundary.
3. Hierarchical Poisson and its scoreline adapter are implemented and used by the prospective research evaluator and gated hierarchical orchestration.
4. Poisson scoreline/Dixon–Coles market calculations exist for all five required market groups.
5. Hierarchical orchestration is explicitly inert until an approved validated release; it does not call providers or write production predictions.
6. Production inference is a fail-closed boundary requiring a production-approved PIT-certified artifact and verified team mappings. It currently returns `NOT_PUBLISHED`, uncertainty `NOT_YET_CALIBRATED`, and empty coverage metadata.
7. Evidence Strong/Medium/Low scoring already exists in `features/evidence.py`; held-out market/tier calibration metrics already exist in `validation/evidence_tier_calibration.py`. Production derivation, calibrated frozen policy and propagation into published prediction records are not yet verified.
8. The retrospective historical rate model is explicitly non-PIT research and contains a hard-coded no-history rate. It is not an acceptable production sparse-data fallback.
9. The model-family mismatch between production inference (attack/defence artifact) and Stage 7 hierarchical research must be reconciled before model promotion.
10. The Stage 7 report shows captured supporting statistics remain sparse: most team-stat value fields have only 5–6 populated rows per side, and competition rate fields have 9 populated rows, despite coverage metadata being present across more rows.

### Documentation commits

- Roadmap model inventory/integration-gap update: `03aa01a07c8eb3389aea5ec35d06bf48f2b90575`.
- This ledger update records the exact Stage 7 run, artifact and source-audit findings.

### Next action — continue Stage 8A

Trace all production call sites, API routes, artifact creation/promotion schema and workflows. Establish the canonical model family and determine whether any existing model components are actually wired into the prediction API. Then finish the inventory with a precise implemented/partial/not-integrated/missing/test-only matrix before changing model code.


### Stage 8A — second-pass API, artifact and workflow trace

- API router inventory: `backend/app/routes/public_predictions.py` exposes only GET `/v1/predictions` and GET `/v1/predictions/{prediction_id}`. It reads from `published_predictions` and `published_prediction_markets`; it is not a publisher.
- `backend/app/main.py` mounts the readiness and public-predictions routers. No inference or publish route is mounted.
- `backend/app/models/prediction_engine.py` validates a production-approved, PIT-certified attack/defence artifact and verified canonical team mappings, calculates all five market groups, then returns `publication_status=NOT_PUBLISHED`. Its uncertainty status is `NOT_YET_CALIBRATED` and coverage is empty.
- `backend/app/research/train_final_model.py` creates a retrospective attack/defence artifact with `deployment_status=RESEARCH_ARTIFACT_ONLY` and `temporal_certification=RETROSPECTIVE_EVENT_TIME_NOT_PIT_CERTIFIED`; it explicitly retains Elo only as a comparator. This artifact cannot satisfy the production inference gate.
- `backend/app/orchestration/hierarchical_predictions.py` provides a separate in-memory hierarchical forecast/audit path, but is explicitly inert without an approved release and does not persist/publish.
- Workflow inventory contains Stage 6 capture/materialization and Stage 7 evaluation, plus historical/retrospective training workflows; there is no dedicated Stage 8 daily inference/publisher workflow.
- Inspected `backend/app/db/store.py` for published prediction/model artifact write methods; no matching prediction publication insertion method was found in that module. This is scoped to that file, not a full SQL migration audit.

### Corrected Stage 8A position

Stage 8A is **partially complete**: model, feature, tier, inference boundary, API read contract and workflow inventory have been mapped. Remaining audit work is to inspect migrations and all persistence interfaces, verify artifact registry/promotion semantics, trace actual model inference call sites and finish a source-to-API data-flow diagram. No prediction code has been changed.


### Stage 8A — migration/storage audit correction

A subsequent migration audit refined the publication gap:

- `backend/migrations/008_model_artifacts.sql` defines immutable model-artifact registry storage with dataset fingerprint, training cutoff and PIT-certification flag.
- `backend/migrations/014_prediction_publication_storage.sql` already defines feature snapshots, predictions, per-market probabilities and append-only publication events, with database triggers enforcing PIT chronology, approved PIT-certified model artifact, verified/reconciled fixture identity, all 11 market outcomes and immutable publication history.
- Migration 014 also defines `published_predictions` and `published_prediction_markets` views consumed by the public GET API.
- Therefore prediction/publication **database storage and enforcement are already built**. The missing component is the application-level inference orchestration/persistence writer and its scheduled workflow/API integration—not the underlying schema.
- Earlier observation that `backend/app/db/store.py` has no matching prediction insertion method remains true for that application module, but must not be interpreted as absence of database publication storage.

Roadmap wording was corrected accordingly in commit `96b57eab50285a1f586c27e1766fad28f9cff40d`.


### Stage 8A — production Neon artifact/publication state (read-only)

Project `young-wind-27772160`, default production branch `br-jolly-darkness-balgmi2t`, database `veltrix_ai_analyst` was queried using read-only SELECT statements only.

- `model_artifacts`: 2 rows.
- Both artifacts are `RECENCY_WEIGHTED_ATTACK_DEFENCE_POISSON`, 380 training fixtures and 20 provider teams, cutoff 2026-11-14 19:30 UTC.
- Both have `point_in_time_certified=false`, `deployment_status=RESEARCH_ARTIFACT_ONLY`, and `temporal_certification=RETROSPECTIVE_EVENT_TIME_NOT_PIT_CERTIFIED`.
- `predictions`: 0 rows.
- `prediction_publication_events`: 0 rows.
- `published_predictions`: 0 rows.
- `prediction_feature_snapshots` (production inference snapshots, distinct from Stage 6 prospective research snapshots): 0 rows.

**Interpretation:** the repository has a production inference boundary and database publication schema/gates, but there is currently no production-approved model artifact and no published production predictions. This confirms Stage 8 must not be treated as a wiring-only release; model artifact PIT certification and application-level inference/persistence are both outstanding.

No database rows were changed. No provider or odds API was called. No migration was applied.


### Stage 8A — source-to-production inventory closed

**Status: COMPLETE.** The audit covered model modules, feature modules, research and validation code, test inventory, API routes/contracts, application entrypoint, workflows, migrations and production Neon artifact/publication state.

Canonical classification:

| Capability | Classification |
|---|---|
| Elo | Implemented; retrospective comparator only |
| Attack/defence Poisson | Implemented; production inference boundary supports it, but only research artifacts currently exist |
| Hierarchical Poisson | Implemented; used by Stage 7 research evaluator and separate gated in-memory orchestration |
| Poisson scoreline/Dixon–Coles | Implemented; derives all five market groups |
| Competition/global pooling for unseen teams | Implemented in hierarchical model as zero-centered unseen team effects with retained competition/global context; not connected to production inference artifact |
| Hard-coded retrospective no-history rates | Exists, but research-only and not approved as production fallback |
| Strong/Medium/Low evidence scoring | Implemented as a policy-driven scorer |
| Tier-by-market calibration diagnostics | Implemented; no production-calibrated policy/propagation verified |
| PIT feature admission and rights/identity checks | Implemented |
| Production inference contract | Implemented fail-closed; no qualifying production artifact exists |
| Prediction/publication database schema and triggers | Implemented in migrations 008 and 014 |
| Public prediction read API | Implemented; GET-only over published views |
| Application inference/persistence writer and daily publisher | Missing |
| Production-approved PIT model artifact | Missing; both production artifacts are research-only |
| Production prediction rows/publications | None at audit time |
| Android UI | Existing UI preserved; end-to-end live prediction integration remains pending |

**Stage 8A is complete. Stage 7 certification remains blocked separately** by zero settled prospective labels/folds and must continue accumulating evidence. The next build work is Stage 8B: governed calculation and sparse-data inference; Stage 8C: reliability policy calibration and production propagation. No production code has been changed during this audit.


## Stage 8B kickoff — feature/outcome pairing constraint

- `backend/scripts/build_prospective_dataset.py` constructs historical training-only rows with `features={}` and `feature_lineage=()`. These 996 records are outcome/identity/competition training evidence, not historical PIT snapshots for the supporting match-stat features.
- The 59 current upcoming prospective snapshots contain PIT feature values and lineage, but currently have zero settled labels.
- Therefore, fitting feature coefficients for shots, possession, attacks, corners, cards, event metrics or other supporting features from the 996 rows would be invalid. Do not fabricate historical feature values, infer them from final scores, or use upcoming features without outcomes as supervised training examples.
- The currently defensible near-term path is to develop and test the existing hierarchical goal-rate model using the eligible historical outcome pool for team/competition partial pooling, including its unseen-team neutral-effect behavior. Keep sparse supporting feature fields explicit and use them for measured coverage/evidence diagnostics only until paired PIT feature/outcome examples or a separately rights-cleared historical feature corpus exists.
- Once prospective fixtures settle, the label materializer can pair each immutable snapshot with its append-only outcome label for feature-model development and later prospective validation. Historical training-only rows still cannot count as prospective certification.
- This finding is recorded in the roadmap under Stage 8B. No model code or data was changed.


## Stage 8B implementation checkpoint — sparse calculation provenance

**Date:** 2026-11-19  
**Branch:** `stage-8b-sparse-inference-governance`

### Implemented on branch

- Updated `backend/app/models/hierarchical_poisson.py` so each forecast rate reports an explicit calculation mode based on actual fitted history counts and competition membership:
  - `TEAM_AND_COMPETITION_HISTORY`
  - `ONE_SIDED_TEAM_HISTORY`
  - `COMPETITION_ONLY`
  - `TEAM_HISTORY_GLOBAL_CONTEXT`
  - `GLOBAL_CONTEXT_ONLY`
- The calculation continues to use the existing hierarchical attack/defence effects, competition effect and global intercept. Unseen team effects remain zero-centered under the existing ridge-regularized model; no fabricated team observations or arbitrary minimum-count thresholds were introduced.
- Updated `backend/app/orchestration/hierarchical_predictions.py` to carry calculation mode, per-side training history counts and competition-seen status into `PredictionAuditRecord`. The audit provenance is computed independently of scoreline construction so it remains available when market calculation fails.
- Extended `backend/tests/test_hierarchical_poisson.py` to assert the explicit mode for one-sided, competition-only, global-only, team-plus-competition and known-team/unseen-competition cases.
- Extended `backend/tests/test_hierarchical_orchestration.py` to assert provenance is carried into the audit record.

### Capture and dataset integrity review

Inspected `backend/app/validation/prospective_dataset.py` and `backend/tests/test_prospective_dataset.py`.

Verified source behavior in code:
- Target rows require a system-observed, PIT-certifiable scheduled snapshot before kickoff with valid feature-engineering/training/validation rights.
- Prior-match features are sourced only from earlier finished fixtures whose qualifying observations were observed by the target snapshot cutoff and pass rights checks.
- Missing rolling features remain absent; explicit coverage counters remain available.
- Target labels are attached only from a qualifying finished observation observed after the target kickoff.
- Existing tests exercise pre-cutoff filtering, post-kickoff schedule exclusion, retrieval-only exclusion, no-history missingness, one-sided history and rolling-stat/event derivation.

The next capture must therefore remain a capture-only evidence operation. It must not train or validate from a snapshot whose own fixture has not settled and must not backfill supporting statistics from the historical outcome-only import pool.

### Verification status and limits

- Changes are committed to the feature branch; no production branch changes have been made.
- PR #121 triggered GitHub Actions run **44621336631**. Run attempt 2 completed the Backend tests and lint job successfully: package installation, full backend test command and lint all passed. Android debug build was cancelled in both attempts before APK assembly (the SDK-install step was cancelled/skipped); no APK result is available. Android source was not changed by this PR, so this is not a backend test failure, but the check is not a successful build. The successful backend job ran against code commit `ecc45aec61a87eb44c780421907e10690b53c62f`; the later branch-head update only amended the ledger. Do not merge until required checks reach a terminal passing state. The Vercel status check separately reported a deployment rate limit with a 24-hour retry window; no deployment was attempted by this work.
- No provider API, The Odds API, Neon write, production migration, artifact promotion or prediction publication was performed.
- Stage 7 certification remains blocked until prospective settled labels and walk-forward evidence accumulate.
- Stage 8B remains in progress; this checkpoint adds auditable sparse-path provenance but does not yet complete hyperparameter selection, stress validation, feature model training or production integration.

### Next actions

1. Finish the sparse-mode test matrix and run CI on the branch.
2. Run existing hierarchical stress/validation suites and chronological tuning against eligible historical outcomes only.
3. Verify that each training label was available by the fold's prediction cutoff before it enters a fit; preserve historical-only rows as training-only.
4. Update the dated ledger with exact workflow run/job/test results.
5. Keep the next scheduled Stage 4 capture enabled; inspect its artifact and inserted-row lineage after it runs, without using upcoming unlabeled snapshots as supervised training data.


## Stage 8B continuation — cutoff-safe tuning and historical feature recovery

**Date:** 2026-11-19  
**Branch:** `stage-8b-sparse-inference-governance`

### Production data audit (read-only)

Neon project `young-wind-27772160`, production branch `br-jolly-darkness-balgmi2t`, database `veltrix_ai_analyst`:
- Historical finished outcome pool: **996** fixtures.
- Stored statistics objects: **6**.
- Stored events arrays: **6**.
- Fixtures with corners fields: **996**.
- Seven approved competition scopes; per-scope finished rows: 122, 110, 90, 100, 113, 380 and 81.
- No production rows changed.

The existing provider adapter requests `include=stats,events` for fixture history, and the importer writes each response as a new immutable source observation. This creates a legitimate recovery route: re-fetch the already-approved historical competition windows with stats/events. New observations are captured at the actual retrieval time. They do not rewrite or backdate prior observations and cannot become historical PIT validation evidence.

### Backfill path implemented (not executed)

- Added `historical_feature_backfill` as a distinct import type in the existing importer and collection CLI.
- Added `.github/workflows/historical-feature-evidence-backfill.yml`, manual-dispatch only. It serializes against the prospective capture workflow, checks the production database identity, probes safe 5Dollar entitlement/quota fields, and defaults to preflight-only. A separate explicit boolean input is required before any historical requests are sent.
- The backfill command is bounded to the seven already-approved competition scopes and uses the existing durable request reservations, raw-response provenance, rights approval and append-only source observation path.
- It has **not** been dispatched and no 5Dollar API requests were made by this work. Review the entitlement output before setting the execute input. The Odds API was not called.

### Fold cutoff enforcement implemented

- `hierarchical_tuning.select_hierarchical_hyperparameters` now accepts `label_available_at` and filters each fold's training pool by both kickoff and actual label availability. An optional `evaluation_as_of` prevents scoring labels not yet available by the research run.
- Strict mode reports protocol `EXPANDING_WINDOW_LABEL_AVAILABILITY_AWARE_PAIRED_POISSON_NLL_V2`.
- Outer and inner prospective evaluator folds now reject any training row whose label was observed after the recorded `train_cutoff_at`; training rights are evaluated at that cutoff; model fitting uses that exact cutoff for recency weights.
- Added tests for delayed import labels, strict tuning, and an intentionally unsafe fold cutoff.

### CI evidence

- CI run **44622722383** on commit `02265a994489207354568f04a52f7919424e94bd`: Android debug build passed; backend suite had 432 passing and one failure caused by an incorrect expected validation count (actual 9, expected 10).
- The expected count was corrected. New CI run **44623277785** on the subsequent branch head was in progress at the time of this ledger update; fetch its terminal job results before declaring the suites passed.
- The earlier run's single failure was in the new synthetic test expectation, not a model convergence failure. No claim of final suite pass until the re-run is complete.

### Remaining blocker and next work

The historical outcome model can train now from the 996 approved results using actual import-completion availability. The missing supporting-feature pool is a source-payload coverage problem: only 6/996 observations currently contain statistics/events. Backfill is prepared but deliberately not run until the 5Dollar quota/entitlement preflight has been reviewed.

After backfill:
1. Build a separate retrospective *training-only* lagged feature dataset from each fixture's earlier same-competition matches, preserving actual source-observed timestamps and rights.
2. Mark all retrospective reconstructed feature rows non-PIT and validation-ineligible; never use them for Stage 7 certification.
3. Train a research-only feature model on the reconstructed lagged covariates and compare against hierarchical goal-rate-only baseline on future prospectively captured and settled fixtures.
4. Re-run the strict chronological tuning/stress suites and inspect the full CI run before merging PR #121.


## Stage 8B continuation — retrospective lagged feature reconstruction

**Date:** 2026-11-19  
**Branch:** `stage-8b-sparse-inference-governance`

### CI checkpoint before new feature module
CI run **44624312572** on commit `62a53cd44ff1b79c19368318a21be3c843a911e3` completed successfully:
- Backend tests and lint: success.
- Android debug APK build: success.
- Backfill workflow YAML validation: success; its collection job was skipped because the workflow defaults to preflight-only.

### New research-only feature builder

Added:
- `backend/app/validation/retrospective_features.py`
- `backend/tests/test_retrospective_features.py`

The builder reconstructs lagged team covariates from strictly earlier fixtures in the same competition:
- Goals for/against means.
- Corners for/against means.
- Cards for/against means where both yellow/red components exist.
- Per-team prior match counts and exact source fixture IDs.

Leakage controls:
- A target fixture is not inserted into its own history until after its features are emitted.
- Same-kickoff fixtures are simultaneous and cannot contribute to one another.
- Competition boundaries are isolated.
- Missing corners/cards remain null; no fabricated imputation.
- All output rows are marked `validation_eligible=false`, `point_in_time_certifiable=false`, and `source_available_before_target_kickoff=false`.

This is retrospective event-time reconstruction, not a claim that VELTRIX possessed the feature values before the target kickoff. It can support research model fitting, but never prospective certification or production PIT artifacts. It provides a way to research the 996-match outcome pool with available lagged goals/corners/cards before the 5Dollar stats/events backfill is available. Shots and possession still require recovered statistics payloads.

### Verification pending
New CI run is expected from commit `bc78d86b8ed404656a1869164d7c0fa2202f832c`; do not claim the new feature tests pass until its backend and Android jobs finish. Next integrate the retrospective rows into a separate training-only candidate dataset, compare against hierarchical goal-rate-only baseline, and keep prospective evaluator input strictly separate.


## Stage 8B — actual fold availability audit and strict research tuning

**Date:** 2026-11-19  
**Branch:** `stage-8b-sparse-inference-governance`

### Read-only production availability audit

Database: `veltrix_ai_analyst`, production branch `br-jolly-darkness-balgmi2t`.

The latest qualifying finished sighting per fixture was used. For non-PIT historical records, `retrieved_at` is used as the actual observed/retrieved availability time; it is never promoted to a PIT timestamp.

- Settled historical results: **996**.
- Available by the audit timestamp (2026-11-19 22:00 UTC): **996**.
- `RETRIEVED_AT_ONLY`: **990** (non-PIT).
- `SYSTEM_OBSERVED_AT`: **6**.
- Availability range: 2026-11-16 21:12:28 UTC through 2026-11-19 05:38:39 UTC.

Actual configured fold checks (training eligibility requires both kickoff and availability at/before the training cutoff):
| Fold cutoff | Kickoff-prior rows | Labels available at cutoff | Validation labels known by evaluation time |
|---|---:|---:|---:|
| 2026-09-15 | 505 | 0 | 91 |
| 2026-09-30 | 596 | 0 | 35 |
| 2026-10-10 | 631 | 0 | 131 |

**Result:** zero valid development folds. The old event-time split had treated historical match dates as if VELTRIX had known the results then. That assumption is false: the 996 labels were imported in November. The seven-competition hierarchical runner now checks actual label availability before tuning and writes `INSUFFICIENT_LABEL_AVAILABILITY_FOR_CHRONOLOGICAL_TUNING` without fitting or scoring a false holdout.

The 996 outcomes remain useful as a current retrospective training pool because they are all available now. They cannot be used to claim September/October walk-forward performance or PIT certification. The 990 retrieval-only records remain explicitly non-PIT.

### Strict tuning implementation

- `hierarchical_tuning.py`: strict mode requires complete `label_available_at` coverage and `evaluation_as_of`; training labels must be available at the fold cutoff; validation labels must be available by evaluation time; future fold cutoffs are rejected.
- `dixon_coles.py`: same availability checks for every inner OOF fit and scored label; strict protocol is `OOF_DIXON_COLES_PROFILE_NLL_LABEL_AVAILABILITY_AWARE_V2`.
- `evaluate_seven_competition_hierarchical.py`: uses latest sighting system-observed time or, for explicitly non-PIT rows, retrieved time; records basis counts and fold audit; exits with an explicit insufficient-evidence report when no fold is eligible.
- Added tests for delayed labels, missing evaluation-as-of, and Dixon–Coles OOF label filtering.

### CI evidence

- CI run **44623823396**, commit `d553cfd24b91d64f051c745db8e9219f28718cc3`: **433 tests passed**, lint passed, Android debug APK assembled and uploaded.
- That run predates the latest Dixon–Coles strict-cutoff and seven-competition runner changes. Current branch-head CI run **44625309292** was interrupted by a subsequent branch update; the newest run **44625309292** is not a terminal verification for the final branch head. Fetch the latest run for commit `2214baaca9d7dd8ca70dea7f560cde0dc89d67fe` before merge.
- Historical feature backfill workflow YAML was corrected after a push-validation failure caused by an unquoted colon in a `run:` scalar. The corrected workflow validation run **44624298002** succeeded. It performed no DB/provider operations.

### Remaining research-data path

1. The model may fit the 996 outcomes now as a current research-only candidate, using actual current training cutoff and no claim of historical fold validation.
2. Keep prospective Stage 4 captures running. Once their target fixtures settle and labels are observed, use those immutable paired snapshots/outcomes for real chronological folds.
3. Run the separate historical feature backfill only after the workflow's 5Dollar entitlement/quota preflight is reviewed. The database audit showed only 6/996 historical observations currently have stats/events; all 996 have corners.
4. Build lagged retrospective feature training rows separately and mark them non-PIT/validation-ineligible. Never use them to satisfy Stage 7 certification.
5. Stage 7 certification and production promotion remain blocked until prospective labels, valid folds and all certification gates pass.


## Stage 8B — retrospective feature builder correction and verified CI

**Date:** 2026-11-19  
**Branch:** `stage-8b-sparse-inference-governance`

### Research model data recovery clarification

The research path was not limited to stats/events. The repository already has `backend/app/validation/retrospective_features.py`, which reconstructs lagged training features from strictly earlier same-competition fixtures:
- goals for/against rolling means;
- corners for/against;
- yellow/red-card aggregates;
- prior-match counts and missingness preserved.

All 996 current settled historical rows contain goals, corners, yellow cards and red cards. Only 6/996 have statistics objects/events arrays. Therefore the first feature-aware research model can use the existing 996 outcomes plus corners/cards now; a stats/events backfill can add shots, possession, attacks and event-derived features later.

The retrospective feature builder explicitly sets `validation_eligible=false`, `point_in_time_certifiable=false`, and `source_available_before_target_kickoff=false`. It is training-only and must not be treated as a historical PIT replay or prospective validation dataset.

### Defect fixed

The retrospective feature builder sorted by kickoff and fixture ID, then added each fixture to history immediately. This allowed a simultaneous fixture with a lexically earlier ID to leak into another fixture's features at the same kickoff. Reworked it to process equal-kickoff fixtures as atomic blocks: compute all feature rows from strictly earlier kickoff blocks, then append the entire block to history. The previously failing regression now covers the exact scenario.

### Final verification

- CI run **44625656408** on branch commit `8d493797a9e43b3d8699a26cb071fe3baed32d37`.
- Backend: **439 passed**, 1 warning, no failures.
- Ruff: **All checks passed**.
- Android debug build: assembled successfully; APK upload step passed.
- Historical feature-backfill workflow YAML validation: run **44624298002** passed on push with no database/provider access.
- PR #121: open, mergeable, not merged.
- No production database rows changed, no migrations applied, no provider API or The Odds API requests sent, and no deployment attempted.

### Next Stage 8B task

Connect the existing read-only seven-competition production source loader to `build_retrospective_lagged_features`. Persist the generated feature/outcome dataset as a content-addressed research-only artifact with per-row source observation IDs, retrieval timestamps, rights lineage and explicit non-PIT flags. Train a feature-aware Poisson candidate on this dataset and compare it with the goal-rate-only hierarchical baseline as development research only. Do not use retrospective rows for Stage 7 certification. Prospective snapshots must continue accumulating settled labels for valid chronological evaluation.


## Stage 8B continuation — isolated retrospective research dataset assembly

**Date:** 2026-11-19  
**Branch:** `stage-8b-sparse-inference-governance`

### Branch and CI re-verification
- PR #121 remains open, unmerged, and mergeable.
- Branch head at start of this continuation: `de89d61726b6c25394b8d999c816c69a0344bb43`.
- Latest CI run on that exact head: **44625959262**, conclusion `success`.
- Backend tests/lint job **135919744188**: success.
- Android debug build job **135919744654**: success; APK upload step succeeded.
- This CI predates the new dataset builder commits below and is not verification of those commits.

### New separate dataset builder
Added `backend/app/research/retrospective_feature_dataset.py`.
- Loads provider-local finished fixtures from `provider_fixtures` with a read-only transaction and checks the exact database name.
- Joins source observation, response, retrieval timestamp, rights approval, permitted uses and source payload hash.
- Requires current rights status APPROVED, FEATURE_ENGINEERING and MODEL_TRAINING permissions, and approval validity at retrieval time; fails closed otherwise.
- Uses `build_retrospective_lagged_features` to construct strictly earlier same-competition features.
- Joins labels by fixture ID and carries source observation/response IDs, retrieval timestamp, availability basis, payload hash and rights lineage.
- Writes a local content-addressed JSON artifact; it does not persist research rows to Neon.
- Dataset envelope and every row are explicitly non-PIT, `validation_eligible=false`, `certification_eligible=false`; it declares no prospective dataset join.
- No production DB writes, provider calls, Odds API calls, deployment, or Android UI changes.

Added `backend/tests/test_retrospective_feature_dataset.py` for row-label joins, non-PIT flags, source lineage, simultaneous-kickoff isolation and content-addressed output.

### Commits
- `daaf714b4514b4a904f87e781004eefb82a0f242` — add isolated retrospective research dataset builder.
- `73911609c4d920a3b993d7a2d4a6b6a988b7f2c1` — add dataset/provenance tests.
- `5d79f5cd50e0122b6f6a11ce2cc5b7d62cf13b35` — enforce research rights lineage before dataset construction.

### Verification status and next work
- The dataset assembly implementation is committed but has not yet run against production Neon or passed CI on the new head.
- Feature-enhanced candidate training and matched comparison against the hierarchical goal-rate-only baseline are NOT implemented or verified yet.
- Competition, team-history-depth and feature-coverage slices are NOT yet computed.
- Chronological stress/tuning suites have NOT yet been rerun after dataset integration.
- Do not merge PR #121 until the new CI is green, dataset artifact is built and audited, candidate comparison is reproducible, and stress/tuning tests pass.
- Prospective Stage 7 input remains completely separate. No retrospective row may enter prospective folds, label counts or certification.


## Stage 8B continuation — retrospective dataset integration and lint correction

**Checkpoint:** 2026-11-19 23:57 WAT  
**Branch:** `stage-8b-sparse-inference-governance`  
**PR:** [#121](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/121)

### Live CI verification

- Re-fetched PR #121 and Actions run `44629918283` from GitHub.
- Run `44629918283` concluded `failure`.
- Backend tests: **444 passed**, 1 warning.
- Android debug build and APK upload: **passed**.
- Ruff lint: failed with 12 `UP017` findings in the newly added retrospective feature dataset builder and its tests. The earlier conversational checkpoint incorrectly described this run as green; this ledger corrects that status.

### Lint correction commits

- `db2d28181b4385ae7d4e699fc58fa4c987b6ee7c` — replace `timezone.utc` with `datetime.UTC` in `backend/app/research/retrospective_feature_dataset.py`.
- `cb6458b35556f889afdd40c82c694f58018d460d` — apply the same lint correction in `backend/tests/test_retrospective_feature_dataset.py`.

These commits correct the 12 reported Ruff findings. A new CI run must verify the correction; no green result is claimed yet.

### Research dataset boundary

The retrospective dataset builder and tests are present on the branch. The builder:
- Reads provider-local completed fixture rows using a read-only transaction.
- Requires approved rights for both feature engineering and model training.
- Joins reconstructed lagged features to fixture outcome labels.
- Preserves source observation, provider response, retrieval time, rights and payload-hash lineage.
- Writes a local content-addressed artifact; it does not write production database rows.
- Marks the dataset and every row ineligible for prospective validation/certification and records non-PIT provenance.

The builder has **not** yet been executed against production Neon. No row count or dataset artifact is claimed.

### Remaining Stage 8B work

1. Verify the new CI run after the two lint-fix commits.
2. Audit the complete dataset builder against the existing query schema and execute it read-only against the approved production corpus.
3. Implement a separate feature-enhanced research candidate and matched chronological comparison against the hierarchical goal-rate-only baseline.
4. Report results by competition, team-history depth and feature coverage.
5. Keep retrospective rows entirely outside the prospective validation/certification pool.
6. Rerun chronological stress tests and nested tuning after candidate integration.
7. Review the full PR diff and latest CI before any merge decision.

### Manual historical backfill

The manual workflow `.github/workflows/historical-feature-evidence-backfill.yml` remains undispatched. The first user dispatch must use `execute_backfill=false` (preflight-only). No provider request or The Odds API request was made in this checkpoint. Do not notify the user to dispatch until engineering integration, research comparison, chronological tests and CI prerequisites are verified.

### Release boundary

PR #121 remains open and unmerged. No production deployment, production prediction publication, model promotion, certification, or value-bet unlock is authorized by this research work.


## Default-branch historical entitlement preflight — verified

**Date:** 2026-11-20 (workflow run timestamp: 2026-11-19 23:17 UTC)  
**Default-branch workflow commit:** `7291c90c3cbf89fe0e5f13bbcb129c3a2c9152a9`  
**Workflow:** `.github/workflows/historical-feature-evidence-preflight.yml`  
**Run:** [44636268137](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44636268137)  
**Job:** `135955473604`

- Added a separate `workflow_dispatch`-only, preflight-only workflow directly on `main`, so the user can access the manual trigger without merging PR #121.
- Workflow file was fetched back from `main` after commit; SHA `5803b990d670cb629a48ab809b0c2c7938d25212`.
- Job conclusion: SUCCESS. Backend installation, database identity verification, explicit read-only transaction, provider entitlement probe and no-collection confirmation all passed.
- Provider response: plan `community`; `limits.rate_limit=300`; `daily_limit=null`; `daily_reset_at=null`.
- Interpretation: 300 is a rate-limit field, not verified remaining quota. The response does not establish daily remaining requests or a safe historical collection budget. Do not launch historical backfill based on this result alone.
- No historical fixture collection was run. No production database writes occurred. The Odds API was not called.
- The separate workflow has no collection input or collection step; it is strictly an entitlement preflight.

### Next actions
1. Determine whether 5Dollar exposes a documented quota/usage endpoint or dashboard value that can establish remaining request budget; do not infer it from `rate_limit`.
2. Preserve the backfill lock until remaining quota and request-cost semantics are verified and the bounded collection plan is reconciled with the provider limit.
3. Continue Stage 8B research dataset execution/training comparison independently; do not merge PR #121 until its stated research and CI gates pass.


## Provider dashboard rate-limit clarification

**Date:** 2026-11-20  
**User-verified dashboard value:** 300 requests per hour.

- User checked the 5DollarFootballAPI dashboard and confirmed the displayed allowance is 300 requests/hour; this agrees with the preflight entitlement response `plan=community`, `rate_limit=300`.
- The configured backfill bounds are seven approved competitions × ten requests per competition = 70 maximum reserved provider requests across the batch. The shared provider client enforces a 60-second minimum interval, i.e. at most 60 requests/hour from this job.
- Therefore the configured batch is below the stated hourly rate limit. This does not establish a separate monthly/account-wide remaining-credit balance; do not describe 300/hour as 300 total credits.
- No collection was started by this clarification. Keep actual execution behind the explicit workflow dispatch gate until the workflow is exposed on the default branch and the selected branch/code is verified. No Odds API calls.


## Default-branch backfill workflow exposure

**Date:** 2026-11-20  
**Main commit:** `6b6c045a50572cf22f12d6ca95038fca81d91b36`  
**Workflow:** `.github/workflows/historical-feature-evidence-backfill.yml`

- Added the bounded manual backfill workflow to `main` so GitHub exposes the workflow dispatch UI without merging unfinished PR #121.
- Fetched the committed workflow back from `main`; file blob SHA `4171c195d0871fb0f36cfac2c373b10085afc69c`.
- Dispatch must select branch `stage-8b-sparse-inference-governance`. The workflow checks out `github.ref`, so the importer implementation and workflow-dispatch run both use the selected Stage 8B branch, not the older main importer. The workflow definition itself is present on default branch for discoverability.
- Default input `execute_backfill=false` remains preflight-only. Actual collection requires explicitly setting it to true.
- Execution scope: seven approved competitions; 10-request per-competition cap (70 total maximum); one request per 60 seconds; 365-day window; import type `historical_feature_backfill`; existing reservation/checkpoint/resume controls remain active.
- Provider dashboard allowance was confirmed by user as 300 requests/hour with hourly reset. The configured 60-second interval is 60 requests/hour, below that rate limit.
- PR #121 remains open and unmerged. No dispatch has been performed; no historical provider collection has started; no Odds API calls were made.

### Manual step now available
Open [the workflow page](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-feature-evidence-backfill.yml), choose branch `stage-8b-sparse-inference-governance`, set `execute_backfill=true` to launch the bounded collection, then click Run workflow. The workflow will first verify database identity and probe provider entitlement before collection. Send the resulting run URL for monitoring and validation.


### Historical feature backfill execution and reconciliation failure (2026-11-20)

- Manual workflow run [44637566125](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44637566125), job 135959917939, ran on branch `stage-8b-sparse-inference-governance` and exited failure (exit code 1).
- Independently verified in Neon: all seven historical import runs (IDs 19–25) completed. Aggregate: 1,601 records seen, 595 inserted, 0 rejected/quarantined, 35 provider requests used. Competition breakdown: Brazil Serie A 289/165/6; Brazil Serie B 384/0/8; England Premier League 180/79/4; France Ligue 1 166/75/4; Germany Bundesliga I 155/74/4; Italy Serie A 200/90/4; Spain La Liga 227/112/5 (seen/inserted/requests).
- The workflow validation step rejected every scope with `FIXTURE_SIGHTING_COUNT_MISMATCH` and `IMPORT_COUNTER_RECONCILIATION_FAILED`; Brazil Serie B also had `NO_FIXTURE_DATA_IMPORTED`. The batch summary therefore reported 7 failed competitions despite all DB import-run statuses being COMPLETED. Treat collection as completed but validation FAILED; do not claim recovered payload coverage or certified reconciliation yet.
- Run logs are available and were independently inspected. The per-competition validation output includes fixture row and sighting counts; the validator is currently failing its reconciliation checks.
- Production database measured 23 MB after run (24,150,016 bytes), versus prior 22 MB. No immediate storage concern relative to 5 GB.
- No Odds API requests were used. Provider request usage total was 35 across the seven scopes.
- Next: diagnose sighting/counter reconciliation and Brazil Serie B zero-row condition; audit stored observations/payload completeness and lineage read-only; repair validation accounting with tests; do not blindly repeat the provider collection or spend additional requests until diagnosis.


### Historical feature backfill reconciliation diagnosis and code repair (2026-11-20)

- Read-only Neon audit of import runs 19–25 confirms 1,601 fixture sightings across seven competition scopes. Each scope's fixture sighting count exactly equals records_seen (289, 384, 180, 166, 155, 200, 227).
- Six scopes materialized 595 new provider_fixtures rows. Brazil Serie B had 384 fixture sightings and zero new rows because its fixtures were already present; the importer preserved the original fixture provenance pointer, so these new sightings correctly do not join through provider_fixtures.source_observation_id. This is not evidence of missing observations.
- Root cause 1: FixturePagePersister incremented records_duplicate in memory but the successful-page checkpoint omitted duplicate/rejected/quarantined counters. _finish() aggregates checkpoint totals, so duplicate accounting was lost and import-run counters falsely failed reconciliation.
- Root cause 2: validator incorrectly required fixture sightings to equal newly inserted fixture rows. Sightings represent every observation; inserted rows represent only new identities. Correct invariant is sightings = records_seen and materialized fixture rows = records_inserted.
- Code repair commits on stage-8b-sparse-inference-governance:
  - f588751b212de77be0f78f70754596264dc8b529 — persist all page counters.
  - 162a624e3b5cbf4d28e6995256715ec3729411db — separate sighting and insert validation; recover legacy duplicate totals only when evidence permits.
  - 7a9244df67bc105bb84047fcda1314c7445f35a8 — regression test for duplicate fixtures and checkpoint accounting.
- The validator's legacy recovery is read-only: it reports inferred duplicate count only when stored duplicate counters are absent, there are no rejected/quarantined records, and later sighting/row checks independently reconcile seen and inserted counts. It does not rewrite historical ledger rows.
- No provider requests, Odds API requests, production database writes, or deployments were made for this repair. CI and PR review are pending; historical backfill remains collection-completed / validation-not-yet-recertified until the corrected validator is run against the existing runs.

- Follow-up correction `681ff63b52b307315ad4b1913e22a30e9b9bb90c`: a scope with zero newly inserted rows is not automatically empty. The no-data gate now checks for zero records/sightings, allowing Brazil Serie B's fully observed duplicate-only scope to validate when all other evidence reconciles.


### 2026-11-20 — reconciliation repair audit and current evidence

- Rechecked PR #121: open, unmerged; current head `4c655469dd023329f71bed97077112a3d9f0263a`. The only CI run at `507163ea4df4f04a78938d53a4c975a94ba99fb0` changed the roadmap file only; backend tests/lint and Android build passed there, but this is not CI evidence for the later validator/importer code commits. A fresh full CI run on the current head is still required.
- Read-only Neon checkpoint reconciliation for import runs 19–25: each run has one completed checkpoint; checkpoint seen/inserted/requests match run totals exactly (289/165/6, 384/0/8, 180/79/4, 166/75/4, 155/74/4, 200/90/4, 227/112/5). Legacy duplicate counters in the stored run/checkpoint rows are zero because the old writer dropped them. Evidence-derived duplicate totals are therefore 124, 384, 101, 91, 81, 110, 115 respectively (seen minus inserted), but must be accepted only alongside the independent observation-sighting and materialized-row reconciliations.
- Read-only raw-response audit: 35 stored provider responses account for exactly 1,601 fixture payload objects. For every import run, fixture payload count equals records_seen. The response bodies contain `statistics` and `events` keys on every fixture, but the `statistics` arrays are empty for all 1,601 fixtures. Events arrays are non-empty for 1,584 fixtures (284, 382, 179, 163, 155, 200, 221 by run). No fixture in this backfill contains a `lineups` key. This is event-payload recovery, not recovery of usable statistics/lineups.
- The latest available CI run 44637030091 passed backend tests/lint and Android debug build, but it ran at the earlier SHA `507163ea4df4f04a78938d53a4c975a94ba99fb0`, whose only changed file was the roadmap. It does not test the later four accounting/validator repair commits. No workflow-dispatch action is exposed through the connected GitHub tools, so CI must be triggered by a new PR-branch commit and checked against the resulting head.
- Backfill workflow run 44637566125 is still failed at the collection step because its bundled validator executed the pre-repair code from the run's earlier SHA. The corrected validator has not yet been executed against runs 19–25. Do not rerun collection; use a no-provider, read-only validation path after CI passes.
- No database writes, provider calls, Odds API calls, deployments, or merges were made during this audit. Production promotion, value betting, and Stage 7 certification remain locked.


### Read-only post-repair reconciliation evidence (2026-11-20)

- Re-ran the validator's core database invariants directly as read-only SQL against Neon for import runs 19–25. Results by run: sightings equal records_seen (289, 384, 180, 166, 155, 200, 227); distinct fixture rows equal records_inserted (165, 0, 79, 75, 74, 90, 112); all 35 linked responses are HTTP-successful with raw bodies; non-PIT provenance violations = 0 for every run. The duplicate-only Brazil Serie B scope correctly has 384 sightings and 0 new fixture rows.
- Combined with the single completed checkpoint per run and the exact raw payload count, the persisted evidence now reconciles without modifying any database row. These SQL checks cover the main sighting/row/provenance invariants; they are not a substitute for executing the corrected Python validator end-to-end (including reservation hash, event-link, rights and quarantine checks).
- No workflow-dispatch action is exposed by the connected GitHub integration. Commits created through the repository contents API did not produce a new Actions CI run. Therefore the current branch still needs a fresh CI run from a GitHub push/PR update before the code repair can be marked CI-verified. Do not rerun the failed backfill workflow: it performs collection and would spend provider requests.


### Correction — historical match statistics were present (2026-11-20)

- The earlier audit incorrectly tested `statistics` as a JSON array. The provider schema returns it as a JSON object containing home/away metrics and first-half splits. That type mismatch caused the false report that all statistics arrays were empty. This correction supersedes that earlier statement.
- Re-audited stored raw responses and immutable source observations using the correct object schema. For imports 19–25, all 1,601/1,601 fixture observations have a non-empty statistics object; all 1,601 have `shots_on_target` and `possession`; all 1,601 have `dangerous_attacks` and first-half splits. Events are non-empty for 1,584/1,601. The statistics are already stored in `source_observations.payload`; no new provider request or statistics recovery collection is required for these records.
- Root cause of the feature gap: the existing retrospective dataset loader used only the fixture projection's first `source_observation_id` and did not select the latest immutable observation payload. This especially excluded the duplicate-only Brazil Serie B backfill observations, because those correctly retained the original fixture provenance pointer.
- Implemented on `stage-8b-statistics-ci-release`: retrospective dataset loader now selects the latest fixture observation under the same original rights approval and reads `payload->'statistics'`; the lagged feature builder now constructs strictly earlier same-competition team-perspective means for attacks, dangerous attacks, shots on/off target, possession, and first-half versions. Added builder and dataset regression tests. Missing statistics remain null; simultaneous kickoff blocks remain atomic; output remains retrospective/non-PIT and certification-ineligible.
- Neon read-only audit of the 1,601 backfill sightings confirms stats object/shot/possession coverage 100% for every competition. The corrected loader has not yet been executed end-to-end and the new tests have not yet received a fresh CI run.
- Consolidated PR #123 is the active CI candidate. PR #121 and #122 were closed as superseded, not merged. The connected GitHub integration did not start CI for PR #123; only the Vercel preview check appeared. A repository-side GitHub Actions run on the candidate head is still required before merge.
- No new provider calls, Odds API calls, production DB writes, or deployments occurred. No statistics backfill is needed for the seven collected competitions unless a later coverage audit identifies a specific missing fixture.


### Statistics-aware dataset and validation workflow completed in code (2026-11-20)

- Added `backend/scripts/validate_historical_feature_backfill.py`. It opens the production database in a read-only transaction, verifies the exact seven expected import scopes (IDs 19–25), and runs the full corrected `validate_competition_import` implementation for each. It performs no provider requests or database writes.
- Updated `.github/workflows/retrospective-research-rebuild.yml` on the candidate branch to run the read-only import validator, build the statistics-aware retrospective feature dataset, retain the prior retrospective baseline report and paired diagnostics, and upload the new dataset artifact.
- Updated the lagged statistics builder to treat absent stats as null and added a regression test for this case. Added dataset assertions for the newly loaded provider statistics. These code changes have not yet been executed by GitHub Actions.
- Candidate PR #123: `stage-8b-statistics-ci-release` -> `main`, non-draft and open. PR #121 and #122 are closed as superseded; none of these PRs has been merged.
- Required manual runs: CI workflow on candidate branch for backend tests/lint and Android build; retrospective research workflow on candidate branch for the seven-run read-only validator and statistics-aware dataset artifact. The connected GitHub integration exposes no workflow-dispatch action and no CI run appeared for the PR-created commits. The workflow pages are available in GitHub Actions; the user must select `stage-8b-statistics-ci-release` and click Run workflow.
- No further data collection is needed to recover statistics from these 1,601 observations. Do not rerun the historical backfill. The feature dataset and candidate model remain research-only/non-PIT.


### Full read-only SQL equivalence audit for historical validator (2026-11-20)

- Extended the independent Neon read-only audit to cover all import-validator invariants that can be checked in SQL. Across runs 19–25: all 35 reservation idempotency keys, endpoints, canonical parameter hashes, request-event links, and raw-response SHA-256 checksums pass (35/35 each); no event-link or checksum failures.
- All seven runs are COMPLETED, provider/source and rights approval fields match the approved scope, request budgets are respected, and the approval is current. Each run has the expected 365-day window protocol, checkpoint totals reconcile, sightings equal records_seen, and fixture rows equal records_inserted. Non-PIT provenance violations, out-of-window/bad fixture rows and unresolved quarantine are all zero.
- Legacy duplicate counts inferred from evidence by run: 124, 384, 101, 91, 81, 110, 115 (total 1,006). The duplicate-only Brazil Serie B scope is fully accounted for by its 384 sightings and zero new fixture rows.
- This is a read-only SQL-equivalence audit of the validator's checks; the Python validator itself still needs to run once from the new manual research workflow. No DB writes or provider requests were made.


### CI duplicate-sighting regression correction — 2026-11-20

- Inspected failed CI run 44697802502 / job 136158651605 on the PR #123 head. Result: 445 tests passed; one failed: `test_duplicate_fixture_sightings_are_counted_separately_from_new_rows`. The failure showed two identical raw fixture occurrences correctly produced one immutable observation/sighting, while `records_seen` counted both occurrences.
- Root cause: the validator compared persisted sightings directly with `records_seen`. This is invalid when the same fixture identity is repeated within one provider response because the ingestion store is intentionally idempotent for an identical fixture/payload/response tuple.
- Corrected `validate_competition_import` to reconcile sightings against distinct fixture identities in the captured raw response, while preserving separate raw occurrence counters (`records_seen`), inserted-row counters, duplicate counters, rights checks, request provenance, and data-quality checks. The validator report now includes `distinct_fixture_entities`.
- Corrected the regression test: two identical fixture occurrences must remain `records_seen=2`, `records_inserted=1`, `records_duplicate=1`, `fixture_sightings=1`, `distinct_fixture_entities=1`, and `fixture_rows=1`.
- Commits on `stage-8b-statistics-ci-release`: validator reconciliation `b98a9fd94d0275e6570a987bb571624970930ca3`; regression assertion `9ffa40527782f39a418295c45b32ade34a75e132`; SQL alias correction `e275a9df361028d7f01c31b2441aabe29ef48a4f`. PR #123 now points to `e275a9df361028d7f01c31b2441aabe29ef48a4f`.
- This is a code correction only; it has not yet been executed by CI. The retrospective workflow has not been run. Rerun CI on this exact head first; only after it passes, run the read-only retrospective research workflow. Do not rerun historical collection, spend provider credits, merge, deploy, or unlock publication/value betting.


### 2026-11-20 — CI malformed-response reconciliation fix

CI run 44704953098 on PR #123 head `71b4d7374e17f71db24a76d14a4eb18962487ea8` completed with Android debug build successful and backend tests at 445 passed / 1 failed. The failure was `test_malformed_provider_page_is_saved_and_quarantined`: the new fixture-identity reconciliation SQL cast every captured `provider_responses.raw_body` to JSONB. The test intentionally stores truncated JSON (`{"success":1,"data":`) for quarantine/audit, so the validator crashed before its expected paused-run validation error.

Corrected `backend/app/providers/historical_validation.py` to derive the distinct fixture observation tuple count from immutable `source_observation_sightings` joined to `source_observations`, counting distinct `(provider_entity_id, payload_sha256)` tuples within the approved fixture scope. This preserves idempotent duplicate accounting while never parsing raw response bodies. Malformed raw payloads remain retained byte-for-byte for quarantine and audit. Code commit: `a92c6d7d1c67feed44ec4936b67edb06ac94c88f`.

Verification status: fix committed but not yet CI-verified. Rerun CI on the updated PR #123 head. Do not run the retrospective workflow until CI passes. Android build from run 44704953098 passed; backend lint was skipped because tests failed. No provider requests, Odds API credits, production DB writes, merges, deployments, or certification changes were made.


### 2026-11-20 — CI lint path correction

CI run 44707971737 on PR #123 head `d0624f95f9b3cc5e09e80771acf13620a56dd85e` passed all backend tests and the Android debug build, then failed Ruff with E902 because `.github/workflows/ci.yml` invoked `../scripts/validate_historical_feature_backfill.py`. The script is located at `backend/scripts/validate_historical_feature_backfill.py`, and the job working directory is `backend`; the correct Ruff argument is therefore `scripts/validate_historical_feature_backfill.py`.

Corrected the workflow path in commit `5522c1c7f09231ff8e61c3ebc4ed4e6f2bcf5dcf`. This is a CI configuration fix; no application logic changed. It is not yet CI-verified. Rerun CI on the latest branch head before running the retrospective research workflow. No provider requests, Odds API credits, production writes, merge, deployment, or certification unlock occurred.
