# 2026-11-26 — WAT daily slate correction (rebased on current main)

## Problem
Stage 7 selected upcoming fixtures by kickoff order and capped at 25 without first restricting kickoff dates to the current Africa/Lagos calendar day. This allowed tomorrow's fixtures to fill the daily slate.

## Implementation
- Added `backend/app/wat_calendar.py` with timezone-aware, inclusive-start/exclusive-end UTC boundaries for the current `Africa/Lagos` day.
- Stage 7 now filters eligible, future fixtures to that WAT window before chronological sorting and the maximum-25 cap.
- Published prediction list and single-prediction retrieval now enforce the same current-WAT-day bounds.
- Research prediction query now enforces the same WAT-day bounds while retaining the existing 36-hour run-age condition.
- Added unit coverage for WAT midnight boundaries, timezone-awareness, exclusion of tomorrow, empty daily slate, cap-after-filter, and API query parameters.

## Preserved safeguards
- Six-hour PIT snapshot age and all Stage 7 row eligibility/cutoff checks are unchanged.
- Research predictions remain `RESEARCH ONLY` and `NOT_PUBLISHED`.
- Production promotion and Value Betting remain `LOCKED`.
- No provider or Odds API calls, production database writes, inference dispatches, publication, or model promotion were performed.

## Verification
- This branch was created from current `main` at `7cc3bb77acc6a6a1947d875cf0f8a56ceb4f2fd4`, avoiding the 52-commit divergence discovered on the earlier PR branch.
- Exact-head CI has not yet run for this branch. Draft PR checks are the next gate.
- Vercel preview and CI results must be checked against the exact latest head.
- Physical Android device verification remains outstanding.

## Release decision
Not release-ready. Keep draft until exact-head backend tests/lint and Android build pass, code review is complete, and the Android app is verified to display only today's WAT fixtures.

## Exact-head CI verification
- Verified code head: `e74a343c3912046330a3aa5d41bcbc468b2b354e`.
- CI run [#1365](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45808399605) completed successfully against that exact head.
- Backend: 592 tests passed; Python compile passed; actionlint passed; Ruff reported `All checks passed!`.
- Android: debug APK assembled and uploaded successfully.
- Vercel Preview deployment completed successfully; Vercel Preview Comments check passed.
- Artifact: `veltrix-ai-analyst-debug-apk`, artifact ID `15110343136`, SHA-256 `d9c4a893340a562add36f19cbe747f88ae311f8287f43b3d3f7732d34dcfcc00`, expires 2026-12-03.
- The final code head remains the PR #179 head at the time of this verification.

## Remaining manual validation
- CI cannot verify runtime rendering or the API response on the user's physical Android device.
- Before production merge, verify on-device that today's list contains only fixtures whose kickoff date is today's Africa/Lagos date; ensure tomorrow's fixtures are absent even when today's slate has fewer than 25.
- If there are no eligible fixtures today, the daily list must be empty rather than populated with tomorrow's fixtures.
- This PR remains draft and unmerged pending physical-device validation. Preview deployment is not production deployment.


## User-reported Android observation — 2026-11-26 12:28 WAT
- User reports that the Predictions screen displays 25 predictions on the Android debug build from CI run #1366.
- This is device-level evidence that the screen renders a populated 25-item list.
- The observation does **not** yet establish that all 25 kickoff dates fall within 2026-11-26 Africa/Lagos, nor that tomorrow's fixtures are excluded, nor the fewer-than-25/empty-slate cases.
- Status: partial manual verification only; date membership and boundary behavior remain unverified. Keep PR #179 draft and unmerged.


## Latest-head CI and workflow schedule audit — 2026-11-26 12:32 WAT
- PR #179 latest head `e327fcdb174d25199734c4372d4f2c0b623680ae` has exact-head CI run [#1367](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45810907938), completed successfully.
- Verified jobs: Backend tests and lint — success; Android debug build — success.
- GitHub currently reports PR #179 open, draft, unmerged, and mergeable.
- Updated the PR description to replace stale CI/device-verification wording and distinguish the user's reported 25-item screen from the still-unverified WAT date membership.
- Workflow schedule audit from current `main`:
  - Prospective 5Dollar capture is scheduled at `17 0 * * *` UTC (01:17 WAT).
  - Stage 6 is triggered after successful capture workflow completion on `main`.
  - Stage 7 research inference is triggered after successful Stage 6 completion for a `main` run; its manual dispatch path requires explicit `confirm_research_ledger_write=true`.
  - The separate `prospective-shadow-predictions.yml` workflow has its inference job hard-disabled with `if: false`.
- Critical sequencing constraint: because PR #179 is still unmerged, the normal scheduled `main` pipeline on 2026-11-27 will execute the current `main` code, not the WAT correction. Therefore that scheduled output cannot validate PR #179 unless the candidate code is run through an explicitly controlled branch-specific research workflow or is merged first. Do not merge solely to obtain a validation run; do not dispatch Stage 7 or write to the research ledger without explicit authorization.
- Current time check: 2026-11-26 12:32 WAT. The next WAT calendar day is 2026-11-27.
- No inference dispatch, production deployment, provider request, Odds API request, production DB write, merge, publication, or Telegram delivery was initiated in this continuation.
- Status: exact-head CI passed; user-reported screen render is partial device evidence; end-to-end WAT-date validation remains blocked by the fact that scheduled Stage 7 runs from `main` while the correction is still on an unmerged draft PR.


## Read-only candidate validation path — 2026-11-26
- User explicitly authorized implementation and execution of a **read-only** validation path. This authorization does not extend to research-ledger writes, production writes, publication, deployment, model promotion, or merging the WAT correction.
- Added `backend/scripts/validate_stage7_wat_daily_slate.py` on the WAT candidate branch. It rebuilds the approved PIT dataset through the existing `build_report` function, runs the candidate Stage 7 selector and inference in memory, and writes a local JSON validation manifest. It records the WAT date and UTC window, selected fixture IDs, kickoff/cutoff timestamps, snapshot ages, count, inference status, and safety flags.
- Source audit: `build_prospective_dataset.build_report` begins a PostgreSQL `REPEATABLE READ, READ ONLY` transaction and the dataset-builder source contains no SQL write statements. The validator does not call provider APIs, The Odds API, or `persist_prospective_shadow_forecasts.py`. Its only output write is the local GitHub Actions artifact file.
- Candidate validator commits: initial `116b83a327a1d40b9448016ca704c802d46a7d7b`, cleanup `a20d55dc32bd58c4cb330fd31e6aed1fc25ef083`, and import-order correction `fb92a479bf358ee6e15915e584fc80a628830909`. Confirm the current branch head before dispatch; do not assume this SHA remains current if further commits are added.
- Added a separate, manual-only workflow in draft PR [#180](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/180). It accepts an exact 40-character candidate SHA, checks out and verifies that exact commit, has `contents: read` permissions, uses the existing protected `veltrix-historical-import` environment, and uploads only the validation manifest. It contains no scheduled trigger, workflow_run trigger, persistence step, or publication step.
- PR #180 must be reviewed and made available on the default branch before GitHub permits dispatch of this new workflow. It remains draft and unmerged. Do not bypass branch protection or merge automatically.
- Candidate PR #179 remains draft and unmerged. A CI run triggered for an intermediate validator commit was cancelled when the branch was updated again; therefore it is not exact-head CI evidence. Recheck CI for the latest candidate head before any dispatch.
- The existing PR #179 latest-head CI run #1368 remains verified successful for the preceding code/ledger head, but it predates the new validator script.
- Execution timing: the next normal 5Dollar capture is scheduled for 2026-11-27 01:17 WAT, with Stage 6 following. The ordinary scheduled Stage 7 on `main` still cannot validate PR #179. Once PR #180 is reviewed and present on the default branch, run its manual workflow only after the 2026-11-27 Stage 6 dataset is complete, pinned to the exact current PR #179 candidate SHA.
- Required manifest checks: current WAT-day-only membership, no next-day fill, maximum 25 applied after date filtering, chronological order, unique fixture IDs, selector/inference count agreement, and valid empty-slate behavior. A zero-fixture day is a successful empty-slate validation, not a reason to fill with tomorrow's fixtures.
- No candidate validation dispatch, database write, research-ledger write, provider request, Odds API request, production deployment, PR merge, publication, Telegram delivery, or model promotion has been performed in this step.
- Release remains blocked pending review/availability of PR #180, exact-head CI for the latest PR #179 commit, a successful read-only WAT-date manifest, Android verification of fixture date membership, and the existing independent certification gates.


## Validator edge-case hardening — 2026-11-26
- Hardened `validate_stage7_wat_daily_slate.py` for the valid case where eligible same-day fixtures exist but Stage 7 correctly abstains because cutoff-valid training labels are unavailable. The validator now distinguishes selector validation from inference readiness instead of incorrectly reporting a selector/inference count mismatch when Stage 7 has no inference summary.
- The validator still fails closed on non-WAT-day selection, over-cap selection, duplicate fixture IDs, non-chronological selection, missing unexpected inference summary, or count mismatch when an inference summary is present.
- Latest validator code commit: `f888f8e1b2da999366ada1f03c04feffdd4af884`. The branch head may be a later ledger-only commit; obtain the live PR #179 head SHA immediately before any manual validation dispatch.
- No read-only validation workflow dispatch has occurred. PR #180 remains a draft proposal for review and must be available on the default branch before the manual workflow can run.


## Candidate validator CI verification — 2026-11-26
- Candidate validator code commit `f888f8e1b2da999366ada1f03c04feffdd4af884` was rechecked through CI run [#1374](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45813000420), backend job rerun completed successfully.
- Verified in the backend job: actionlint success, Python compilation success (including backend scripts), `592 passed` in pytest, and Ruff `All checks passed!`.
- The Android job in run #1374 was cancelled before build. This PR adds no Android source changes; Android debug build had already completed successfully in CI run [#1368](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45811608351). Do not describe #1374 as a complete two-job pass.
- The read-only workflow in PR #180 was tightened to require that the exact requested SHA is an ancestor of `fix/wat-daily-slate-current-main`, in addition to checking out and verifying that SHA. The workflow YAML parsed successfully in a local YAML parser; no GitHub actionlint run for PR #180 has yet been recorded.
- PR #179 remains draft/unmerged; PR #180 remains draft/unmerged. The manual read-only validation has not been dispatched. No production or research database writes, provider requests, Odds API requests, deployments, publication, Telegram delivery, or model promotion occurred.
