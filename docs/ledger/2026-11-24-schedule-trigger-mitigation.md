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
