# VELTRIX AI ANALYST — Implementation Roadmap

**Last updated:** 2026-11-20 (Stage 8B retrospective rebuild verified; PR workflow reconciliation underway)  
**Repository:** `Nexora-Apparel/veltrix-ai-analyst`  
**Roadmap status:** engineering baseline; statuses below distinguish implemented infrastructure from validated production capability.

## Operating contract

- Preserve the existing Android application UI and navigation. Integrate functionality into its established screens; do not redesign it.
- Android is the only user-facing delivery application. No Telegram or external messaging delivery.
- Daily capture target is 04:00 WAT; prediction availability target is 06:00 WAT, with 07:00 WAT as the latest target.
- Publish at most 25 eligible fixtures per WAT prediction date. Never pad the list. Publish fewer or zero when evidence or release gates require it.
- Markets: 1X2, BTTS Yes/No, and Over/Under 1.5, 2.5 and 3.5.
- Match probabilities must be model-derived and must not depend on bookmaker odds.
- Value betting remains separately locked until its independent certification requirements pass.
- Historical training-only records may support training, but never count as prospective validation or certification evidence.
- Missing data must remain explicit. Sparse-data calculation paths are permitted only when governed, tested and defensible; no fabricated observations or arbitrary generic probabilities.
- Strong / Medium / Low describe evidence reliability, not the chance of a particular outcome.
- Protect The Odds API budget. No odds requests are needed for ordinary model development, capture, snapshotting or match-probability inference.

## Stage status summary

| Stage | Name | Status | Exit condition |
|---|---|---|---|
| 1 | Canonical scope inventory CLI | Complete | Inventory command and contract tests merged |
| 2 | Approved-scope materializer | Complete | General materializer and safe scope controls merged |
| 3 | Production database migrations | Applied through migration 017 | Schema and migration integrity verified |
| 4 | Prospective provider capture | Active | Scheduled seven-scope capture remains healthy with auditable provider-response lineage |
| 5 | Canonical identity linkage | Applied; reconciliation outstanding | All conflicts/restrictions resolved or safely excluded with evidence |
| 6 | Immutable prospective snapshots and outcome labels | Implemented; accumulating evidence | Daily snapshots and strictly post-kickoff append-only labels verified |
| 7 | Research evaluation and certification | Evaluator verified live; certification blocked by prospective evidence | Keep accumulating strict prospective labels until walk-forward and certification gates pass |
| 8 | Model capability completion and production inference | In progress; Stage 8A inventory complete | Complete governed calculations and reliability integration; validate and certify immutable artifact; build gated daily inference/publisher |
| 9 | Android integration and release verification | Partial API/UI foundation; integration pending | Existing UI consumes real published predictions, history/settlement and in-app notifications; runtime checks pass |

## Stage 1 — Canonical scope inventory CLI

**Status: COMPLETE.** The approved competition scope inventory tooling and contract were delivered. Do not rebuild unless a new defect is found.

## Stage 2 — General approved-scope materializer

**Status: COMPLETE.** The reusable materialization workflow exists. Keep scope authorization and identity controls intact.

## Stage 3 — Production database migrations

**Status: APPLIED/VERIFIED THROUGH 017.** Preserve migration ordering and existing production data. Any new schema change requires a forward migration and production verification.

## Stage 4 — Prospective provider capture

**Status: ACTIVE.**

- Scheduled workflow: `.github/workflows/prospective-5dollar-daily-capture.yml`.
- Schedule: `0 3 * * *` UTC (04:00 WAT).
- Primary source: approved 5DollarFootballAPI scopes.
- Continue seven approved competitions; monitor provider request lineage, rights, timestamps, deduplication and actual inserted records.
- A `SKIPPED_ALREADY_VALIDATED` status or reported collector count must not be described as newly inserted rows.
- Do not add competitions until provider rights and the full governance path are checked.

**Exit:** repeatable capture with verified source-response-observation lineage, canonical fixture identity, rights and point-in-time timestamps.

## Stage 5 — Canonical identity linkage and reconciliation

**Status: MATERIALIZATION APPLIED; EXCEPTIONS OPEN.**

The recorded inventory had 1,063 fixture links, 1,058 verified identities, five fixture conflicts and one team identity conflict. Brazil Serie B has two global restrictions: the PIT timestamp gap and the 2026 CBF round-coverage reconciliation. The Premier League also has one fixture conflict.

- Do not rerun the bulk seven-scope apply; PR #118 made it manual-only.
- Resolve exceptions only with admissible source evidence.
- Keep conflicted/restricted rows excluded from dependent features, evaluation and publication until resolved.

**Exit:** all rows used downstream have verified canonical fixture/team/competition identity, or unresolved rows are demonstrably excluded.

## Stage 6 — Immutable prospective snapshots and append-only outcome labels

**Status: IMPLEMENTED; DAILY ACCUMULATION ACTIVE.**

- Preserve immutable pre-match feature snapshots and content hashes.
- Append outcome labels only after kickoff, using exact provider response, observation and sighting lineage.
- Never overwrite snapshots or backfill an outcome into pre-match features.
- Keep missing feature values missing; do not coerce absence to zero.
- Historical training-only rows from PR #119 are not prospective snapshots or prospective labels.

Latest recorded checkpoint: 59 eligible snapshots, zero settled prospective labels and zero expanding folds. This is a historical checkpoint, not a claim about current live totals.

**Exit:** daily idempotent materialization and independently verified post-kickoff labels with strict lineage.

## Stage 7 — Research evaluation and certification

**Status: EVALUATOR/GATES IMPLEMENTED; CERTIFICATION BLOCKED BY INSUFFICIENT PROSPECTIVE EVIDENCE.**

- Evaluator: `backend/scripts/evaluate_prospective_hierarchical.py`.
- Implementation: `backend/app/validation/prospective_model_evaluation.py`.
- Dataset builder: `backend/app/validation/prospective_dataset.py`.
- Certification gates: `backend/app/validation/certification_gates.py`.
- Historical training-only pool: PR #119, 996 eligible historical rows at the recorded audit, marked training-only and excluded from prospective validation counts.
- Trigger correction: PR #120 adds evaluator/dataset code paths to Stage 7 push triggers.
- Existing research uses hierarchical goal rates and a competition-only Poisson baseline; nested OOF Dixon–Coles rho is used when inner-fold evidence is sufficient, otherwise rho=0 is explicit.
- The last recorded evaluator report had zero prospective validation fixtures/folds and correctly returned `INSUFFICIENT_PROSPECTIVE_DATA`. Verify a fresh post-PR119/120 run and artifact before relying on updated live results.
- Captured event/shot/possession/attack features are not yet fully active in the evaluator; last recorded usage was `HIERARCHICAL_GOAL_RATE_ONLY`.

### Certification requirements

For value betting and any applicable model promotion gates, preserve the strict thresholds already recorded in the certification code and ledger: at least 1,000 walk-forward matches per market, at least 300 prospective settled selections, at least 90 distinct dates, 98% timestamped odds coverage, positive net ROI with positive lower 95% ROI bound, and 1X2 improvement over bookmaker Brier and log loss. These requirements are not relaxed by historical training data. Production promotion and value betting remain locked until their independent gates pass.

**Exit:** reproducible chronological evaluation, adequate prospective evidence, independent gate pass and a versioned immutable artifact approved for production.

## Stage 8 — Model capability completion and production inference

**Status: IN PROGRESS. Existing model, feature and reliability components are present, but are not yet integrated into one certified production calculation path.**

### 8A. Model and feature inventory audit

**Status: COMPLETE — source, tests, workflows, API contracts, database schema and production artifact state audited on 2026-11-19.** The live main branch contains the following components:

| Component | Source | Verified position |
|---|---|---|
| Elo ratings | `backend/app/models/elo.py` | Implemented chronological Elo; retained as a retrospective research comparator, not selected in the current final training artifact |
| Recency-weighted attack/defence Poisson | `backend/app/models/attack_defence.py` | Implemented and used by `prediction_engine.py` production inference contract |
| Hierarchical Poisson | `backend/app/models/hierarchical_poisson.py` | Implemented competition/team partial pooling and unseen-team neutral effects |
| Hierarchical scoreline adapter | `backend/app/models/hierarchical_scoreline.py` | Implemented adapter from hierarchical rates to scoreline/market probabilities |
| Poisson scoreline + Dixon–Coles | `backend/app/models/scoreline.py` | Implemented five-market derivation and low-score dependence correction |
| Hierarchical research orchestration | `backend/app/orchestration/hierarchical_predictions.py` | Implemented but inert until an approved validated release; no provider calls or production writes |
| Production inference boundary | `backend/app/models/prediction_engine.py` | Implemented fail-closed artifact-based inference; requires a production-approved, PIT-certified artifact and verified team mappings; outputs `NOT_PUBLISHED` |
| Retrospective historical rate model | `backend/app/models/retrospective.py` | Research-only, explicitly not PIT-certified; contains a hard-coded no-history rate and must not be reused as a production sparse fallback |
| Evidence tiers | `backend/app/features/evidence.py` | Strong/Medium/Low scoring implemented from five weighted evidence signals and frozen policy inputs |
| Tier calibration diagnostics | `backend/app/validation/evidence_tier_calibration.py` | Held-out Brier, log loss, entropy, mean maximum probability and ECE by tier/market implemented |
| Feature admission/PIT checks | `backend/app/features/admission.py`, `eligibility.py` | Fail-closed source, rights, identity, response lineage and pre-match cutoff checks implemented; bookmaker odds explicitly forbidden as core prediction features |
| Feature evidence model | `backend/app/features/evidence.py` | Signal schema/policy/scorer exists; automatic derivation of all signals from the canonical feature snapshot and production wiring still needs verification |

### 8A.1 Confirmed integration gaps

- The latest Stage 7 research artifact explicitly reports `HIERARCHICAL_GOAL_RATE_ONLY`; captured shot, possession, attack and event features are not used by that evaluator.
- The latest dataset contains 59 eligible prospective snapshots. Several team-stat fields have values in only 5–6 rows per side; competition-rate features in 9 rows. Coverage indicators exist, but availability of a coverage indicator is not equivalent to availability of the underlying statistic.
- The standalone production inference engine currently deserializes `AttackDefenceModel`, while the prospective research evaluator and hierarchical orchestration use `HierarchicalPoissonModel`. The intended canonical production model family and artifact schema must be reconciled before promotion.
- Production inference sets uncertainty status to `NOT_YET_CALIBRATED` and emits empty coverage metadata. It must not be treated as Strong/Medium/Low-calibrated output.
- The evidence tier scorer and tier-calibration evaluator exist, and tests exist, but the audit has not established a production snapshot-to-signal builder, frozen calibrated policy artifact, or end-to-end tier propagation into persisted/public API predictions.
- Hierarchical orchestration requires `release.approved`; it creates in-memory audited predictions only and explicitly performs no provider calls or production persistence.
- The production inference engine returns `publication_status=NOT_PUBLISHED`. The public API route is read-only and only reads already-published rows; the inspected DB store has no prediction insertion/publishing methods, and the workflow inventory has no Stage 8 publisher. Thus the read contract exists, but the production write/orchestration path is missing.
- The final retrospective training artifact deliberately marks itself `RESEARCH_ARTIFACT_ONLY` and `RETROSPECTIVE_EVENT_TIME_NOT_PIT_CERTIFIED`. It cannot be used for production inference or prospective certification.
- Do not treat retrospective model hard-coded priors as the requested governed sparse-data fallback. The fallback path must be developed and validated separately.

### 8A.2 Existing model test coverage found

- `test_attack_defence.py`
- `test_hierarchical_poisson.py`
- `test_hierarchical_stress_validation.py`
- `test_hierarchical_validation.py`
- `test_model_engines.py`
- `test_prediction_engine.py`
- `test_hierarchical_orchestration.py`
- `test_evidence_tier_calibration.py`
- `test_feature_eligibility.py`
- `test_final_model_training.py`

Presence of tests is not proof of production integration or prospective model performance. Stage 8A exit criteria are met. The remaining items move to Stage 8B/8C: add tests for sparse-data segments, derive evidence signals from PIT-qualified snapshots, freeze a calibrated policy and propagate reliability into persisted/public API predictions.

### 8B. Complete the governed calculation engine

**Stage 8B initial data-feasibility finding (2026-11-19):** the 996 historical training-only rows currently enter the prospective dataset with `features={}` and empty feature lineage. They contain verified training labels/identity/competition information, not historical PIT snapshots of the rich match-stat feature set. The 59 upcoming prospective snapshots do contain PIT feature values/lineage, but have no settled labels yet. Therefore, it is not statistically valid to fit coefficients for shots, possession, attacks, corners, cards or other supporting features from the 996 outcome-only rows. Those feature effects require prospectively paired feature/outcome examples or another separately rights- and PIT-qualified historical feature corpus. Until then, the existing hierarchical goal-rate model can use the historical labels for team/competition partial pooling, while sparse supporting features remain explicit evidence/coverage signals rather than invented model coefficients.


### 8A. Model and feature inventory audit

Inspect the live default-branch source, tests and workflows and classify every intended model/calculation as:
- implemented and tested;
- implemented but not integrated;
- partially implemented;
- specified but not built; or
- obsolete/not approved.

The existing hierarchical Poisson implementation, scoreline/market probability code and Dixon–Coles research evaluation must be reused where sound. Do not assume that a model name in documentation means it is wired into production inference. Verify exact source paths, call sites, tests and workflow use.

### 8B. Complete the governed calculation engine

- Integrate eligible captured features only after checking provenance, freshness, missingness and point-in-time validity.
- Evaluate additional information such as recent team performance, attack/defence strength, competition context and other available event/shot/possession features; do not claim use of a feature until it is in the inference path and tested.
- Implement defensible sparse-data pathways using hierarchical pooling, competition context, shrinkage and uncertainty-aware estimates where development-fold evidence supports them.
- Missing values remain explicit. Never fabricate match observations or silently turn missing inputs into zero.
- Validate calibration and proper scoring rules by market and by data-availability segment.
- Tune hyperparameters only on chronological development folds; freeze the candidate before prospective evaluation.
- No bookmaker odds as model inputs for match probabilities.

### 8C. Strong / Medium / Low reliability

Implement reliability as a separate evidence-quality assessment, considering sample size, source quality, feature completeness, freshness, uncertainty and out-of-sample reliability by relevant segment.

- **Strong:** rich, current and consistent evidence; calculation path has adequate validation support.
- **Medium:** usable evidence with material gaps or uncertainty; any fallback is tested and calibrated.
- **Low:** substantial limitations; publish only if a defensible calculation and release policy explicitly permit it.
- Do not assign tiers from outcome probability, favourite status or arbitrary cutoffs.
- Reliability tiers do not override identity, rights, freshness, PIT or certification gates.

### 8D. Model validation and artifact governance

- Use historical training-only data for model development, never for prospective certification counts.
- Use expanding chronological folds and strict PIT feature/label separation.
- Report sample counts, dates, market-level Brier/log loss/calibration and uncertainty intervals, including sparse-data cohorts.
- Produce a versioned immutable model artifact with training cutoff, feature contract, code/model version, hyperparameters and reproducibility metadata.
- No artifact is production-certified merely because training or CI succeeds.

### 8E. Daily inference and publication

Build a workflow that runs after successful Stage 6 materialization, but only when a certified production artifact exists.

- Select upcoming fixtures from the canonical approved dataset.
- Enforce identity, rights, freshness, PIT and model compatibility gates.
- Calculate all required markets for up to 25 eligible fixtures per WAT date.
- Sparse fixtures may proceed only through validated fallback paths; otherwise exclude with a recorded reason.
- Publish fewer than 25 or zero when required. Never pad.
- Persist immutable predictions and full provenance; idempotency key includes canonical fixture and model version.
- Do not overwrite old predictions or settled history.
- Return verified publication outcomes for Android notifications.
- Keep value betting separately locked. Do not spend odds credits for ordinary match predictions.

**Exit:** certified model artifact, tested inference contract, deterministic/idempotent publisher, API readback verification and daily publication dry-run/release-gate evidence.

## Stage 9 — Android integration and release verification

**Status: EXISTING UI AND API FOUNDATION; END-TO-END INTEGRATION NOT COMPLETE.**

Preserve the existing six-tab UI: Home, History, BTTS, Value Bet, Over/Under and Menu.

- Connect existing Home/BTTS/Over-Under views to the real published prediction API.
- Populate History from immutable prediction and settled-result records without duplicates.
- Keep Value Bet locked until its independent certification gate passes.
- Add a Notifications destination inside the existing Menu; do not redesign the dashboard.
- Persist dated, readable in-app notifications driven only by verified publication outcomes: published count, shortfall and verified zero-publication reason.
- Use the collective voice “The models…” in notification copy. No Telegram, OS push or external messaging is part of this requirement.
- Preserve loading, unavailable and empty states.
- Verify API errors, stale data, no-prediction days, partial publication and duplicate/idempotency behavior.
- Build Android and perform runtime verification on a physical device before release.

**Exit:** Android displays actual published predictions and settled history, notifications reflect verified outcomes, and physical-device/runtime checks pass.

## Cross-stage release blockers and invariants

1. Five fixture conflicts and one team conflict remain unresolved in the recorded Stage 5 inventory; Brazil Serie B PIT and coverage restrictions remain.
2. The latest recorded Stage 6 checkpoint had no settled prospective labels; re-check current live state before claiming progress.
3. The last recorded Stage 7 result was insufficient prospective data; post-PR119/120 live run and artifact require verification.
4. No production daily inference/publisher was verified in the ledger.
5. No production certified immutable artifact was established in the ledger.
6. Android UI exists, but Notifications and end-to-end prediction/history integration remain outstanding.
7. Value betting remains independently locked.
8. Do not infer current state from this document alone: verify GitHub main, Actions artifacts, database state and API readback before release claims.

## Immediate execution order

1. Verify latest main commit and Stage 7 post-PR119/120 run/artifact.
2. Perform Stage 8A full source/test/workflow inventory of all model and feature components.
3. Update this roadmap and dated ledger with the verified inventory, exact file paths, integration status and missing tests.
4. Implement Stage 8B/8C calculation and reliability capabilities with tests.
5. Run chronological research and sparse-segment validation; do not promote without prospective evidence.
6. Build Stage 8D artifact governance and Stage 8E gated publisher.
7. Implement Stage 9 API integration, History and Menu Notifications while preserving UI.
8. Complete runtime verification and release only after all applicable gates pass.


### Stage 8B implementation checkpoint — 2026-11-19

**Status: IN PROGRESS; first governed sparse-path implementation committed on the Stage 8B work branch.**

- The hierarchical Poisson predictor now exposes an explicit `calculation_mode` with five provenance states: `TEAM_AND_COMPETITION_HISTORY`, `ONE_SIDED_TEAM_HISTORY`, `COMPETITION_ONLY`, `TEAM_HISTORY_GLOBAL_CONTEXT` and `GLOBAL_CONTEXT_ONLY`.
- The classification is derived from observed training-history counts and whether the competition was represented in the fitted model. It introduces no arbitrary minimum-match threshold and does not convert missing feature fields into zeros.
- The hierarchical orchestration audit now carries the calculation mode, home/away history counts and competition-seen flag alongside its market calculations. These fields remain research/audit outputs; they do not authorize production publication.
- Unit tests were extended for one-sided team history, both unseen teams in a known competition, known team history in an unseen competition, fully unseen teams/competition, and orchestration audit propagation.
- Existing prospective dataset logic was inspected: it requires a genuine pre-kickoff scheduled snapshot, filters feature observations by observed-at cutoff and rights, derives rolling features only from eligible earlier finished matches, and attaches a label only from a finished observation observed after kickoff. Existing tests cover no-history and one-sided missing-feature behavior.
- The 996 historical training-only rows still have no feature snapshots and cannot train supporting-feature coefficients. Upcoming snapshots remain unlabeled until a verified post-kickoff finished observation is captured. No synthetic features or labels were added.
- This change does not relax Stage 7 prospective certification, Stage 5 identity/rights restrictions, or the Stage 8 production artifact/publisher gates.

**Remaining Stage 8B work:** run CI and model stress/chronological development validation; inspect the training-row cutoff/label-availability semantics; evaluate sparse cohorts and convergence; only then freeze a candidate calculation protocol. Stage 8B is not complete.


### Stage 8B — label-cutoff enforcement and historical feature recovery (2026-11-19)

**Status: IMPLEMENTATION IN PROGRESS; backend/Android CI re-run pending.**

#### Training-label availability correction

- Hierarchical chronological tuning now supports an explicit `label_available_at` map. A result is admitted to a training fold only when both its fixture kickoff and its recorded label-availability timestamp are at or before that fold's training cutoff.
- Optional `evaluation_as_of` prevents scoring validation labels that had not yet been observed by the research run.
- Prospective outer and inner evaluation now validate each training label against `fold.train_cutoff_at` (not merely the later validation kickoff) and validate training rights at that same cutoff.
- The hierarchical model is fitted `as_of=fold.train_cutoff_at`, so its recency weights use the actual data-availability cutoff.
- Stress/tuning tests now exercise delayed-import labels and strict availability-aware tuning. An evaluator regression test deliberately moves the recorded cutoff before a training label and expects a fail-closed rejection.

#### Production data audit and recovery path

Read-only production Neon inspection found 996 eligible historical finished fixtures across seven approved competitions. Only 6/996 stored observations currently contain a statistics object or events array; all 996 have corners fields. The shortage is therefore mainly missing historical source feature payloads, not a lack of historical outcomes.

The existing 5Dollar provider adapter already requests `include=stats,events` on league fixture-history requests and the importer persists normalized fixture payloads as append-only source observations. A separate `historical_feature_backfill` import type and manually dispatched, quota-gated workflow were added. The workflow:
- serializes against the regular prospective capture;
- probes the 5Dollar account entitlement first and prints only safe plan/quota fields;
- defaults to preflight-only mode;
- requires an explicit workflow input to send backfill requests;
- uses a separate import type so prior completed outcome-only imports do not suppress feature recovery;
- uses the existing approval, durable per-run request reservations, raw response hashes and append-only ingestion path.

The backfill is not yet executed. It must only run after the entitlement output is reviewed; it is not allowed to consume The Odds API credits. Refetched observations are captured now and are **retrospective training-only evidence**. They must not be represented as historical pre-match system snapshots or used as prospective validation labels.

#### Remaining data/model work

- Add a distinct retrospective event-time feature-row builder that derives each historical training fixture's inputs only from earlier fixtures in the same canonical competition, using the recovered statistics/events and marking every such row `validation_eligible=false` with non-PIT retrospective lineage.
- Train a research-only feature model on those lagged historical covariates plus settled outcomes; compare it with the hierarchical goal-rate-only model using future prospective settled fixtures only.
- Keep the 996 outcome-only records available to the hierarchical model now, but only at actual import-completion cutoffs. Never claim their match kickoff alone proves when VELTRIX knew the result.
- Stage 7 certification, production promotion and value betting remain locked.


### Stage 8B — retrospective feature reconstruction implementation (2026-11-19)

**Status: research-only feature builder implemented; CI pending.**

Added `backend/app/validation/retrospective_features.py` and focused tests. The builder reconstructs team-level lagged goals-for/against, corners-for/against and cards-for/against means from strictly earlier fixtures in the same competition. It excludes simultaneous kickoffs, isolates competitions, preserves missing covariates as null, and records the exact historical fixture IDs used.

Every emitted row is explicitly `validation_eligible=false`, `point_in_time_certifiable=false`, and `source_available_before_target_kickoff=false`. This is retrospective event-time reconstruction from later-retrieved historical data; it is a research-training candidate only, never Stage 7 prospective validation or production inference evidence. It is deliberately separate from the prospective snapshot dataset.

This gives the 996 historical outcomes a legitimate route to richer research features using already stored corners (and goals/cards where present), even before any feature backfill. Shots, possession and detailed event-derived metrics remain unavailable until the quota-gated 5Dollar stats/events backfill has been run and audited. The new builder has not yet been wired into model training; integration and comparison against the goal-rate-only baseline are the next task.


### Stage 8B — strict real-data fold audit (2026-11-19)

- Both hierarchical hyperparameter tuning and Dixon–Coles OOF estimation now require actual label-availability timestamps in strict mode, plus an explicit evaluation-as-of timestamp. Each training row must have both kickoff and label availability at/before its fold cutoff. Validation labels must have been observed by evaluation-as-of. A fold cutoff later than evaluation-as-of is rejected.
- The seven-competition hierarchical research runner now reads the latest sighting's `system_observed_at`, falling back to `retrieved_at` only for non-PIT retrospective records. It audits fold availability before tuning and writes an explicit `INSUFFICIENT_LABEL_AVAILABILITY_FOR_CHRONOLOGICAL_TUNING` report rather than scoring invalid event-time folds.
- Read-only Neon audit: 996 settled historical results are available by 2026-11-19 22:00 UTC; 990 are `RETRIEVED_AT_ONLY` (non-PIT) and 6 are `SYSTEM_OBSERVED_AT`. Their availability range is 2026-11-16 21:12:28 UTC to 2026-11-19 05:38:39 UTC.
- Actual configured fold audit: 15 Sep: 505 kickoff-prior rows / 0 labels available at cutoff / 91 validation labels known by evaluation time; 30 Sep: 596 / 0 / 35; 10 Oct: 631 / 0 / 131. All three folds are invalid for training, so no real-data hyperparameter or rho selection is permitted from this corpus.
- This does not mean the 996 results are useless: all are available now as a retrospective training pool for a current research fit. They cannot validate predictions as of September/October, and the 990 retrieval-only records cannot support PIT certification.
- The manual feature-backfill workflow now passes its push validation check and remains preflight-only by default. It has not made provider requests. Its execution remains gated on the entitlement/quota report.
- Full backend stress/tuning tests and Android build passed on CI run 44623823396 (433 tests, lint clean, APK assembled) before the latest strict Dixon-Coles and real-data runner refinements. CI for the current branch head must complete before merge.


### Stage 8B — retrospective feature path and final CI checkpoint (2026-11-19)

- Confirmed the repository already contains `backend/app/validation/retrospective_features.py`, a research-only lagged feature builder using earlier same-competition outcomes, corners and cards. Its output is explicitly non-PIT and `validation_eligible=false`.
- Fixed a same-kickoff leakage defect: fixtures sharing an identical kickoff timestamp are now processed atomically. Every feature vector for that timestamp is generated before any fixture in the block is added to team history.
- Production coverage audit: all 996 settled historical rows contain goals, corners, yellow cards and red cards; only 6/996 contain statistics objects/events arrays. Thus a useful retrospective lagged feature matrix can be built now from the existing outcome/corners/cards corpus; historical stats/events backfill is an enhancement, not a prerequisite for the first research feature model.
- Remaining Stage 8B work is to wire the read-only production loader to this builder, persist an immutable training-only research dataset artifact with source lineage/fingerprint, and fit/compare a feature-aware candidate against the hierarchical goal-rate baseline. These rows must remain non-PIT and validation-ineligible.
- Prospective Stage 4 snapshots/outcomes remain the only valid route to chronological prospective validation and Stage 7 certification.

**Verification:** CI run 44625656408 on commit `8d493797a9e43b3d8699a26cb071fe3baed32d37`: 439 backend tests passed, Ruff lint passed, Android debug APK assembled and uploaded. PR #121 is open and mergeable, not merged. No production DB writes, provider requests or deployment occurred.

### 5DollarFootballAPI rate-limit confirmation (2026-11-20)
- User independently checked the provider dashboard: 300 requests/hour, matching the entitlement preflight response.
- Current batch guardrails: seven approved competitions × ten requests maximum = 70 total request reservations; provider client throttle is one request per 60 seconds. This is within the reported hourly rate cap, but is not evidence of a separate monthly credit balance.
- No historical collection was launched from this clarification. Actual dispatch remains gated until default-branch workflow and selected branch execution path are verified.


### Historical feature evidence preflight (2026-11-20)
- A separate default-branch manual workflow is available at `.github/workflows/historical-feature-evidence-preflight.yml`; it performs only database identity/read-only and 5Dollar entitlement checks. Run `44636268137` passed.
- Entitlement response reports Community plan and rate_limit 300, but daily_limit and daily_reset_at are null. Remaining quota is therefore unknown; historical collection remains blocked pending authoritative quota semantics/value. No collection or database writes occurred.


### Historical feature backfill workflow available (2026-11-20)
- Added `.github/workflows/historical-feature-evidence-backfill.yml` to `main` (commit `6b6c045a50572cf22f12d6ca95038fca81d91b36`) without merging PR #121.
- Manual dispatch must select `stage-8b-sparse-inference-governance`; the workflow checks out the selected ref, where the feature-backfill importer exists.
- Default is preflight-only. To run the bounded collection, set `execute_backfill=true`. Scope is 7 approved competitions × 10 requests maximum, 365-day window, 60-second request spacing (60/hour), under the user-confirmed 300/hour provider limit.
- Workflow is exposed but has not been dispatched. User must perform the actual manual dispatch; inspect the resulting run before claiming collection success.


### 2026-11-20 backfill execution checkpoint

The manually dispatched historical feature backfill (run 44637566125) completed its collection work but the workflow exited failure during reconciliation validation. Neon independently confirms seven import runs completed: 1,601 records seen, 595 inserted, 35 requests used, 0 rejected/quarantined. Scope-level details and failure codes are recorded in the dated ledger. Validation reported sighting-count and import-counter reconciliation mismatches across all seven competitions; Brazil Serie B additionally inserted zero fixtures. The database is 23 MB. Treat this as completed collection with failed validation—not as a verified feature-recovery success. Do not repeat collection until the importer/reconciliation and zero-insert scope are audited. No Odds API use.


### Stage 8B — historical backfill accounting and validation repair (2026-11-20)

**Status: code repair committed to Stage 8B branch; CI and revalidation pending.**

- Corrected successful-page checkpoint persistence so records_duplicate, records_rejected, and records_quarantined are retained alongside seen/inserted counts. This allows _run_totals() and _finish() to calculate truthful run-level counters.
- Corrected validator semantics: fixture sightings must reconcile to provider records seen; fixture rows linked through the stable provenance pointer must reconcile to newly inserted identities. A duplicate sighting is expected to create immutable observation evidence without replacing the original fixture provenance key.
- Added a regression test with two sightings of one fixture identity, expecting seen=2, inserted=1, duplicate=1, sightings=2, fixture rows=1.
- For historical runs created by the defective checkpoint writer, validator may derive a legacy duplicate count without mutating the database, but only if all sightings reconcile, inserted rows reconcile, and no rejected/quarantined records exist.
- Read-only audit establishes the 384 Brazil Serie B sightings are already captured observations; zero new fixture rows is expected because the identities existed before the backfill. The original fixture rows intentionally retain their first source-observation pointer.
- No further provider calls or database writes are needed for this repair. Next: run full CI, inspect the complete PR diff, execute the corrected validator read-only against runs 19–25, inspect payload feature completeness, then proceed with retrospective dataset/model comparison. Certification/value-bet locks remain unchanged.

- Follow-up correction `681ff63b52b307315ad4b1913e22a30e9b9bb90c`: a scope with zero newly inserted rows is not automatically empty. The no-data gate now checks for zero records/sightings, allowing Brazil Serie B's fully observed duplicate-only scope to validate when all other evidence reconciles.


### 2026-11-20 reconciliation repair — verification state

- Import runs 19–25 are independently reconciled at the checkpoint level: records_seen, records_inserted and requests_used match their single completed checkpoint for each competition. The legacy stored duplicate counters remain zero; read-only evidence implies 1,006 duplicate fixture sightings across the batch, conditional on the separate sighting and materialized-row checks.
- The 1,601 raw fixture payload objects all include a statistics key, but every statistics array is empty. Events are non-empty for 1,584/1,601 fixtures. Lineups are absent. Do not describe this as recovered stats or lineup intelligence; it is primarily historical event-payload evidence.
- The previous green CI run 44637030091 is not sufficient for the later accounting/validator code: its tested commit changed only this roadmap. Trigger and verify a fresh CI run against the latest PR head before merge.
- The original collection workflow failed while executing its older validator. Corrected validator revalidation has not yet run. Next: full CI on latest code, execute a read-only validator against import runs 19–25 (without provider requests or DB writes), then run the retrospective dataset builder and baseline comparison. No repeat collection.
- PR #121 remains open/unmerged. Production inference, publication, Stage 7 certification, and value betting remain locked.


### 2026-11-20 — historical statistics recovered from existing observations

**Correction:** the previous audit mistakenly treated the provider `statistics` JSON object as an array and incorrectly concluded that all statistics arrays were empty. The provider returns an object containing home/away attacks, dangerous attacks, shots on/off target, possession and first-half splits. Correct read-only validation confirms all 1,601/1,601 fixture observations from backfill runs 19–25 have non-empty statistics objects, including shots and possession; 1,584/1,601 have non-empty event arrays. Statistics already exist in immutable `source_observations.payload`; no new collection is needed for this corpus.

**Implementation added on `stage-8b-statistics-ci-release`:** the retrospective dataset loader now reads the latest observation payload under the fixture's original rights approval (not just the original fixture projection pointer). The retrospective feature builder derives strictly lagged, same-competition, team-perspective means for attacks, dangerous attacks, shots on/off target, possession and first-half versions. Missing values remain null; simultaneous kickoff fixtures cannot leak; all outputs remain retrospective, non-PIT and certification-ineligible. Regression tests cover the new feature path.

**Current verification:** database coverage checks passed read-only. End-to-end dataset build, complete corrected Python validator, backend test/lint, and Android CI remain unverified. PR #123 is the active consolidated candidate; PRs #121 and #122 were closed as superseded, not merged. The connected GitHub integration created PR #123 but did not trigger GitHub Actions CI; a fresh CI run on the candidate head is required. Do not rerun historical collection or spend provider requests for the statistics already present.


### Next execution gates — 2026-11-20

1. Run GitHub Actions `CI` on branch `stage-8b-statistics-ci-release`; require backend pytest, Ruff and Android debug build success on the candidate head.
2. Run `Rebuild retrospective research report` on the same branch. The candidate workflow now performs full read-only validation of import runs 19–25 and builds/uploads the statistics-aware retrospective feature dataset before the existing baseline research report.
3. Inspect the dataset artifact's row count, statistics coverage, provenance hashes, rights eligibility and feature null rates.
4. Train a statistics-aware research candidate and compare it with the goal-rate baseline on identical chronological folds, stratified by competition and history depth. Do not mix these retrospective rows with prospective certification.
5. Review PR #123 after both workflow artifacts pass. Keep Stage 7 certification, production publication and value betting locked.

The 1,601 historical observations already contain non-empty statistics objects, so further historical statistics collection is not required for this corpus. Any later collection must be limited to an explicitly audited coverage gap.


### Historical import verification refinement — 2026-11-20

A complete read-only SQL equivalence audit now verifies 35/35 request reservation keys, endpoints, canonical request-parameter hashes, request-event links and raw-response SHA-256 checksums. All seven import runs have current approved rights, correct request budgets/windows/checkpoints, complete fixture sightings, inserted-row reconciliation, valid provenance, no invalid fixtures and no unresolved quarantine. The Python validator and candidate CI workflows still require manual GitHub Actions dispatch; do not rerun collection.


### 2026-11-20 — CI duplicate-sighting regression fix

The first PR #123 CI run (44697802502) reported 445 passing tests and one failing duplicate-sighting regression. The ingestion store intentionally deduplicates identical fixture observations within the same provider response, so two identical raw fixture occurrences count as two `records_seen` but one persisted sighting. The validator incorrectly equated sightings with raw occurrence count.

The validator now compares persisted sightings with distinct fixture identities extracted from the captured raw response. Raw seen/inserted/duplicate counters remain independently reconciled, and fixture-row counts remain checked against inserted rows. The regression now asserts: 2 seen, 1 inserted, 1 duplicate, 1 sighting, 1 distinct fixture identity, 1 fixture row. The validator report exposes `distinct_fixture_entities` for auditability.

Changes committed to `stage-8b-statistics-ci-release`; latest verified PR #123 head: `e275a9df361028d7f01c31b2441aabe29ef48a4f`. The fix is not CI-verified yet. **Next user action: run CI only on this exact branch/head.** If it passes, then run the retrospective research workflow. Do not rerun historical collection; no provider calls or production DB writes are needed for this fix. Stage 7 certification, production publication and value betting remain locked.


### 2026-11-20 — Stage 8B CI blocker update

The first CI rerun on PR #123 head `71b4d7374e17f71db24a76d14a4eb18962487ea8` passed the Android debug build but failed one backend test (445 passed, 1 failed). The failing malformed-provider-response quarantine test exposed that fixture reconciliation attempted to cast captured raw response bytes to JSONB. The validator now derives distinct fixture observation tuples from immutable sightings/observations instead, so malformed response bodies remain auditable without breaking validation. Fix commit: `a92c6d7d1c67feed44ec4936b67edb06ac94c88f`.

**Gate:** CI must be rerun on the updated branch head. Retrospective research workflow remains blocked until CI passes. No historical collection rerun, provider-credit spend, merge, deployment, production publication, or value-bet unlock is authorized by this change.


### 2026-11-20 — Stage 8B lint-path correction

The CI run on the latest pre-fix PR #123 head passed backend tests and Android build but Ruff failed with E902 because the validator script path was incorrectly prefixed with `../`. Since the backend job runs from `backend/` and the validator is under `backend/scripts/`, the workflow now uses `scripts/validate_historical_feature_backfill.py`. Workflow fix commit: `5522c1c7f09231ff8e61c3ebc4ed4e6f2bcf5dcf`.

**Gate:** rerun CI on the new branch head. The retrospective research workflow remains blocked until CI fully passes. No data collection, provider-credit use, merge, deployment, or production unlock.


## 2026-11-20 — Stage 8B CI verification

**Status: CI PASSED on candidate head; retrospective research rebuild is the next gate.**

- CI run [44711273673](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44711273673) completed successfully on `6aba288a8d102301329d220bc776fa09faa14fbb`, the PR #123 head at run time.
- Backend tests, Ruff lint and Android debug build all passed. Android APK artifact ID `14617771339` was uploaded (16,448,825 bytes; SHA-256 `7c7d62718f06ae0909de2c44bbec2073fd5c5dd90a394666b93b052eaf3e5a90`).
- The prior duplicate-sighting, malformed-JSON and Ruff-path blockers are cleared by this exact-head CI result.
- **Next:** manually dispatch `.github/workflows/retrospective-research-rebuild.yml` on `stage-8b-statistics-ci-release`. It performs read-only import validation for runs 19–25, builds the statistics-aware retrospective dataset, runs retrospective research and paired chronological diagnostics, then uploads three artifacts.
- The current GitHub connector exposes no workflow-dispatch action; manual UI dispatch is required. No repeat collection, provider requests, Odds API requests or production DB writes are needed for this next gate.
- CI success is not model certification. PR #123 remains open/unmerged; production publishing and value betting remain locked.
- Detailed evidence: `docs/ledger/2026-11-20-stage-8b-ci-passed.md`.


## 2026-11-20 — Retrospective rebuild: scheduled fixture classification

**Status: root cause confirmed by read-only Neon audit; correction committed; CI pending.**

- Run [44711913137](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44711913137) passed the read-only validator for import runs 19–25 and the statistics-aware feature dataset build, then failed in the retrospective training runner with `UNEXPECTED_STATUS_OR_SCORE_ROWS:2`.
- Read-only status distribution for the selected competition: 380 FINISHED with scores, four UNKNOWN without scores, and two SCHEDULED without scores. The two unexpected records are legitimate upcoming 2026-11-22 fixtures, not malformed results.
- Corrected source classification now distinguishes FINISHED, UNKNOWN, SCHEDULED and INVALID. Scheduled rows are excluded from retrospective labels and counted separately; partial scores and inconsistent status/score combinations still fail closed.
- Report validator source accounting now requires source rows = finished + unknown + scheduled + invalid, with regression tests.
- Expected next report accounting: 386 total rows, 380 finished labels, four unknown exclusions, two scheduled exclusions, zero invalid. This is a target to verify, not yet a generated report.
- **Next:** full CI on the updated head; if green, rerun the retrospective rebuild and inspect all artifacts. No repeat collection, provider requests, Odds API requests or production database writes.
- Production certification, inference/publishing, PR merge and value betting remain locked.
- Detailed evidence: `docs/ledger/2026-11-20-retrospective-scheduled-fixture-fix.md`.


## 2026-11-20 — Stage 8B retrospective rebuild verified

**Status: retrospective research rebuild completed; outputs remain research-only and non-PIT-certified.**

- CI run [44712955417](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44712955417) passed on candidate head `e61791463e142a4afceaab363537ba853f37a4cb`: backend tests, Ruff and Android debug build. APK artifact ID `14618615613`, SHA-256 `268da91198a0dba132cf0f7bed92d4e9a22acb1a200f323d31891a8a3d3dff96`.
- Retrospective rebuild [44713600712](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44713600712) passed all steps: read-only import validation, statistics-aware dataset build, corrected retrospective training, paired chronological diagnostics and all three artifact uploads.
- Corrected source accounting verified: 386 rows = 380 FINISHED labelled + 4 UNKNOWN unlabelled + 2 SCHEDULED unlabelled + 0 INVALID. Only the 380 finished fixtures entered the retrospective report.
- Report hash: `14a69cc1d0b3b786d4a11808079b43ab0d3ffa97581e1136a3881e5cb8813ad5`. Full-corpus prequential 1X2 metrics (380 matches): Elo Brier/log loss 0.63336/1.05113; Poisson 0.63055/1.04804; ensemble 0.62933/1.04589. Paired block-bootstrap intervals overlap zero for all reported pairwise Brier/log-loss differences; no statistically supported winner is established. No bookmaker odds were used, so bookmaker-relative improvement is not assessed.
- Statistics-aware feature dataset: 1,576 rows across seven competitions; dataset hash `fd805256d0015f08e05f4a312d065fa8f8c00170227ac08e37ac10d11be7bf55`. Statistics feature cells are 95.05% non-null for home-perspective fields and 95.37% for away-perspective fields; 1,498/1,576 rows have at least one home stat mean and 1,503/1,576 have at least one away stat mean.
- Critical provenance boundary: all 1,576 feature rows are retrospective event-time reconstructions; all have `source_available_before_target_kickoff=false`; dataset-level `point_in_time_certifiable=false`, `validation_eligible=false`, and zero certification-eligible rows. Rights status at current read is APPROVED, but this does not make later-retrieved historical statistics PIT evidence. Do not use this dataset for prospective certification or production inference.
- Artifacts uploaded: corrected retrospective report (ID `14618990915`), paired diagnostics (ID `14619310095`), statistics-aware dataset (ID `14618123576`). Artifact ZIP SHA-256 digests and report/dataset hashes are recorded in the dated ledger.
- PR #123 remains open and unmerged. Production publishing, Stage 7 certification and value betting remain locked. No provider or Odds API calls, historical recollection, production DB writes, deployment or merge were performed by this research rebuild.

**Next:** use this corpus only for exploratory feature/model diagnostics; design a genuinely PIT-qualified feature/outcome dataset from prospective snapshots and post-kickoff labels, then continue Stage 8B/8C. Do not claim that statistics are production-integrated or that any model is certified.

Detailed artifact, metric, provenance and limitation record: `docs/ledger/2026-11-20-stage-8b-retrospective-rebuild-passed.md`.


### 2026-11-20 — PR #123 workflow reconciliation underway

- Candidate backfill workflow now verifies Neon database identity in a read-only transaction while preserving manual dispatch, review-before-execution and bounded request controls.
- Candidate now includes the manual entitlement preflight workflow. It uses a read-only Neon transaction, probes 5Dollar entitlement and performs no historical collection or database writes.
- No collection dispatch, provider collection requests, Odds API spend, production writes, merge or deployment occurred.
- Reconciliation is not complete: inspect the three main-only commits and remaining diff, verify both workflow files by fetch-back, then run CI on the exact resulting head. Keep production inference/publication and value betting locked.


## 2026-11-20 — PR #123 workflow reconciliation review

The three commits present on `main` but absent from the candidate's ancestry were reviewed individually. Their functional changes are represented on `stage-8b-statistics-ci-release`: the corrected manual entitlement preflight is content-equivalent, and the backfill workflow retains the default-branch push-validation/manual-dispatch behavior while using stricter candidate-side read-only Neon identity verification, review-before-execution wording, bounded request budget and preflight-only default. No blind merge or cherry-pick was used. Both workflow files were fetched back from the candidate after the updates.

**Status:** workflow-content reconciliation reviewed; branch ancestry remains divergent until a safe integration strategy is chosen. Do not merge solely on this review. Require fresh CI on the exact updated candidate head. No historical collection, production database writes, provider collection calls, Odds API spend, deployment or production publication occurred during this review.

**Next engineering work:** build a strictly point-in-time prospective feature dataset from immutable pre-kickoff snapshots and post-kickoff append-only labels. Keep retrospective event-time reconstructed statistics in a research-only namespace. Continue feature/model comparisons and reliability calibration without unlocking production publication or value betting before the stated certification gates pass.
