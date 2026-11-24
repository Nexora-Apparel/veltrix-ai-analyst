# 2026-11-24 — Scheduled capture trigger investigation and mitigation

## Verified state

- Repository: `Nexora-Apparel/veltrix-ai-analyst`
- Default branch: `main`; repository is public, not archived, and not disabled.
- Capture workflow remains present on `main` with cron `0 0 * * *` (00:00 UTC / 01:00 WAT).
- Actions schedule-event listing contains no 24 November capture. Latest scheduled capture remains run `45171104634`, created 23 November at 12:06:06 UTC.
- At 04:02 UTC / 05:02 WAT, the 24 November run was already absent; it remained absent in the 06:21 WAT check.
- The repository has other recent scheduled workflow runs, so scheduled Actions are not globally absent from this repository.
- The capture workflow's previous observed scheduled execution was substantially late relative to its then-active cron. The current top-of-hour cron has not produced a run on 24 November.

## Assessment

GitHub documents that scheduled workflow events may be delayed or dropped during high-load periods, with top-of-hour schedules particularly exposed to contention. The current `0 0 * * *` cron is exactly at the start of an hour. This is a plausible contributing cause, not a proven diagnosis. Workflow-specific enablement state could not be read through the available read-only GitHub endpoint surface; do not state it has been independently verified.

## Mitigation proposed

PR #169 changes the cron to `17 0 * * *` (00:17 UTC / 01:17 WAT) and updates the workflow summary text. The change is deliberately narrow. It does not alter the rolling capture window, request budget, PIT checks, import behavior, Stage 6/Stage 7 triggers, six-hour freshness gate, or production locks.

## Safety and outstanding verification

- No manual dispatch or rerun was performed.
- No 5Dollar Football API or Odds API request was made for this investigation.
- No production database write, deployment, model promotion, publication, or Value Bet unlock occurred.
- PR #169 must pass CI and be reviewed/merged before the new cron becomes active on `main`.
- After merge, verify the next natural scheduled capture, fresh import IDs/observations, its exact Stage 6 child, and Stage 7 inference outcome. A green workflow conclusion alone is not evidence that forecasts were produced.
- Keep production publication, promotion, and Value Bet locked until independent certification criteria are met.

## User-confirmed delivery-window correction (24 November 2026)

- The required user-facing prediction availability window is **07:00–09:00 WAT**, not 07:00–10:00 WAT.
- The capture workflow's previous summary text incorrectly stated 07:00–10:00 WAT. PR #169 now changes that line to 07:00–09:00 WAT while retaining the proposed 00:17 UTC / 01:17 WAT capture cron.
- This is a target window, not yet a proven delivery SLA. Stage 6 and Stage 7 are chained automatically after successful capture, but Stage 7 currently selects only snapshots no older than six hours and can correctly emit zero forecasts when data is stale or ineligible.
- No dedicated 07:00–09:00 publication/notification job was verified in the inspected workflow files. Android refreshes its API feed while the app is in foreground; this does not by itself prove forecasts will exist by 07:00.
- Required follow-up: validate natural capture timing and actual Stage 7 forecast counts, then add/verify a bounded pre-window readiness check and user-facing publication path without bypassing PIT, freshness, or certification gates.
- CI on the previous PR head `770ba1ec35f483b23b53ce882b6b56f9b16119fe` had passed, but the timing correction creates a new head and must receive its own CI result before merge.
