# 2026-11-23 — Post-merge capture and Stage 6/7 workflow audit

## Repository state inspected
- Repository: `Nexora-Apparel/veltrix-ai-analyst`.
- Branch inspected: `main`.
- Current main head at audit time: `4fbdbc9bab83cf04f2d4a423ee83de7388c3ca8e`.
- The latest commit is the documentation merge recording PRs #146, #150, and #151; the implementation commits are `eafc30fca814ddf41e3ffd1fc115406210699fff` (capture timing) and `2158a0a4b7ae5eff77f67a04ff170b7e4bfe6234` (Stage 7 automation).

## Workflow definition audit
- Capture workflow: `.github/workflows/prospective-5dollar-daily-capture.yml`.
  - Main schedule is `17 3 * * *` = 03:17 UTC / 04:17 WAT.
  - Capture uses the existing 5Dollar Football provider secret.
  - The bounded capture command uses request budget 4.
  - The workflow records event name, cron, run-created timestamp, runner-start timestamp, capture outcome, and run ID in the Actions summary.
- Stage 6 workflow: `.github/workflows/stage-6-daily-snapshot-materialization.yml`.
  - Subscribes to completion of the named capture workflow.
  - A workflow_run-triggered materialization proceeds only when the capture conclusion is success.
  - It verifies immutable snapshot persistence, distinct fixture identity, append-only protections, and exact latest label events.
  - It explicitly requires release eligibility false, production promotion LOCKED, and value betting LOCKED.
  - It records capture and Stage 6 creation/start times, capture conclusion, verification outcome, and run IDs.
- Stage 7 workflow: `.github/workflows/research-shadow-inference.yml`.
  - Subscribes to completion of the named Stage 6 workflow.
  - Automatic inference requires Stage 6 workflow ID `423623285`, upstream event `workflow_run`, main branch, and successful conclusion.
  - The manual path remains gated by `confirm_research_ledger_write=true`.
  - The inference remains capped at 25 fixtures and a six-hour snapshot age; persistence targets the isolated research ledger and uploads a sanitized summary.

## Findings and risk controls
- Static workflow definitions are consistent with the intended capture → Stage 6 → Stage 7 sequence.
- Stage 7's additional upstream-event condition intentionally prevents a Stage 6 run caused by a direct push from triggering automatic inference.
- No workflow was manually dispatched or rerun during this audit.
- The first scheduled capture using the merged 03:17 UTC cron is still the required runtime test. At this audit point, the expected 24 Nov 2026 run is future-dated; no post-merge runtime success or punctuality is claimed.
- No production deployment, production prediction publication, release-gate change, value-betting unlock, Odds API request, or provider-budget consumption was initiated.

## Next verification
1. Inspect the first scheduled capture after the cron merge; record run-created and runner-start timestamps and calculate actual delay from 03:17 UTC.
2. Verify successful capture conclusion and Stage 6 workflow_run parent/run IDs, event lineage, jobs, artifact, snapshot counts, and closed gates.
3. Verify Stage 7 was automatically triggered by that exact Stage 6 run, not by a manual dispatch or historical run.
4. Inspect Stage 7 job outcome, sanitized artifact, and isolated research-ledger run key; check idempotency and ensure production publication/value betting remain locked.
5. Update the dated ledger with observed runtime evidence. Do not infer punctuality from static YAML or CI success.
