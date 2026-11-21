# 2026-11-20 — First-launch activation checkpoint

## Repository state verified

- Default branch: `main`
- Main HEAD: `bea70392e45e97848d0df006ffef7dbb262bcb47` (PR #124 merge)
- Main CI run `44762169304`: completed successfully.
- PR #74 (`feature/hierarchical-sparse-team-rates`) remains open and unmerged. Its base SHA is behind current main; do not merge without rebasing/reconciliation and fresh CI.
- Existing prospective shadow workflow: `.github/workflows/prospective-shadow-predictions.yml`; scheduled daily at 05:00 UTC, manually dispatchable, and triggered after successful Stage 6 completion.
- Existing prospective capture workflow: `.github/workflows/prospective-5dollar-daily-capture.yml`; scheduled daily at 03:00 UTC (04:00 WAT), manually dispatchable.
- Existing shadow builder is read-only: max 25 fixtures, six-hour snapshot freshness, minimum 30 cutoff-valid training labels, no provider calls, no database writes, and all output remains NOT_PUBLISHED / promotion LOCKED / value betting LOCKED.
- Stage 6 output is consumed by the shadow workflow only after successful Stage 6 completion.

## Activation status at 2026-11-20 16:38 WAT

- The latest main commit includes the PR #124 capture reconciliation fix.
- The next scheduled capture opportunity is 2026-11-21 03:00 UTC / 04:00 WAT.
- The existing 19 November snapshots are too old for the six-hour shadow freshness gate. Do not run shadow inference against them as if they were current.
- The 20 November failed capture must not be blindly rerun: it used the pre-fix code and already made 13 provider requests. The France Ligue 1 identity conflict remains excluded.
- The current GitHub integration exposes repository reads and selected GitHub writes, but no workflow-dispatch action. Therefore a manual dispatch cannot be executed from this session. The scheduled capture remains configured; if it is missed, dispatch the existing workflow from GitHub Actions UI rather than repeating the old run.

## Remaining implementation gap

- `backend/app/research/prospective_shadow.py` generates deterministic, cutoff-safe shadow forecasts but does not persist them.
- The production prediction schema in migration 014 requires a PIT-certified, production-approved model artifact before a production prediction can be inserted or published. The current shadow model is explicitly research-only and must not bypass that guard.
- Build a separate append-only research forecast ledger for immutable shadow outputs, with fixture/cutoff/model identity, generated timestamp, training cutoff/hash, dataset and snapshot hashes, full market distributions, code commit, and idempotency constraints.
- Keep shadow research records separate from `predictions`, `published_predictions`, publication events and settlement events.
- Do not apply a new migration or write to production Neon without explicit user approval.

## Next execution sequence

1. Observe the 21 November 03:00 UTC capture on the corrected main commit; verify per-scope provider request counts, inserted/quarantined records and France conflict handling.
2. Verify Stage 6 materializes only independently validated scopes and produces fresh snapshots.
3. Confirm the automatic shadow workflow runs from that successful Stage 6 completion; inspect the artifact for training cutoff, label count, data hash, convergence, abstentions and <=25 forecasts.
4. Implement and test the append-only research forecast ledger separately from production publication.
5. Preserve the existing Android UI. Connect it only to eligible published forecasts once the model release and publication gates are genuinely satisfied.

## Safety boundaries

- No provider request or Odds API credit was spent during this checkpoint.
- No production database write, migration, prediction insert, publication, settlement insert or Vercel deployment occurred.
- Value betting and production promotion remain LOCKED.
- Verified facts are distinguished above from future scheduled actions; no capture or Stage 6 run after PR #124 is claimed as completed.

## Implementation added on PR #125

- Added migration `019_research_shadow_forecast_ledger.sql` defining a dedicated append-only research run ledger. It stores the complete report JSONB plus report hash, dataset/training hashes, model version, code commit, cutoff timestamps, forecast and abstention counts.
- Added `app.research.shadow_ledger` to validate the research-only state, all five market distributions, probability normalization, per-forecast pre-match chronology, model/training lineage, 25-fixture cap and stable idempotency key before any write.
- Added `scripts/persist_prospective_shadow_forecasts.py`. Writes require both the explicit CLI confirmation flag and `VELTRIX_SHADOW_LEDGER_WRITE_ENABLED=true`; the database URL must target `veltrix_ai_analyst`. Repeated identical runs are idempotent; conflicting content under the same run key fails closed.
- Added unit tests for immutable identity, locked publication/value-betting state, market balance, chronology, fixture cap, explicit write opt-in and database target. Extended migration integration assertions to include migration 019 and the append-only trigger.

## Verification boundary

- These changes are committed to the PR #125 feature branch; CI is the next verification gate.
- The scheduled shadow workflow remains read-only and was deliberately not modified to write to production Neon.
- Migration 019 has **not** been applied to production. The writer has **not** been executed. No production database write or provider request was made.
- Before enabling persistent writes, a separately approved migration and explicit production-write authorization are required. Do not add the production DB secret to Preview or automatically run the writer from the scheduled workflow.

## CI iteration

- First full backend test pass completed: **487 passed, 1 warning** on commit `558cb158026e3299505a19549b266dfa53bc06db`.
- Ruff then found three `TRY004` findings in the new validator (invalid input types were raised as `ValueError` rather than `TypeError`). Corrected those exception classes in commit `be89293df48ebdf0ea71b3fe2302648bf6d8a42b`.
- Fresh CI run `44766266221` is in progress against the corrected commit. Do not treat the earlier lint failure as passed; await this rerun's completed checks.


## 2026-11-20 — PR #125 final CI and migration safety review

- PR #125 head: `0260ce23ef871fc7ef9dc3b632b799dddd4c8f13`; base is current main `bea70392e45e97848d0df006ffef7dbb262bcb47`; PR remains open and GitHub reports it mergeable.
- CI run [44766392542](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44766392542) completed successfully on the exact PR head. Both jobs passed: Backend tests and lint; Android debug build. Earlier interrupted CI attempts are superseded by this completed run.
- The capture workflow remains scheduled for 03:00 UTC / 04:00 WAT daily. The only capture run found in the current recent run inventory is the pre-fix 20 November run [44725750217], which failed. No post-PR #124 capture, Stage 6 materialization or shadow forecast run is verified yet. Next scheduled capture is 21 November 04:00 WAT.
- Critical merge-safety finding: `.github/workflows/apply-database-migrations.yml` has a `push` trigger on `main` for `backend/migrations/*.sql`; its migration job automatically applies all pending migrations using the production database secret. Therefore merging PR #125 would trigger migration 019 against production. This is a production schema write, not a documentation-only merge.
- PR #125 is intentionally **not merged**. Migration 019 has not been applied and the writer has not been run. No production database write, provider request, Odds API credit use or Vercel deployment occurred in this checkpoint.
- Do not merge PR #125 or apply migration 019 without explicit production-write authorization. Safe alternative under evaluation: preserve immutable shadow reports as GitHub Actions artifacts first, with hashes and run metadata, without production Neon persistence. Revisit the DB ledger only through an explicitly approved migration path.
- France Ligue 1 remains excluded for its unresolved provider fixture identity conflict. Publication and value betting remain locked.


## 2026-11-20 16:52 WAT — Production migration approval and execution

### Authorization
- Project owner explicitly approved production migration and associated write operations on 2026-11-20.
- Scope executed: merge PR #125 and apply migration 019 only. Existing production data was not intentionally modified or deleted. No prediction or publication records were inserted.

### Repository and CI
- PR #125 merged successfully by squash. Merge commit: `ad91e87d1e9aacd21c3e77680f9d89646b239c31`.
- PR CI run [44766975475](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44766975475): backend tests/lint and Android debug build both passed.
- Main push CI run [44767283702](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44767283702): completed successfully.
- Production migration workflow [44767283690](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44767283690): completed successfully; every job step passed.

### Production database migration
- Migration runner output: `MIGRATIONS_APPLIED: 019_research_shadow_forecast_ledger.sql`. No other pending migration was applied.
- Post-migration verification checked migrations 006–018 and required prediction-storage, PIT, identity, snapshot-label and settlement objects. All workflow verification steps passed.
- Independent read-only Neon query against production database `veltrix_ai_analyst` confirmed:
  - Migration 019 checksum recorded: `6d6b8a191253edcf19e04718d595b57bcb3aa3ca58f3059615f30b8b6b970a4e`.
  - Table `veltrix_ai_analyst.research_shadow_forecast_runs` exists with 14 columns.
  - Append-only trigger `research_shadow_forecast_runs_append_only` is enabled.
  - Index `research_shadow_forecast_runs_generated_idx` exists.
  - Research ledger rows: 0 (migration created schema only; no report persisted yet).
  - Production `predictions` rows: 0; `published_predictions` rows: 0. No forecast publication was created by the migration.
- Existing data was preserved; no DELETE, TRUNCATE or destructive schema operation was run.

### Production API compatibility
- `GET /health`: HTTP 200, service status `ok`.
- `GET /ready`: HTTP 200; database connected, migrations current, prediction storage available.
- `GET /v1/predictions/history`: HTTP 200; returns an empty prediction list, consistent with the verified zero published prediction rows.
- Vercel deployment lookup for merge SHA returned no matching deployment at check time. No Vercel deployment was required for this database-only schema change; the existing production API remained healthy.

### Current release boundary and next work
- Migration 019 is applied and verified. The explicit report writer remains opt-in; it has not yet been executed. The research ledger is empty.
- Next safe execution: wait for the scheduled 21 November 04:00 WAT post-PR #124 capture; verify Stage 6 and shadow forecast artifact; then validate and persist the research-only report using the approved isolated ledger writer.
- Production prediction publication, model promotion and value betting remain LOCKED until the independent prospective certification gates pass.
- France Ligue 1 remains excluded pending provider fixture identity reconciliation.
- This section supersedes earlier statements in this checkpoint that migration 019 had not been applied or required future authorization. Those statements were accurate before the approval and execution recorded here.


## 2026-11-20 — Android launch-readiness preparation checkpoint

### Repository evidence reviewed
- Rechecked the live repository and Actions inventory before making launch-readiness statements. The latest observed main CI run is [44767283702](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44767283702), completed successfully on the PR #125 merge SHA; the production migration run [44767283690](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44767283690) also completed successfully.
- The most recent observed Stage 5 identity reconciliation preview is [44767447965](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44767447965), completed successfully. This is not evidence of a fresh post-fix fixture capture.
- The only capture run in the recent Actions inventory remains the pre-fix failed run [44725750217](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44725750217). A successful post-fix capture, subsequent Stage 6 materialization and shadow forecast artifact have not yet been verified.

### Android integration review
- Reviewed `android/README.md`, `PredictionApi.kt` and `VeltrixDashboard.kt` on main.
- Existing Android screens/design remain in place. The client already calls `GET /v1/predictions` and `GET /v1/predictions/history`; empty prediction responses are represented as an empty state, while API/network errors are represented separately. No sample fixtures or fabricated metrics are bundled.
- Android README explicitly distinguishes successful CI compilation from live prediction display and physical-device verification. The prior PR CI run confirms the debug build passed; no physical-device test is claimed in this checkpoint.

### Launch preparation and boundaries
- Capture workflow is scheduled for 03:00 UTC / 04:00 WAT on 21 November. Stage 6 is configured to run after a successful capture; shadow inference is configured after successful Stage 6 materialization and also on its own schedule.
- Shadow inference is read-only with respect to the database and provider (zero provider calls, zero database writes), capped at 25 fixtures, requires snapshots no older than six hours and at least 30 cutoff-valid training fixtures, and explicitly marks forecasts research-only/not published with promotion and value betting locked.
- Target for 21 November: verify the post-fix capture, Stage 6 materialization, shadow forecast artifact, and Android/API end-to-end readiness. A working demonstration is conditional on valid eligible forecasts and passing checks; it is not represented as a guaranteed certified production launch.
- No code changes, provider requests, Odds API credit use, Vercel deployment, or additional production database writes were made during this readiness review.

### Next actions
1. Inspect the 21 November scheduled capture run and verify per-scope outcomes and artifacts.
2. Confirm Stage 6 snapshot/label materialization and lineage checks.
3. Inspect the shadow forecast artifact for status, hashes, training cutoff/count, fixture count, abstentions, probability validity and convergence.
4. If a valid report exists, validate and persist it only through the already approved research-only ledger writer; verify append-only persistence. Do not insert into production prediction/publication tables.
5. Run/inspect Android integration and physical-device release checks where available; preserve the existing UI.
6. Keep publication, model promotion and value betting locked until the agreed certification criteria are met.

### Evidence classification
- **Verified:** repository workflow definitions, current Actions results listed above, Android API integration code and documented build/device distinction.
- **Pending:** next scheduled capture and its downstream Stage 6/shadow outputs, plus physical-device verification.
- **Not claimed:** successful post-fix capture, generated forecasts, live predictions displayed in the app, or full certified production release.


## 2026-11-20 — PR #74 integration blocker review

### Repository evidence
- Rechecked live main: `a608d37c1eb42bbda2ead0b75e54778235d4d432`.
- PR [#74](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/74) remains open and unmerged. It adds a competition-aware hierarchical Poisson goal-rate component and sparse-team tests, but its own description states it is not wired into prediction orchestration/API or production.
- PR #74 head is `15c62661e30781e305eac00afc0ebd400fe3ec13`; its base/merge-base is `e137a8525dee5f9231a1f6423661b639b72810ff`. GitHub comparison reports the PR branch diverged from current main: 2 commits ahead and 290 commits behind. PR metadata reports `mergeable=false`, and the head combined-status endpoint returned no status checks.
- Current Android README confirms the app reads only the published `GET /v1/predictions` contract; an empty response is displayed as “No upcoming predictions”. CI build alone does not verify live prediction display or physical-device behavior.

### Decision / next steps
- Do not merge PR #74 in its current state. It is materially stale against main and has no current head status evidence. First rebase/reconstruct the model component against current main, rerun its tests and full CI, and review the statistical implementation before considering integration.
- Do not wire the component into production prediction orchestration or expose forecasts until chronology, hyperparameter selection, convergence, calibration, and prospective evaluation requirements are satisfied.
- Keep Android UI and published API contract unchanged. The launch path remains dependent on successful post-fix capture, Stage 6 materialization, eligible shadow output, and safe demonstration/publication boundaries.
- No code merge, branch rewrite, provider request, Odds API credit use, deployment, or production database write was performed during this review.

### Evidence classification
- **Verified:** main SHA, PR metadata, comparison divergence counts, absent PR head status entries, and Android published-endpoint contract.
- **Pending:** current-main rebased model implementation, fresh CI, integration review, next scheduled capture, Stage 6 and shadow outputs, and physical-device verification.


## 2026-11-20 — PR #74 statistical review

- Posted a non-approval engineering review comment on PR #74 (review ID `5996224886`). GitHub rejected a formal REQUEST_CHANGES review because the connected account is the PR author; a COMMENT review was successfully recorded instead.
- Findings recorded: optimizer convergence is not exposed/enforced; ridge penalty scaling appears to weaken with larger total sample weight under the current gradient normalization; centering/reparameterization requires derivation and invariance tests; tests do not establish fit recovery, convergence, numerical stability, chronology, or row-order invariance.
- Required before resubmission: reconstruct/rebase against current main, define and test the penalized objective, expose convergence diagnostics and fail-closed behavior, add synthetic recovery/held-out and invariance tests, then run full CI. No merge or production integration is approved by this review.
- No provider requests, Odds API credit use, deployments, or production database writes were performed.


## 2026-11-20 — launch-chain and current-main model preflight

### Findings
- Re-inspected the three live workflow definitions on current main. Capture is scheduled at 03:00 UTC (04:00 WAT), bounded to yesterday's results plus a rolling seven-day fixture window, with a request budget of 4 and a production database/schema preflight before provider access.
- Stage 6 is triggered only by a successful capture completion (or its own workflow-file push), builds the strict PIT dataset, refuses to persist if no eligible prospective rows exist, and verifies persisted snapshot/label counts plus append-only guards.
- Shadow inference is triggered by successful Stage 6 completion (and separately scheduled at 05:00 UTC / 06:00 WAT). It is read-only, caps forecasts at 25, enforces a six-hour snapshot age and at least 30 cutoff-valid training fixtures, and uploads a research-only artifact.
- Reviewed current-main `backend/app/models/hierarchical_poisson.py`: unlike the stale PR #74 head reviewed above, current main already includes an explicit penalized objective, normalized likelihood plus ridge penalty, backtracking line search, convergence diagnostics, and fail-closed non-convergence. Prediction output also reports history-aware calculation modes. This is a verified difference between current main and PR #74's stale branch; do not apply PR #74 review findings to current main without rechecking the exact code revision.
- Reviewed current-main shadow builder and ledger validator. The builder's terminal statuses align with the ledger's allowlist; successful forecasts carry research-only flags, market distributions, cutoff/training lineage and explicit NOT_PUBLISHED / LOCKED statuses. No Android shadow endpoint exists in the inspected client; Android continues to consume only published prediction endpoints.

### Operational decision
- No early/manual capture was triggered today. Preserve the scheduled 21 November run and provider request budget.
- No Android API change or UI redesign is justified before tomorrow's evidence exists. Do not route research-only forecasts into the published endpoint to create a demo.
- Tomorrow's operator action is only to inspect completed GitHub Actions runs/artifacts; no manual upload or data entry is required from the user.
- No provider calls, Odds API usage, Vercel deployment, or production DB writes were performed during this preflight.


## 2026-11-21 06:26 WAT — scheduled capture verification

### Live repository state
- Rechecked the live default branch: `main` is at `13bcef1d0135f7d45cfc04d13bd63f34c9cb40d3` (`docs(ledger): record launch pipeline preflight`).
- Open PR inventory still contains PR #74 only; it remains open and is not part of today's capture execution.
- The capture workflow on current main remains configured with cron `0 3 * * *` (04:00 WAT), plus manual dispatch. It targets yesterday's settlements and a rolling seven-day forward fixture window, with request budget 4.
- The Stage 6 workflow remains gated on successful completion of the capture workflow. The shadow workflow remains gated on successful Stage 6 completion (and has its own 06:00 WAT schedule).

### 21 November capture status
- As of 06:26 WAT, the GitHub Actions scheduled-run inventory contains no 21 November run for the prospective 5Dollar capture workflow.
- The newest capture run available is [44725750217](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44725750217), created 2026-11-20T11:12:59Z, event `schedule`, head SHA `6b6c045a50572cf22f12d6ca95038fca81d91b36`, conclusion `failure`. This run is not evidence of a 21 November capture and does not run from today's current main SHA.
- Its job log reports all seven competition scopes failed. Brazil Serie A, Brazil Serie B, England Premier League, Germany Bundesliga I, Italy Serie A and Spain La Liga reported `FIXTURE_SIGHTING_COUNT_MISMATCH` and `IMPORT_COUNTER_RECONCILIATION_FAILED`; Brazil Serie B additionally reported `NO_FIXTURE_DATA_IMPORTED`. France Ligue 1 failed separately with `PROVIDER_FIXTURE_IDENTITY_CONFLICT`.
- The prior audit for this run recorded 13 provider requests and 58 records observed. The log shows partial ingestion counters for some scopes; therefore this must not be described as a zero-write run. No additional provider request was made during this verification.
- Stage 6 run [44727606590](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44727606590) completed with its materialization job skipped. The capture and Stage 6 runs each have zero uploaded artifacts.

### Decision / blockers
- No successful 21 November capture, fresh Stage 6 dataset, or shadow forecast artifact is verified. No Android live-prediction demonstration can be claimed from this evidence.
- Do not manually rerun the failed 20 November capture: it already consumed provider requests and was executed on an earlier commit. Do not spend Odds API credits; no Odds API calls were made.
- The connected GitHub action set exposes workflow run reads and logs but no workflow-dispatch action. A manual dispatch could not be initiated from this session. If the 21 November schedule remains absent, dispatch the existing capture workflow from GitHub Actions UI only after confirming the corrected current-main implementation and checking the request budget.
- Next engineering action: inspect the current-main capture reconciliation implementation against the failed run's exact failure counters, verify whether the fix is present on current main, and add a focused regression test before any further provider execution. Preserve France Ligue 1 exclusion until its identity conflict is resolved.
- Publication, production promotion and value betting remain LOCKED. No code changes, production DB writes, deployments, provider requests or Odds API usage occurred during this 06:26 WAT verification.

### Evidence classification
- **Verified:** current main SHA; current workflow configuration; absence of a 21 November scheduled capture in the returned Actions inventory; 20 November capture run status, head SHA and job logs; seven failed scopes and their logged error classes; Stage 6 skipped status; zero artifacts for those two runs.
- **Not verified:** whether GitHub will deliver a delayed scheduled run later on 21 November; whether the current-main reconciliation code fully resolves the observed mismatch; any 21 November snapshot or shadow forecast.


### Follow-on code-path review — 21 November 06:35 WAT
- Inspected current-main `scripts/collect_5dollar_all_approved_competitions.py`, `backend/app/providers/historical_validation.py` and `backend/app/providers/historical_import.py`.
- Confirmed the failed 20 November capture ran on historical SHA `6b6c045a50572cf22f12d6ca95038fca81d91b36`. At that revision, validation compared total fixture sightings directly with `records_inserted`, which can reject a response containing duplicate observations even when fixture ingestion is otherwise represented.
- Current main (`13bcef1d0135f7d45cfc04d13bd63f34c9cb40d3`) has a materially revised check: it compares sighting rows with distinct (provider entity ID, payload hash, response ID) tuples, and separately verifies distinct provider fixture rows against inserted counters. It also reconciles legacy duplicate counters from immutable evidence when permitted.
- The collector continues independently across competition scopes, records each scope failure, and returns success only when at least one scope validates. This is designed to permit Stage 6 to consume validated scopes after partial success.
- This source review establishes that current main differs from the failed run's validator; it does **not** establish that the current implementation passes against live provider data. A fresh scheduled/manual capture is still required for runtime proof.
- No provider call, database query/write, workflow dispatch, deployment or Odds API request was made during this follow-on review.


## 2026-11-21 06:38 WAT — prospective capture scope correction

### Live repository review
- Confirmed current main before the change: `26d38becb0d7b1294a01cd084c276f3465c2cfbc`.
- Confirmed PR #74 remains the only pre-existing open PR.
- Re-read the active collector, capture workflow, historical validator/importer, and the full historical-import integration test file.
- Found that the active collector tuple still included France Ligue 1 (provider competition ID `3614399544`) even though the prior ledger explicitly said France remained excluded pending identity reconciliation. This was an implementation/configuration mismatch.

### Change prepared on PR #126
- Created `backend/app/providers/prospective_capture_scope.py` as the single explicit allowlist for the prospective capture's active competitions.
- Excluded France Ligue 1 without changing source-rights approvals, historical records, or other ingestion scopes.
- Kept Brazil Serie A, Brazil Serie B, England Premier League, Germany Bundesliga I, Italy Serie A, and Spain La Liga.
- Updated `scripts/collect_5dollar_all_approved_competitions.py` to consume the centralized allowlist.
- Added `backend/tests/test_prospective_capture_scope.py` to enforce six unique approved active competition IDs and prevent France from being reintroduced accidentally.
- PR: [#126](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/126)
- PR head at creation: `b352f65e1bed70ddd106fc350925d7cc972871df`.
- CI run [44871749422](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44871749422) was queued when this ledger entry was prepared; no test result is claimed yet.

### Validator assessment
- Current validator already has a regression test for repeated identical fixture objects and repeated fixture sightings across provider responses.
- Legacy duplicate-counter recovery is conditional on zero rejects/quarantines and is followed by independent checks for captured fixture sightings, distinct sighting tuples, materialized provider fixture rows, request/response lineage, and PIT timestamp provenance. It does not bypass those evidence checks.
- The source review does not establish live-provider correctness; the corrected capture still needs a controlled runtime execution after CI and merge.

### Execution boundary
- No provider request, production DB query/write, workflow dispatch, Odds API request, Vercel deployment, or Android change was performed.
- Do not dispatch capture while PR #126 is unmerged or CI is pending.
- Next: inspect CI run #44871749422 and its exact head SHA; resolve any failures; merge only after all required checks pass; then manually dispatch the corrected workflow once and inspect per-competition counters and immutable evidence.
- Production prediction publication, model promotion, and value betting remain LOCKED.


## 2026-11-21 06:55 WAT — corrected prospective capture completed

### Run identity and execution
- Manually dispatched prospective capture run [44872062807](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44872062807), job [136748574209](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44872062807/job/136748574209).
- Job conclusion: `success`; all setup, database/schema preflight, capture and cleanup steps completed.
- The job checked out corrected main commit `5735b4126ea228c078d60af18e5b5b97dd6f86ca`, confirming execution included PR #126's centralized six-competition allowlist and France exclusion.
- Capture window: `2026-11-20T00:00:00Z` through `2026-11-29T00:00:00Z`, covering yesterday's settlements and the rolling forward fixture horizon.
- Provider used: 5DollarFootballAPI. The Odds API was not called.

### Per-competition outcomes
| Competition | Import run | Inserted | Provider requests | Status |
|---|---:|---:|---:|---|
| Brazil Serie A | 33 | 3 | 2 | COMPLETED_VALIDATED |
| Brazil Serie B | 34 | 0 | 2 | COMPLETED_VALIDATED |
| England Premier League | 35 | 3 | 2 | COMPLETED_VALIDATED |
| Germany Bundesliga I | 36 | 5 | 2 | COMPLETED_VALIDATED |
| Italy Serie A | 37 | 3 | 2 | COMPLETED_VALIDATED |
| Spain La Liga | 38 | 4 | 2 | COMPLETED_VALIDATED |
| **Total** | — | **18** | **12** | **6/6 validated** |

- Batch summary: `competitions_total=6`, `failed_competitions=0`, `validated_competitions=6`, status `COMPLETED`.
- France Ligue 1 (provider ID `3614399544`) was not included, as required while its identity conflict remains unresolved.
- Brazil Serie B inserted zero new records but its import scope passed validation. This does not establish complete historical coverage for that competition.
- The log reports inserted counts and validation statuses. Do not infer that all observed provider records were new inserts; detailed sighting/duplicate/reject/quarantine reconciliation remains a downstream audit item.
- Total provider requests for this run: 12. No Odds API credits were used.

### Downstream gates and boundaries
- Capture job success is verified. Stage 6 materialization and the subsequent shadow workflow are **not yet verified** in this entry; inspect their own run IDs, job logs and artifacts before claiming snapshots or forecasts exist.
- The capture job itself uploaded no artifacts.
- No production prediction or publication rows were created by this capture workflow. The workflow performed the approved prospective source-data ingestion into the production research dataset; this is distinct from forecast publication.
- Production publication, model promotion and value betting remain LOCKED. No forecasts are approved for the Android published-prediction endpoint based on capture success alone.

### Next actions
1. Verify the automatic Stage 6 workflow_run execution, its exact commit/run ID, materialization outcome, snapshot/label counts, PIT lineage and append-only checks.
2. If Stage 6 succeeds, inspect the downstream shadow workflow and its artifact for terminal status, cutoff-valid training count, snapshot freshness, hashes, convergence, abstentions, market distributions and <=25 fixture cap.
3. If a valid research report exists, validate and persist it only through the previously approved research-only ledger writer; independently verify append-only persistence. Never write it into production prediction/publication tables.
4. Audit the import-run rows and immutable provider-response/sighting evidence for all six import runs, including duplicates, rejects and quarantines. Treat zero inserts for Brazil Serie B as an observed result, not as a failed scope or a proof of completeness.

### Evidence classification
- **Verified from job 136748574209 logs:** checked-out SHA, database/schema preflight success, capture window, six competition results, 12 total requests, 18 inserted records, zero failed scopes, and job success.
- **Pending independent verification:** Stage 6 materialization, shadow forecast artifact, detailed per-run raw evidence reconciliation and any research-ledger persistence.
