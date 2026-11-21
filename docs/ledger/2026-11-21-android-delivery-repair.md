# 2026-11-21 — Android research forecast delivery repair

## Findings
- The installed Android client is configured to call `https://veltrix-ai-analyst-api.vercel.app/v1/research/predictions`.
- Vercel project `veltrix-ai-analyst-api` had SSO protection set to `all_except_custom_domains`. Its only attached domain is the Vercel-managed `veltrix-ai-analyst-api.vercel.app`, not a custom domain; therefore the installed app's API host was inside the protected scope.
- Vercel project SSO protection was changed to `preview`. Read-back verified `ssoProtection.enabled=true`, `deploymentType=preview`; Production API host is intended to be publicly reachable while Preview deployments remain protected.
- The research endpoint SQL also expired reports after six hours. Daily capture/inference is generated around 06:00 WAT, so that cutoff could hide still-upcoming fixtures later on matchday. This is independent of the SSO access problem.

## Code repair
- PR #130: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/130
- Branch: `fix/android-research-prediction-delivery`
- Changes: increase research report maximum age from 6 to 36 hours; preserve upcoming-kickoff, research-only, NOT_PUBLISHED, production-promotion LOCKED and value-betting LOCKED predicates; add regression test for the 36-hour window.
- No model, capture, provider, Odds API, production publication, settlement or certification logic changed.
- Existing Android APK already points to the production API hostname; the SSO configuration repair does not require an APK rebuild by itself.

## Verification boundary
- Vercel project setting update succeeded and was read back.
- The latest production deployment remained READY on main commit `de34c8c05d563f465e8784a5c7a5050d6b016c53`.
- The direct API response could not be independently fetched through the available external page fetch; Vercel runtime logs showed no API requests in the 15-minute observation window. Do not claim endpoint response or physical app display verified.
- PR #130 is open. Vercel preview deployment was reported READY; GitHub Actions CI had not yet reported a completed run at this checkpoint.
- The production API currently still runs the six-hour SQL guard until PR #130 is merged and deployed. Therefore the access-protection repair is applied, while the full-day freshness repair awaits CI/merge/deployment.

## Next steps
1. Wait for and verify backend tests/lint and Android debug build on PR #130.
2. Merge only after required checks pass; confirm production deployment READY on the merge commit.
3. Verify live `GET /v1/research/predictions` HTTP response and payload count.
4. Have the user force-close/reopen the installed app and refresh; no APK replacement should be needed for the project-level SSO change or backend SQL-only change.
5. If the app still shows no forecasts, capture Android Logcat entries for tag `VeltrixPredictions` and correlate request paths/status with Vercel runtime logs.
6. Keep all research forecasts unpublished; production promotion, certification and value betting remain locked.
