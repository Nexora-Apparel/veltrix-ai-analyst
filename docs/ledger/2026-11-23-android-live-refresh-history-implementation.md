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
- PR #164 merged: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/164
  - Merge commit: `37f18612d72beb800a55a465ef23c0b61c564afd`
  - Added deterministic WAT history date-boundary tests for UTC-to-WAT midnight conversion and invalid timestamps.
  - Initial compile failure was corrected in commit `d6b007305e52c299370384286a23557b8e3041bf`.
  - Exact-head CI run `45269810785`: Backend tests/lint SUCCESS; Android debug build SUCCESS; APK upload step SUCCESS.
  - PR head was three commits ahead of main and zero behind before merge.
- PR #160 remains unmerged. Exact-head run `45269479785`: backend tests/lint SUCCESS, Android debug build FAILURE, APK upload skipped. Do not treat the PR as release-ready; inspect the Android build failure before any merge.
- Physical-device verification has NOT been performed. Treat device validation as a release blocker; do not claim the app has been tested on hardware.
- No production API, database, provider, Odds API, production forecast, research/production gate, certification, value-betting lock or scheduled pipeline was changed by these Android merges.

## Remaining work

1. Obtain a fresh APK built from the integrated main branch after PR #164, verify artifact provenance, package/version, signing certificate and SHA-256.
2. Establish update compatibility without uninstalling the user's existing app; if the installed signing certificate cannot be established, treat update installation as a manual blocker and preserve the current installation.
3. Verify on the target Android device: future fixtures show probabilities; exact/past kickoff and invalid kickoff hide all probabilities while retaining metadata.
4. Verify five-minute foreground refresh, suspension/resumption after backgrounding, manual refresh, history grouping and settled 1X2 totals.
5. Continue implementing remaining existing-app surfaces against verified backend contracts. Do not fabricate dashboard performance, operational status, market certification, AI explanations or value-bet selections.
6. PR #160 (WAT calendar-day backend feed bounds) remains separate and unmerged; its Android build failure must be diagnosed independently.


## Side-by-side QA install — PR #166

- PR #166: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/166 — merged.
- Merge commit: `53eb45bd47a3b41712a9846f6f5ebb55f388c1a3`.
- Exact-head CI run `45271840825` for `d353f80640142bd03bffcd3212230d12a153ce03`: Android debug build SUCCESS; backend tests/lint SUCCESS; APK upload SUCCESS.
- The debug build uses application ID `com.veltrix.aianalyst.test` and version suffix `-test`; release application ID remains `com.veltrix.aianalyst`. This permits side-by-side QA installation and avoids replacing the existing app or relying on the old debug signing key.
- CI log confirms `VELTRIX_API_BASE_URL=https://veltrix-ai-analyst-api.vercel.app` was supplied to Gradle.
- APK artifact ID `14866310869`, name `veltrix-ai-analyst-debug-apk`, run `45271840825`, SHA-256 of uploaded artifact ZIP `6741bcdf7d31e0aad92019a47b402d465ac34ddc6bbf1a7379e617c4ea8d3e2a`, expires 2026-11-30 21:40:18 UTC.
- Artifact was built from the exact PR head immediately before merge; it includes the same source changes as merge commit, but is not a post-merge main-branch build. Do not describe it as a main-branch artifact.
- Device install, launch, live API connectivity, rendering and functional checks remain unverified until performed on the user's Realme 5 Pro.
