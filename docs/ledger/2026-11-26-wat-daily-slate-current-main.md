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
