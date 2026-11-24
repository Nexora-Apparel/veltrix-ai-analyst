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
