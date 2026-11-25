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

## Verification

- Read back the branch workflow file after the update; exact contents confirm the restrictive predicate is absent and all other gates remain.
- PR #176 is open, targets `main`, is based on `3a301f6b5f92120c25c5722038b5172dde4a6c12`, and GitHub now reports it mergeable.
- Vercel Preview deployment is Ready. This is not backend CI evidence.
- The commit status exposes only Vercel; the available workflow-run lookup returns no PR CI runs for the exact head. Backend tests, lint, actionlint/workflow validation and Android build remain unverified. Do not merge.
- No workflow was dispatched. No database write, provider/Odds API request, forecast publication, promotion, certification or Value Bet unlock occurred.

## Next gates

1. Obtain exact-head CI evidence for PR #176: backend tests, lint, actionlint/workflow validation and Android debug build.
2. Resolve any CI failure and rerun against the new exact head.
3. Merge only after required CI passes and the PR remains mergeable.
4. Manually dispatch Stage 6 on `main` only; verify the successful Stage 6 run automatically starts Stage 7.
5. Inspect the Stage 7 report and isolated research ledger for fresh nonzero forecasts, timestamps, fixture identities and eligibility decisions.
6. Then validate research API exposure and the existing Android feed/parser/screens. Do not redesign the app.

Production publication, model promotion, certification and Value Betting remain locked until their independent evidence gates pass.
