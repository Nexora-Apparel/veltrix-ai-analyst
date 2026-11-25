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
