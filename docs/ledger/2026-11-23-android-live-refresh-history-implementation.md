# 2026-11-23 — Android live refresh and history implementation

## Scope

Implemented against the existing Compose application and preserved its screen/navigation structure. PR #162 builds on the kickoff-visibility changes from PR #159.

## Changes

- Added lifecycle-aware automatic refresh of published, research and history feeds every five minutes while the activity is in the STARTED lifecycle state.
- The refresh coroutine suspends when the app leaves STARTED; the existing manual Refresh action remains.
- Added a client-side "Last checked" timestamp. This records the device's last fetch attempt and is not represented as server data freshness.
- Added settled 1X2 history scoring using the highest-probability outcome from the immutable stored probabilities and final score.
- Tied maximum 1X2 probabilities are not assigned an arbitrary pick; pending entries or entries without scores are excluded from performance totals.
- Added won/lost summary counts only when at least one settled 1X2 result can be scored.
- Sorted history newest-first and grouped entries by Africa/Lagos calendar date.
- Added unit tests for 1X2 outcome selection, tied probabilities, correct/incorrect settled outcomes and pending/missing-score exclusion.
- Added lifecycle-runtime-compose dependency.
- PR #159 hides 1X2, BTTS and Over/Under probabilities at/after kickoff, including invalid kickoff timestamps, while retaining match identity and kickoff metadata.

## Merge and verification evidence

- PR #159 merged: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/159
  - Merge commit: `72bed26ea370a7fc53d798d834c4a889dea54aaf`
  - Exact-head CI run `45265851313`: completed SUCCESS.
- PR #162 merged: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/162
  - Merge commit: `0b44169417b511b9bf08928cc128019322b314d2`
  - Exact-head CI run `45268476965`: completed SUCCESS.
  - Merged after PR #159 using a merge commit to preserve dependency ancestry.
- Post-merge combined status read-back for merge commit `0b44169417b511b9bf08928cc128019322b314d2` showed Vercel PENDING at time of check; no post-merge GitHub Actions run was returned by the PR-only workflow-run lookup.
- Physical-device verification has NOT been performed. The owner explicitly authorized merging despite this outstanding manual test. Treat device validation as a release blocker; do not claim the app has been tested on hardware.
- No production API, database, provider, Odds API, production forecast, research/production gate, certification, value-betting lock or scheduled pipeline was changed by these Android merges.

## Remaining work

1. Install/update-compatible APK and verify on the target Android device: future fixtures show probabilities; exact/past kickoff and invalid kickoff hide all probabilities while retaining metadata.
2. Verify five-minute foreground refresh, suspension/resumption after backgrounding, manual refresh, history grouping and settled 1X2 totals.
3. Continue implementing remaining existing-app surfaces against verified backend contracts. Do not fabricate dashboard performance, operational status, market certification, AI explanations or value-bet selections.
4. PR #160 (WAT calendar-day backend feed bounds) remains separate and unmerged; do not assume it was included in these two merges.
