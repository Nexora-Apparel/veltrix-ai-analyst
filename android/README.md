# Android application

Native Android client built with Kotlin and Jetpack Compose.

## V1 screens

- Home: published 1X2 probabilities for upcoming fixtures.
- BTTS: Yes and No probabilities.
- Over/Under: Over and Under probabilities for 1.5, 2.5, and 3.5 goals.
- History: settled-prediction empty state until a real results service is available.
- Value Bets: explicitly locked until independent validation is complete.
- Menu: basic app preferences.

The client reads the typed `GET /v1/predictions` contract. A valid empty response is shown as “No upcoming predictions”; API/network failures are shown separately as temporarily unavailable. No sample fixtures or fabricated metrics are bundled.

## Build

Requires JDK 17, Android SDK platform 35, and Gradle 8.9 or compatible.

```bash
cd android
VELTRIX_API_BASE_URL=https://veltrix-ai-analyst-api.vercel.app gradle :app:assembleDebug
```

The Gradle property `VELTRIX_API_BASE_URL` can also be supplied through `-PVELTRIX_API_BASE_URL=...`. The CI debug build is configured to use the production API base URL.

A successful CI build verifies compilation only. Live prediction display still requires eligible published predictions, and physical-device verification remains a separate release check.
