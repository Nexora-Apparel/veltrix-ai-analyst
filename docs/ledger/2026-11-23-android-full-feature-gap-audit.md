# 2026-11-23 — Android full-feature gap audit

## Current verified implementation

The Android application module currently contains three main Kotlin files:
- `MainActivity.kt`
- `PredictionApi.kt`
- `VeltrixDashboard.kt`

The app ID and namespace are both `com.veltrix.aianalyst`; current Gradle metadata is versionCode 1 / versionName 0.1.0. The app uses Compose and currently has these bottom tabs:
- Home
- History
- BTTS
- Value Bet
- Over/Under
- Menu

The API client currently requests:
- `GET /v1/predictions`
- `GET /v1/research/predictions`
- `GET /v1/predictions/history`

It fetches those feeds on initial composition and when the user taps Refresh. No periodic/background automatic refresh is currently implemented in the dashboard.

History displays published prediction entries, settlement status and final score when present. It is a read-only view. Value Bet is currently a locked placeholder screen.

## Gaps against the intended product

The current app is a partial shell, not the complete VELTRIX AI ANALYST product. The existing screen layout must be preserved, but the following product work remains:

1. **Dashboard**
   - Real daily fixture counts and feed freshness/last-updated information.
   - Clear separation of published versus research-only records.
   - Fixture cards with competition/team identity and available logos.
   - Useful AI analysis/explanation, confidence and verdict fields only when supplied by an approved backend contract.
2. **Prediction**
   - A dedicated prediction browsing surface with fixture selection/details.
   - 1X2, BTTS and O/U 1.5/2.5/3.5 market presentation.
   - Market-level certification/availability states; uncertified markets must remain restricted.
   - Research-only predictions must remain clearly labelled and must never be represented as published.
3. **Automatic updates**
   - Safe periodic refresh while the app is active, pull-to-refresh/manual retry, loading/error/stale states.
   - No fabricated freshness timestamps; use server-provided metadata.
4. **History and settlement**
   - Group and sort records by date.
   - Separate wins/losses/pending/void where the backend provides settled market outcomes.
   - Display actual scores and market-specific result/settlement details.
   - Preserve immutable prediction-at-publication values; never rewrite past forecasts.
5. **Status**
   - Dedicated operational status view covering API/data freshness, research run state, production publication state, and market certification/locks.
   - Status must come from a supported backend endpoint/schema, not hardcoded UI claims.
6. **Market**
   - Dedicated market/certification view with available markets, evidence status and lock reasons.
   - Value betting remains locked until its separate certification requirements are met.
7. **Settings and reliability**
   - Functional preferences only (for example time zone/odds display where supported), app/build information, retry and diagnostics.
   - Proper offline, timeout, empty-feed and API error handling.
8. **Design and QA**
   - Preserve the existing visual design and navigation direction; no unsolicited redesign.
   - Add parser, state, market-gate, date-boundary and UI tests.
   - Validate on a physical Android device before release.

## Release and model constraints

- This is an Android-only product; Telegram delivery is out of scope.
- Research forecasts stay isolated from production predictions.
- Uncertified markets remain restricted.
- No model promotion, production publication or value-betting unlock without the relevant evidence and explicit release authorization.
- The app must consume approved backend output; capture/model processing remains server-side.

## Installation / update compatibility

- The current applicationId is `com.veltrix.aianalyst`.
- Android can install an APK over an existing installation only when the package ID and signing certificate match and the version code is acceptable.
- CI currently assembles a debug APK. GitHub Actions debug signing keys are ephemeral unless explicitly persisted; therefore an APK from a different CI run may not be signature-compatible with an already-installed debug APK.
- Do not tell the user to uninstall the current app until the installed APK's signing certificate is known and an update-compatible APK is prepared. Uninstalling may erase local app data; current manifest sets `allowBackup=false`.
- Before distributing an update, increment versionCode and establish a consistent signing strategy. Do not commit signing secrets to the repository.

## Verification evidence as of this audit

- PR #159 Android kickoff guard: exact-head CI run `45265851313` passed Android debug build and backend tests/lint. Physical-device test has not been performed; PR remains unmerged.
- PR #160 WAT feed backend: exact-head CI run `45265970048` passed backend tests/lint and Android debug build. PR remains draft and unmerged, pending safe integration with PR #159.
- PR #154 capture schedule change is merged; `main` runs capture at 01:00 WAT.
- No successful scheduled fresh capture / Stage 7 research forecast run is asserted by this feature audit.

## Next implementation order

1. Complete physical-device validation of PR #159; merge only after the guard behaves correctly.
2. Merge PR #160 after the Android/backend daily-feed contract is integrated.
3. Implement the missing app features in vertical slices: dashboard freshness/insight data contract, full prediction browsing and certified market gates, automatic refresh, full history/settlement, Status, Market, settings/reliability.
4. Extend backend API contracts only where required; keep model inference and capture on the backend.
5. Run end-to-end tests against the same report and verify app behaviour without exposing research forecasts as production.
