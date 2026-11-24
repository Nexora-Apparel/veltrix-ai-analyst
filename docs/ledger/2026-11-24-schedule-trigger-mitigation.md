# 2026-11-24 — Scheduled capture trigger investigation and mitigation

## Verified state

- Repository: `Nexora-Apparel/veltrix-ai-analyst`
- Default branch: `main`; repository is public, not archived, and not disabled.
- Capture workflow remains present on `main` with cron `17 0 * * *` (00:17 UTC / 01:17 WAT), merged through PR #169.
- Actions schedule-event listing contains no 24 November capture. Latest scheduled capture remains run `45171104634`, created 23 November at 12:06:06 UTC.
- At 04:02 UTC / 05:02 WAT, the 24 November run was already absent; it remained absent in the 06:21 WAT check.
- The repository has other recent scheduled workflow runs, so scheduled Actions are not globally absent from this repository.
- The capture workflow's previous observed scheduled execution was substantially late relative to its then-active cron. The current top-of-hour cron has not produced a run on 24 November.

## Assessment

GitHub documents that scheduled workflow events may be delayed or dropped during high-load periods, with top-of-hour schedules particularly exposed to contention. The current `0 0 * * *` cron is exactly at the start of an hour. This is a plausible contributing cause, not a proven diagnosis. Workflow-specific enablement state could not be read through the available read-only GitHub endpoint surface; do not state it has been independently verified.

## Mitigation proposed

PR #169 merged successfully as commit `81ff45e2b7e3658d458abb5ee20aa407e85000cb`; it changes the cron to `17 0 * * *` (00:17 UTC / 01:17 WAT) and updates the workflow summary text. The change is deliberately narrow. It does not alter the rolling capture window, request budget, PIT checks, import behavior, Stage 6/Stage 7 triggers, six-hour freshness gate, or production locks.

## Safety and outstanding verification

- No manual dispatch or rerun was performed.
- No 5Dollar Football API or Odds API request was made for this investigation.
- No production database write, deployment, model promotion, publication, or Value Bet unlock occurred.
- PR #169 CI run `45333649748` completed successfully: backend tests/lint and Android debug build both passed. PR #169 merged at 05:35:28 UTC on 24 November 2026; the new cron is active on `main`.
- After merge, verify the next natural scheduled capture, fresh import IDs/observations, its exact Stage 6 child, and Stage 7 inference outcome. A green workflow conclusion alone is not evidence that forecasts were produced.
- Keep production publication, promotion, and Value Bet locked until independent certification criteria are met.

## User-confirmed delivery-window correction (24 November 2026)

- The required user-facing prediction availability window is **07:00–09:00 WAT**, not 07:00–10:00 WAT.
- The capture workflow's previous summary text incorrectly stated 07:00–10:00 WAT. PR #169 now changes that line to 07:00–09:00 WAT while retaining the proposed 00:17 UTC / 01:17 WAT capture cron.
- This is a target window, not yet a proven delivery SLA. Stage 6 and Stage 7 are chained automatically after successful capture, but Stage 7 currently selects only snapshots no older than six hours and can correctly emit zero forecasts when data is stale or ineligible.
- No dedicated 07:00–09:00 publication/notification job was verified in the inspected workflow files. Android refreshes its API feed while the app is in foreground; this does not by itself prove forecasts will exist by 07:00.
- Required follow-up: validate natural capture timing and actual Stage 7 forecast counts, then add/verify a bounded pre-window readiness check and user-facing publication path without bypassing PIT, freshness, or certification gates.
- Final PR head `e91f538b33a0cd33411224679d1e70e1c4cb7d09` passed CI run `45333649748`; backend tests/lint and Android debug build both succeeded.

## Post-merge and same-day manual recovery (24 November 2026)

- PR #169 is merged; main capture workflow exposes `workflow_dispatch` and now uses cron `17 0 * * *` (01:17 WAT).
- The available GitHub connector is read-only for workflow dispatch; it cannot start a manual run. User can dispatch from GitHub Actions UI if same-day recovery is required.
- Manual dispatch path: repository Actions → `VELTRIX prospective 5Dollar evidence capture` → Run workflow → select `main` → Run workflow. Do not dispatch Stage 6 or Stage 7 separately; successful capture automatically triggers Stage 6, and successful Stage 6 on main automatically triggers Stage 7.
- A manual run after 09:00 WAT cannot restore the missed morning delivery. It may still produce forecasts for eligible upcoming fixtures if capture, PIT validation, Stage 6, freshness checks, and Stage 7 all succeed.
- After dispatch, verify the capture event/run conclusion, its exact Stage 6 child, exact Stage 7 child, and actual forecast count. A green capture run alone does not mean forecasts exist.


## Manual recovery execution and downstream diagnosis (24 November 2026)

### Verified execution

- Manual capture run `45336063708` completed successfully on `main` at 06:02:38 UTC (07:02:38 WAT), commit `96d1add7aad6239021c89b7876297d32fc849461`. Workflow event: `workflow_dispatch`.
- Capture covered 23 November 00:00 UTC through 2 December 00:00 UTC, six approved competitions, request budget 4 per competition. It used 12 provider requests and reported zero failed competitions.
- Import runs 51–56: Brazil Serie A inserted 2 records; Brazil Serie B inserted 2; England Premier League inserted 1; Germany Bundesliga I, Italy Serie A, and Spain La Liga inserted 0. All six imports were `COMPLETED_VALIDATED`. Total new records: 5.
- Stage 6 child run `45337517651` completed successfully. Dataset artifact `veltrix-stage6-daily-materialization-audit` (artifact `14894139168`) reported 9 eligible prospective rows, 9 distinct fixtures, 9 feature-lineage records, 0 settled labels, and 0 expanding folds. Persistence reported 0 inserted and 9 unchanged; verification found 9 snapshots and 0 latest label events.
- The downloaded Stage 6 dataset artifact was inspected directly. It contains 9 rows from a single provider competition (`3614399544`), all with kickoff times 20–22 November and a prediction cutoff of 19 November 05:45:59 UTC. Every listed team/competition last-five/last-twenty feature coverage value is 0.0. The dataset's `created_at` is 24 November 06:04:23 UTC, but its underlying snapshot cutoffs are old.
- Automatic Stage 7 inference child run `45337758682` completed successfully at 06:07 UTC (07:07 WAT) but its report explicitly returned `NO_FRESH_UPCOMING_SNAPSHOTS`: 0 fixtures considered, 0 fitted fixtures, 0 shown fixtures, 0 forecasts, 0 provider calls. Research ledger run was recorded, but contained no forecasts.
- Independent Stage 7 evaluation run `45337758751` also completed successfully and returned `INSUFFICIENT_PROSPECTIVE_DATA`: 0 fixtures evaluated, 0 folds, 0 settled labels, 0 distinct settled-label dates, and zero walk-forward fixtures for all reported markets. Production certification remains `BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE`; production promotion and Value Betting remain locked.

### Diagnosis and boundaries

- The immediate reason no forecasts were produced is verified: Stage 7 had no fresh, upcoming snapshots. Its six-hour freshness and upcoming-fixture eligibility were not bypassed.
- The Stage 6 artifact shows why its nine rows could not support current inference: all nine fixture kickoffs were already in the past by 24 November, and their prediction cutoffs were 19 November. Snapshot rows were unchanged, not refreshed by the 24 November capture.
- Although the capture inserted five records across three competitions, those records did not result in eligible fresh canonical snapshots in this Stage 6 dataset. The exact upstream cause is not yet established. Investigate import-to-canonical identity mapping, prospective dataset selection, and why newly captured fixture observations did not enter the Stage 6 eligible set. Do not assume the five inserts were forecast-eligible.
- Public API endpoint checks through the available web reader were inaccessible; API payload and Android visibility have therefore not been independently verified in this pass.
- No Android UI change, production prediction publication, model promotion, certification pass, or Value Bet unlock occurred. Do not describe this run as successful forecast delivery.

### Next actions

1. Trace import runs 51–56 and their inserted source observation/fixture IDs through canonical fixture identity mapping.
2. Inspect Stage 6 selection predicates and verify why the nine old rows remained eligible while the five newly inserted records were excluded.
3. Confirm fresh prospective snapshots are actually persisted for upcoming fixtures before Stage 7 starts; preserve the six-hour freshness and PIT gates.
4. Re-run only after the upstream eligibility defect is fixed and tests cover current upcoming fixtures, stale kickoff exclusion, and fresh snapshot selection.
5. Then verify non-zero research forecasts in Stage 7, the research API response, and the existing Android feed/parser/display path. Production publication and certification remain separate locked workstreams.

## Canonical fixture-linkage root cause and guarded repair proposal (24 November 2026)

### Live database evidence (read-only inspection)

- The production Neon project is veltrix-ai-analyst-db; inspection used its default main branch and the veltrix_ai_analyst database.
- Across the six active prospective capture competitions, the database contains **47 upcoming scheduled fixtures**.
- All 47 have a valid SYSTEM_OBSERVED_AT point-in-time source observation and successful response provenance; response hash length, fetched/retrieved timestamp equality, system-observed timestamp equality, and required feature/model-use approval coverage each passed for all 47.
- All 47 have effective reviewed home-team, away-team, and competition identity mappings.
- All 47 lack a row in canonical_fixture_sources; therefore none can pass the Stage 6 builder's reviewed canonical fixture source join.
- A read-only collision check found zero duplicate pairs among the 47 when grouped by canonical competition, ordered canonical home/away teams, and kickoff within 120 seconds.
- This is not limited to the five records newly inserted by capture runs 51–56. Those five are included in the 47; the other upcoming fixtures were already in the provider fixture store but also lacked canonical fixture source links.
- Stage 6 currently builds its dataset read-only and does not run canonical source fixture materialization. The existing approved-scope materialization workflow is a separate manual operation. The previous Stage 6 dataset consequently selected nine old fixtures with past kickoffs and no usable feature history; Stage 7 correctly rejected them as stale.

### Root cause

The daily capture path stores provider fixture rows and point-in-time observations, but it does not incrementally create and adjudicate the corresponding canonical fixture/source-link rows. The dataset builder intentionally requires an exact, provenance-verified, reviewed canonical source link plus reviewed team/competition mappings. The missing fixture links—not the Android parser—are the immediate blocker.

### Guarded code change under review

Branch: fix/daily-canonical-fixture-linkage

- Adds a versioned deterministic source-local fixture-link adjudication policy. It requires exact provider fixture ID, matching observation/sighting/response/payload/rights provenance, effective source approval at observation time, required feature/model-use rights, exact copied fixture facts, reviewed canonical team and competition mappings, one source per canonical fixture, and a 120-second canonical-team duplicate check.
- Appends an evidence-hashed SOURCE_FIXTURE_LINK_REVIEWED event only when all checks pass. Duplicate candidates receive CONFLICT; unresolved evidence stays pending and blocks Stage 6 when it affects an upcoming scheduled fixture.
- No cross-provider merge, source-row update/delete, PIT timestamp fabrication, provider request, Odds API request, model promotion, production publication, or Value Bet unlock is part of this change.
- The Stage 6 workflow is changed to run guarded materialization/adjudication before dataset construction, and gains workflow_dispatch for same-day recovery without another provider capture.
- The entire six-scope operation is preflighted and executed in one serializable transaction. It verifies that upcoming fixtures are either eligible or explicitly conflicted before allowing Stage 6 to proceed.
- This policy certifies only the source-local link; the prospective dataset builder still independently enforces PIT cutoff, rights and feature-lineage rules.

### Verification status and next actions

- Database investigation was read-only. No production database rows have been changed by this repair work.
- New unit tests cover collision detection, evidence-hash stability, and fail-closed adjudication decisions. Exact-head CI has not yet been run; do not merge until it passes and the workflow/script are reviewed.
- After merge, manually dispatch Stage 6 once to materialize the currently stored fixtures without consuming another 5Dollar API request. Then verify the Stage 6 dataset has fresh upcoming rows and Stage 7 generates non-zero research forecasts before checking the research API and Android feed.
- If preflight, source rights, mapping review, provenance or collision checks fail, the transaction must roll back and Stage 6 must remain blocked. Do not weaken the gates.


### Canonical fixture state drift discovered and addressed in the same repair branch

- A read-only audit found **50 existing canonical fixture rows** whose current status or score no longer matched the mutable provider-fixture projection. All 50 were exact provider-fixture links, effectively reviewed, canonical identity VERIFIED, and single-source. This would make the existing all-scope materializer reject the run as existing fixture mapping drift.
- The immutable source observation referenced by each source identity link is the original schedule observation. Separate later source observations exist for the current live/finished state. The provider-fixture projection had advanced, but the canonical fixture current-state projection had not.
- A second read-only audit found that **all 50/50** have a latest valid PIT observation whose status, score, kickoff, competition, teams and provider record ID exactly match the current provider-fixture projection. All 50 also pass successful-response timestamps/hash, effective approval, full STORAGE/INTERNAL_ANALYSIS/FEATURE_ENGINEERING/MODEL_TRAINING/MODEL_VALIDATION rights, exact competition approval scope, single-source and reviewed-link checks.
- The repair now separates source identity from mutable fixture state. Migration 020 adds append-only canonical fixture state events, strict database provenance/PIT/rights triggers, a current-state projection trigger, and a state provenance audit view. State events reference the latest valid source observation/sighting/response and update only the canonical fixture's current status and score projection; source observations and the original source identity link remain unchanged.
- The Stage 6 dataset builder now requires STATE_PROVENANCE_VERIFIED in addition to the existing canonical source-link and PIT feature-lineage gates. The daily materializer syncs existing state before canonical materialization, then syncs newly linked fixtures after adjudication.
- The migration workflow applies migration 020 and synchronizes existing reviewed fixture states before running its canonical provenance verification. This is required so the existing 50 stale projections are reconciled from valid source observations rather than silently overwritten.
- The state sync runner is serializable, exact-database guarded, competition-scoped and provider-request-free. The Stage 6 workflow can be manually dispatched on main for recovery; automatic capture completion still triggers it. A merge alone does not trigger Stage 6 canonicalization.
- No production database rows have been changed by this branch. The state-event migration and workflow changes are still under PR review; exact-head CI and the migration workflow must pass before Stage 6 is manually dispatched.


### PR #170 CI correction and next verification

- Exact-head CI initially exposed a PostgreSQL migration parse failure in the PL/pgSQL payload score comparison. The score extraction was simplified into typed local variables before comparison, and the follow-up CI run was queued against head `758c15bcb424a8fe398a0656776a6a6341f06976`.
- Migration 020's state-event table constraint was also corrected to allow a live match to carry a score while still requiring home/away score values to be both present or both absent.
- The source-link audit confirms 963 existing links across the six prospective competitions have matching original observation, first sighting, provider response, rights approval and payload hash. All six competition groups have zero team/competition materializer drift.
- The migration and state sync remain unmerged. The live Neon branch checks were read-only; no production DB changes have been made by PR #170.
- Next gate: exact-head CI must pass both backend tests/lint and Android debug build. Then review PR diff and mergeability. After merge, the main-branch migration workflow applies migration 020 and runs the guarded state sync. Only after that succeeds should Stage 6 be manually dispatched on main to materialize the 47 already-captured upcoming fixtures; no additional provider capture is required for that recovery attempt.


### PR #170 exact-head CI lint correction (24 November 2026)

- Exact-head CI run `45345323202` on head `f77f542352da4cfb007d50960352907b5af1ae9e` completed: Android debug build passed; backend test suite passed (565 tests); backend lint failed on two auto-fixable import rules only.
- Ruff findings: move `Sequence` from `typing` to `collections.abc` in `backend/app/canonical_fixture_states.py`; sort `typing.Any` before `urllib.parse.urlsplit` in `backend/scripts/materialize_and_adjudicate_daily_fixtures.py`.
- No test, migration, runtime, database or Android failure was reported in this run. These are formatting/import-order corrections; no functional behavior is changed.
- Next gate: rerun exact-head CI after the two corrections. Do not merge or apply migration 020 until all required checks pass.


## PR #170 merged and migration 020 production verification (24 November 2026)

### Merge and CI

- PR #170, `Automate guarded daily canonical fixture linkage`, was marked ready and squash-merged into `main` at 07:14:44 UTC.
- Merge commit: `1e7fc7b62cbf7c1b23a314f8e2995e1a7d10cb00`; merged PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/170.
- Exact PR-head CI run `45345669929` passed: backend tests/lint and Android debug build.
- Post-merge main CI run `45346493526` also passed both backend tests/lint and Android debug build.
- The Vercel commit status was `failure` with target `build-rate-limit`; this was a deployment-capacity limitation, not a code-test failure. PR #170 changes backend/workflow/database behavior, not website UI. Do not claim a Vercel deployment succeeded.

### Production migration and state sync — verified

- Automatic migration workflow run `45346493574` completed successfully on merge commit `1e7fc7b62cbf7c1b23a314f8e2995e1a7d10cb00`.
- Migration `020_canonical_fixture_state_events.sql` was applied; migration checksum verified as `2523bc886a801116fa722a89cbfab4483257b7bcf610bd190ff23f3888b15872`.
- Guarded PIT state synchronization completed successfully: 958 state events inserted, 958 state-provenance records verified.
- Migration workflow verified the required relations, functions, trigger set, and existing migration checksum/object ledgers. Entire workflow concluded success.
- Independent read-only Neon query on production branch `br-jolly-darkness-balgmi2t` / database `veltrix_ai_analyst` confirmed: 958 state events, 958 verified state-provenance rows, 963 existing 5Dollar canonical fixture source links, 47 upcoming scheduled fixtures, and one recorded migration-020 checksum row.
- No provider or Odds API requests were made during the migration or state sync.

### Post-merge preview ordering issue and recovery

- Merge push launched migration run `45346493574`, Stage 6 read-only preview `45346493500`, Stage 7 read-only evaluation `45346493504`, and CI `45346493526` concurrently.
- The first Stage 6 preview and Stage 7 evaluation attempts raced ahead of migration 020 and failed with `UndefinedTable: canonical_fixture_state_provenance_audit does not exist`. This was a migration-ordering race, not a data-integrity failure.
- After migration 020 and state sync completed, the failed read-only preview/evaluation jobs were rerun. At ledger update time, those reruns were still in progress; inspect exact run/job outcomes before claiming success.
- Stage 6's actual canonical fixture linkage/materialization is a separate `workflow_dispatch` on main. The connector does not expose a workflow-dispatch action. Do not infer that it ran from the migration or read-only preview. User-facing recovery path: repository Actions → “Stage 6 daily immutable snapshot and outcome materialization” → Run workflow on `main`.
- After manual Stage 6 completion, verify canonical linkage report, eligible fresh upcoming snapshots, and exact Stage 7 automatic inference child. Only a non-zero forecast count plus research API and Android visibility can establish research forecast availability.
- Production publication, certification, model promotion, and Value Bet remain locked. Do not claim the 47 upcoming fixtures have been linked until the Stage 6 canonicalization report confirms it.



## Post-migration preview recovery and canonicalization blocker (24 November 2026)

### Verified reruns after migration 020

- The Stage 6 read-only preview rerun in workflow run `45346493500` / job `138282758658` completed successfully after migration 020. Its log reports dataset SHA-256 `a8fdf0e9840a3fffcc4577c6a8cb3cc31d9ab8a9b0b2b9f2a49b18372040eb73`, 50 eligible prospective rows, 50 settled-label rows, and 2 expanding folds. Snapshot validation returned `VALIDATED_READ_ONLY`. This job did not write canonical fixture links or persist snapshots.
- The Stage 7 read-only evaluation rerun in workflow run `45346493504` / job `138282768937` completed successfully. It evaluated 50 fixtures and 50 settled labels across 2 folds. All reported markets had 50 walk-forward fixtures; only 6 distinct settled-label dates were represented. Status remained `RESEARCH_ONLY_NOT_PRODUCTION_APPROVAL`; certification was `BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE`; production promotion and Value Bet remained `LOCKED`.
- Stage 5 identity reconciliation preview run `45346632797` completed successfully. This was also read-only and is not the Stage 6 canonicalization operation.
- Main CI run `45346889551` on ledger commit `bf075f98bc2b3c8df61159d1f8a49a0ff6b52d50` completed successfully: Android debug build and backend tests/lint passed.

### Current live database blocker — independently rechecked

- A fresh read-only Neon query on production branch `br-jolly-darkness-balgmi2t`, database `veltrix_ai_analyst`, and the six approved 5Dollar competition IDs returned:
  - Upcoming provider fixtures: **47**
  - Upcoming fixtures with canonical source links: **0**
  - Upcoming fixtures without canonical source links: **47**
  - Upcoming fixtures with fully verified canonical source/state provenance: **0**
- Therefore the successful read-only preview/evaluation jobs do not resolve the 47-fixture linkage gap. The 50-row research evaluation is a historical/settled evidence evaluation and is not proof of fresh upcoming snapshots or forecasts.
- No post-merge actual Stage 6 `workflow_dispatch` run has been verified. The actual Stage 6 workflow is configured with `workflow_dispatch` on `main`; it performs the guarded canonical materialization/adjudication, builds the strict PIT dataset, persists immutable snapshots and append-only labels, then verifies persistence.
- The GitHub connector available in this session does not expose workflow dispatch. Do not claim the operation was started. Manual action remains: https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/stage-6-daily-snapshot-materialization.yml — select branch `main`, then run “Stage 6 daily immutable snapshot and outcome materialization”.

### Next execution sequence

1. Run Stage 6 manually on `main` once; it does not make provider or Odds API requests.
2. Inspect the Stage 6 canonical linkage report. Require all 47 upcoming fixtures to be either verified eligible or explicitly conflicted; unresolved upcoming fixtures must remain a hard failure.
3. Verify fresh upcoming PIT snapshots and their cutoff timestamps in the Stage 6 artifact and database.
4. Confirm the exact automatic Stage 7 inference child run and require a non-zero research forecast count.
5. Verify `/v1/research/predictions` and the existing Android test-app feed/parser/display without redesigning the app.
6. Keep production publication, model promotion, certification, and Value Bet locked. The current 50 labels across 6 dates are far below the user's 300 settled selections and 90 distinct-date certification thresholds; no certification pass is claimed.



### Research inference and Android feed contract recheck

- Independent read-only Neon inspection of `research_shadow_forecast_runs` shows the latest inference record is still `NO_FRESH_UPCOMING_SNAPSHOTS`, generated 24 November at 06:07:43 UTC, with 0 training fixtures and 0 forecasts. The newer Stage 7 run `45346493504` was an evaluation/certification workflow, not a shadow inference run; it did not create forecasts.
- The last stored non-empty inference is 21 forecasts from 22 November at 07:51:24 UTC, trained on 996 fixtures. It is now older than the research API's 36-hour freshness window, so it cannot serve as current upcoming forecasts.
- Android `PredictionApi.parseResearchPredictions` expects the same envelope metadata returned by `backend/app/routes/research_predictions.py`: `research_only=true`, `publication_status=NOT_PUBLISHED`, `production_promotion=LOCKED`, `value_betting=LOCKED`, plus the nested fixture/markets DTO. The app feed parser and backend serializer contract are structurally aligned in the inspected code.
- The research API intentionally returns a quarantined/empty response unless `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true` and the model admission record passes its hash/tier/lock checks. The production environment flag was not inspected and must not be assumed enabled. Verify it only after a fresh non-zero Stage 7 inference exists; do not weaken the admission record or release gates.
- The production API URL could not be independently opened by the available public web reader in this pass. No successful live API response or on-device prediction display is claimed.


### Stage 6 manual dispatch failure and PR #171 fix (24 November 2026)

- User supplied Stage 6 manual workflow run `45347792540` (job `138286480834`). The run completed with failure at the canonical fixture adjudication step; all downstream dataset/snapshot/persistence steps were skipped.
- Exact failure: `EXISTING_TEAM_MAPPING_DRIFT:1446563615`.
- Read-only production Neon inspection of provider team `1446563615` established:
  - Provider catalogue label: `Avaí`.
  - Existing canonical display label: `Avai`.
  - Canonical identity basis: `SOURCE_LOCAL_ONLY`.
  - Mapping: `EXACT_PROVIDER_ID`, status `REVIEW_REQUIRED`.
  - Provider team observation, source sighting, provider response, rights approval, payload SHA-256, source/provider IDs, and mapping provenance all match.
  - The only mismatch in the materializer's strict tuple comparison is the Unicode diacritic in the display label.
- No production rows were changed by the failed run. The materializer ran inside a transaction and failed before later stages; no fixture snapshots were built or persisted by this workflow attempt.
- PR #171: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/171
  - Branch: `fix/canonical-team-diacritic-drift`.
  - Head at PR creation: `f310855b6f86c66757a0cc9eed72d6445f8ed8c5`.
  - Narrow change: compare canonical/source team labels after Unicode NFD decomposition and removal of combining marks, while preserving canonical display labels. Every other field in the mapping tuple remains exact; substantive name changes and provenance/rights/identity mismatches still fail closed.
  - Unit cases cover accent-only equivalence (`Avai`/`Avaí`, `Sao Paulo`/`São Paulo`) and substantive mismatches.
  - PR CI run `45355197842` was still in progress at ledger update time; no merge authorized or performed yet.
- After PR CI passes and the diff is reviewed, merge PR #171. Then rerun Stage 6 once on main. Require its linkage report to resolve all 47 upcoming fixtures as verified or explicitly conflicted, with zero unresolved fixtures, before proceeding to PIT dataset build and persistence.
- No provider or Odds API calls were made during the incident investigation or fix preparation.


### PR #171 completed — canonical team diacritic drift correction (24 November 2026)

- PR #171 merged safely into `main` on 24 November 2026 at 08:25:13 UTC.
- PR head: `a2b0a6970a6702169e465094ade4881022339193`.
- Squash merge commit: `e3d3c4bae57860f176c0219693b8609837fffeda`.
- Exact-head CI run `45355726925` completed successfully:
  - Backend tests: success.
  - Ruff/lint: success.
  - Actionlint: success.
  - Backend compile: success.
  - Android debug build: success; debug APK artifact uploaded.
- Earlier failed CI attempt `45355356381` was due only to import ordering; that was corrected before the successful exact-head run. Its Android build had also passed.
- The code change preserves canonical display labels and relaxes only accent/diacritic differences. Provider identity, canonical team ID, rights, provenance, mapping method and mapping status comparisons remain strict.
- The PR's review-thread and review-submission lists were empty at merge time. No outstanding review threads were present.
- Vercel status for the branch was a deployment-rate-limit failure, not a code-check failure. No website changes were included and no deployment success is claimed.
- PR #171 resolves the specific `Avaí` vs `Avai` materializer drift at provider team ID `1446563615`; it does not itself create the 47 missing fixture links or persist Stage 6 snapshots.
- Stage 6 manual dispatch must now be run again once against `main` at merge commit `e3d3c4bae57860f176c0219693b8609837fffeda`. The available GitHub connector still has no workflow-dispatch action; use the workflow page and select branch `main`.
- Before dispatch, current last-known production state remains 47 upcoming fixtures, 0 canonical links, 47 unlinked, with no review events created by the failed Stage 6 attempt. Re-query before and after the next dispatch.
- Continue to keep production publication, model promotion, certification and Value Bet locked until fresh Stage 6/Stage 7/API/Android evidence and the full certification criteria pass.


### Post-PR #171 main CI and Stage 6 preflight audit (24 November 2026)

- Main-branch CI run `45355990778` completed successfully on ledger commit `5009ece9a74265175577ec90f46850ea43bb6b46`. Both Backend tests and lint and Android debug build jobs passed. This is separate from and follows the successful exact-PR-head CI `45355726925`.
- Read-only preflight against Neon project `young-wind-27772160`, branch `br-jolly-darkness-balgmi2t`, database `veltrix_ai_analyst` covered all six configured 5Dollar competition scopes.
- Each of the six competition scopes has exactly one currently valid approval satisfying the expected scope, data types and permitted uses.
- All six existing provider-competition identity links have exact provider IDs, canonical names, `SOURCE_LOCAL_ONLY` identity basis, expected `EXACT_PROVIDER_ID` / `REVIEW_REQUIRED` mapping values, and matching observation, rights, payload, source-sighting and provider-response provenance.
- Across the six scopes, 132 distinct provider teams were found; all 132 have complete source observation, matching rights, payload and successful provider-response/sighting provenance. Of those, 119 already have identity links and 13 do not; the materializer is designed to create the missing source-local mappings after the same evidence checks pass.
- Six existing team labels differ from source catalogue labels only by Unicode diacritics: provider team IDs `1446563615` Avaí/Avai, `1657329649` Ceará/Ceara, `2016651568` Operário PR/Operario PR, `4227927162` Cuiabá EC/Cuiaba, `4267737771` Náutico/Nautico, and `844813267` São Bernardo/Sao Bernardo. All six existing mappings have matching observation, rights and payload metadata; aggregate existing non-label drift count is zero. PR #171's accent-equivalence logic covers these cases without changing canonical labels.
- Across the six scopes, 1,533 provider fixture rows were found and all 1,533 passed read-only source observation, rights, entity identity, payload, successful response and sighting provenance checks. Five Brazil Serie A, one England Premier League, four Spain La Liga, and six Brazil Serie B rows have `UNKNOWN` status; the canonicalization contract permits `UNKNOWN` but does not allow it to carry scores. Finished fixtures missing scores: zero. Non-finished fixtures carrying scores: zero.
- All six provider-competition mappings have complete and matching provenance. These audits are read-only; they did not create identity links, fixture links, review events, snapshots, or state events and made no provider/Odds API requests.
- Latest independent upcoming-coverage query still reports 47 upcoming fixtures, 0 canonical source links, 47 unlinked, and 0 eligible verified upcoming fixtures. Canonical fixture state ledger remains 958 events, all 958 with verified provenance.
- Stage 6 workflow file on main exposes `workflow_dispatch` and restricts manual execution to `refs/heads/main`. The available GitHub connector has no workflow-dispatch operation; no new Stage 6 run exists after PR #171 merge. User must start one Stage 6 run from Actions UI using branch `main` at current main commit.
- Next: dispatch Stage 6 once; inspect its complete report and artifact. Require 47 upcoming fixtures to be either fully reviewed/verified or explicitly conflicted, zero unresolved, and verify persisted PIT snapshots before allowing Stage 7. Do not interpret preflight provenance completeness as successful materialization.
- Production API publication, production promotion, certification and Value Bet remain locked.
