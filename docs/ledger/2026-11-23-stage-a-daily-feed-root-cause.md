# 2026-11-23 — Stage A daily-feed root-cause investigation

## Scope

Read-only investigation of the Android research/published prediction feeds, history endpoint, research API query, and existing daily workflow. The owner requirement is: show all fixtures whose kickoff date is today in Nigeria/WAT; retain them in the daily feed after kickoff and full-time; exclude tomorrow; preserve older fixtures in history.

## Repository state inspected

- Repository: `Nexora-Apparel/veltrix-ai-analyst`
- Default branch: `main`
- Inspected main commit: `508e60b57c89d0d23ef2dfdc17a222d11b81718c`
- Existing open PR #146 is capture timing diagnostics; it does not implement the daily WAT feed contract.
- The 2026-11-22 research-display ledger was read before investigation.

## Verified root causes

### 1. Backend research endpoint removes matches at kickoff

File: `backend/app/routes/research_predictions.py`

The research SQL query contains:

- `fixture.kickoff_at > %s`, with the parameter supplied as `datetime.now(UTC)`.
- A latest-run age restriction of 36 hours.
- A 25-row maximum.

Therefore, a research fixture disappears from the API as soon as its kickoff timestamp is reached, even though it belongs to today's WAT calendar date and should remain visible through full-time. This is a confirmed mismatch with the owner's daily-feed requirement.

### 2. Published daily endpoint has the same upcoming-only behavior

File: `backend/app/routes/public_predictions.py`

`_load_public_predictions()` filters with `fixture.kickoff_at > datetime.now(UTC)`. This also removes today's started/completed fixtures from the daily prediction endpoint.

### 3. Android does not apply a WAT day window

Files:
- `android/app/src/main/java/com/veltrix/aianalyst/PredictionApi.kt`
- `android/app/src/main/java/com/veltrix/aianalyst/VeltrixDashboard.kt`

The app fetches the published feed, research feed, and published history. Home, BTTS, and Over/Under merge published and research lists. There is no local kickoff-date filter. Kickoff formatting uses `ZoneId.systemDefault()`, which is not an authoritative Nigeria/WAT date boundary.

Home's section is labelled “Upcoming predictions”. Research-only marking is visible on Home. BTTS and Over/Under do not currently show the same explicit per-card research-only pill.

### 4. History is published-only

The Android history screen consumes `/v1/predictions/history`. The backend history query is built from the published `predictions` table and requires a prior publication event. It does not include isolated research-shadow forecasts.

Research forecast snapshots therefore need a separate research history/settlement path. They must not be inserted into or counted as certified published performance.

### 5. Daily automation does not currently generate the app's research forecast each day

The Stage 6 daily workflow materializes prospective feature snapshots and outcome labels after capture. The Stage 7 research shadow inference workflow is `workflow_dispatch` only and requires explicit confirmation before writing the isolated research ledger. No automatic daily Stage 7 inference schedule is defined in that workflow.

Do not change schedules or trigger inference as part of this investigation.

## 21-to-5 discrepancy qualification

The code confirms that started fixtures are removed upstream by the `kickoff_at > now` predicate. This is a plausible direct explanation for a shrinking count as matchday progresses. However, the exact identity/status of the 16 fixtures not visible on the user's device was not independently enumerated in this read-only pass. Do not claim all 16 had already kicked off without a timestamp-level comparison against the exact API response and device refresh time.

## Required implementation contract

1. Use one authoritative timezone: `Africa/Lagos` (WAT, UTC+1).
2. Define today's interval as local midnight inclusive to next local midnight exclusive, converted to UTC for SQL comparisons. The equivalent UTC interval is 23:00 UTC on the previous date through 23:00 UTC on the current date.
3. Filter by fixture kickoff timestamp in that interval, not by whether kickoff is still in the future.
4. Include all match states for fixtures in today's kickoff-date interval, including live and completed fixtures.
5. Exclude tomorrow's kickoff-date fixtures from today's daily feed, even if forecasts already exist.
6. Keep older fixtures and immutable forecast snapshots available through history.
7. Build separate research history and settlement support; retain the original research forecast and attach only verified final results.
8. Keep research records visibly marked RESEARCH ONLY and isolated from published/certified performance and value betting.
9. Preserve the existing Android screen design; change data filtering, status labels, and feed semantics only where required.

## Verification still required in implementation stage

- Unit tests at both WAT day boundaries, including UTC date rollover.
- Fixtures immediately before/at/after WAT midnight.
- Today's not-started, live, and completed fixtures all retained.
- Tomorrow excluded; yesterday retained only in history.
- Published and research feeds deduplicated by canonical fixture identity without cross-tier promotion.
- Research history does not affect published performance.
- Android debug build and API contract tests.
- Live endpoint/device comparison to account for the exact 21-to-5 discrepancy.

## Safety and changes

- Read-only repository inspection only.
- No source files changed.
- No PR created or merged.
- No production deployment, environment change, DB write, inference run, schedule change, or provider/Odds API call.
- Production publication and value betting remain locked.

## Next stage

Stage B: implement the backend WAT day-window contract and research/published feed semantics with focused tests, then integrate Android current-day filtering and a distinct research history path. Keep the change on a reviewed branch/PR; do not deploy to production without explicit authorization.
