# 2026-11-22 — PR #145 merge, Stage 7 handoff, and capture timing checkpoint

## PR #145 merge and exact-head verification

- PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/145
- Title: Stage 7 Newton model — research-only shadow integration.
- Exact tested PR head: `a880af8e4fe6280630a5856bcc703dbefc95b2dd`.
- Exact-head CI run: [44956826163](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44956826163), completed successfully.
- Backend tests step passed; backend lint step passed; Android debug build and APK upload passed.
- PR marked ready for review, then squash-merged with expected-head guard.
- Merge commit on `main`: `cfe5671d380b7846006ca5bf93e7a880d75003e2`.
- GitHub post-merge issue state confirmed PR #145 closed. Repository commit search lists the merge commit as the latest commit on the default branch at verification time.
- Merge scope is research-only. Model remains `hierarchical-poisson-newton-shadow-v2`, SHADOW / RETROSPECTIVE_NOT_PIT_CERTIFIED. Production promotion, value betting and app display remain locked.
- No inference dispatch, research-ledger database write, provider request, odds request, schedule activation, quarantine change or production lock change was performed by this merge.

## Stage 7 owner handoff — still pending

1. Obtain a fresh prospective capture and successful Stage 6 materialization.
2. Owner manually dispatches **VELTRIX Stage 7 research shadow inference (manual only)** on `main`, explicitly setting `confirm_research_ledger_write=true`; this is a database write and remains owner-controlled.
3. Review the sanitized run summary, monitor status, and five sample forecasts. If no fresh upcoming snapshots exist within the six-hour guard, the runner must fail closed without persistence.
4. Only after review may the owner separately enable `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true`, redeploy, and verify API/app read-back.
5. Keep production prediction publication and value betting locked. Do not activate the disabled scheduled shadow workflow.
6. Within three days after any research display, run the separately owner-dispatched sanitized retained-vs-abstained development-fold diagnostic (fold, retained flag, probabilities, outcome only; no fixture/team names).

## Capture scheduler delay — evidence-based conclusion

- Capture workflow observed on the prior schedule: `.github/workflows/prospective-5dollar-daily-capture.yml`, cron `0 3 * * *` (03:00 UTC / 04:00 WAT).
- Observed runs: [44514389412](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44514389412) (Nov 19), [44725750217](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44725750217) (Nov 20), and [44896202232](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44896202232) (Nov 21).
- Run creation occurred substantially later than the scheduled time (approximately 11:23, 11:12 and 10:50 UTC respectively); job start followed run creation by seconds.
- The observed delay is before GitHub Actions run creation, not a runner queue or environment approval delay. Environment approval/queueing was ruled out by the run timestamps and job-start evidence.
- Mechanism is scheduler-side delay; its internal cause is undocumented and not controllable from this repository. A cron minute shift may be tested as a mitigation but must not be described as a confirmed fix.
- PR #146 proposes moving the cron to 03:17 UTC and adding run-created/start plus capture-to-Stage-6 timing summaries. It is still a draft and has no exact-head CI run reported at this checkpoint.

## PR #146 current state and sequencing constraint

- PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/146
- Head: `ac7f203d79d07befbf0dc7f5c06b2f720c8cb720`; base recorded as `da86cef52d51a7b8924ad837fe91208a30f562c5`, which predates PR #145 merge.
- PR is open, draft, and GitHub reports `mergeable=false`. No pull-request-triggered workflow run was returned for its exact head by the available commit-workflow-run query.
- Do not mark ready or merge until the base is reconciled with current `main`, exact-head CI is green, and the workflow changes are reviewed. In particular, validate the new `actions: read` permissions and shell/step-summary behavior.
- PR #147 dispatcher remains deferred until PR #146 is resolved. The dispatcher design removes the capture workflow's own cron and relies on dispatch slots; implementing it concurrently with #146 would create competing edits to the same capture workflow and obscure which schedule is active.

## Actions performed in this checkpoint

- Read-only verification of PR #145, exact-head CI jobs, merge commit, and latest default-branch commit listing.
- Read-only inspection of PR #146 diff, branch head, base SHA and comments.
- Added this dated ledger entry only. No production data, credentials, provider balances, workflows, schedules, model flags or deployment settings were changed.
