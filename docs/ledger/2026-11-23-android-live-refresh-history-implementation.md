# 2026-11-23 — Android live refresh and history implementation

## Scope

Implemented against the existing Compose application and preserved the existing screen/navigation structure. This is an incremental implementation branch based on PR #159 head `2b3852b60bb28b5f43b07d446efba219f7749bd2`; it must not merge ahead of that kickoff-visibility dependency.

## Changes

- Added lifecycle-aware automatic refresh of published, research and history feeds every five minutes while the activity is in the STARTED lifecycle state.
- The refresh coroutine suspends when the app leaves STARTED; the existing manual Refresh action remains.
- Added a client-side "Last checked" timestamp. This records the device's last fetch attempt and is not represented as server data freshness.
- Added settled 1X2 history scoring using the highest-probability outcome from the immutable stored probabilities and verified final score.
- Tied maximum 1X2 probabilities are not assigned an arbitrary pick; pending entries or entries without scores are excluded from performance totals.
- Added won/lost summary counts only when at least one settled 1X2 result can be scored.
- Sorted history newest-first and grouped entries by Africa/Lagos calendar date.
- Added unit tests for 1X2 outcome selection, tied probabilities, correct/incorrect settled outcomes and pending/missing-score exclusion.
- Added lifecycle-runtime-compose dependency.

## Evidence

- Branch: `feat/android-live-refresh-integration`
- PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/162
- Current head at ledger creation: `1e36d19ae9c1c056387dd958cdc044fdc03583fb`
- Branch comparison against main: 9 commits ahead, 0 behind; five changed files.
- GitHub combined status read-back at head showed Vercel pending; no associated PR workflow runs were returned at the time of inspection. Android CI is therefore NOT YET VERIFIED.
- No physical-device test has been performed.
- No backend API, database, provider, Odds API, production forecast, research/production gate, deployment or value-betting state was changed by these Android changes.

## Blockers and next steps

1. Obtain exact-head Android CI result and inspect any failed job logs.
2. Verify app behaviour on a physical Android device, including foreground refresh cadence, background suspension/resumption, history scoring and WAT grouping.
3. Keep PR #162 unmerged until PR #159's kickoff behaviour is physically verified and the dependency is safe to integrate.
4. Continue implementing the remaining existing-app surfaces against verified backend contracts; do not fabricate dashboard performance, operational status, market certification, AI explanations or value-bet selections.
