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


## Follow-up verification — 2026-11-21 08:00 WAT
- PR #130 merged successfully by squash merge as commit `bf6986d03d3687f36dbd7e84de7adb148e93c64d`.
- Required CI run #44882438326 completed successfully. Both jobs passed: backend tests and lint; Android debug APK build and artifact upload.
- Vercel production deployment was created for the merge commit and was still in `BUILDING` state at the last read-back. Do not claim production deployment ready until a subsequent deployment status check confirms it.
- Existing automatic daily chain verified in repository workflow definitions:
  - `prospective-5dollar-daily-capture.yml` runs daily at 03:00 UTC (04:00 WAT), capturing yesterday's settlements plus a rolling seven-day forward fixture window. It is limited to four provider requests per run.
  - Successful capture triggers Stage 6 daily snapshot/outcome materialization.
  - Successful Stage 6 completion triggers `prospective-shadow-predictions.yml`; that workflow also has a daily 05:00 UTC (06:00 WAT) schedule and manual dispatch. It generates up to 25 research forecasts and persists them only to the isolated research ledger.
  - Stage 7 evaluation follows Stage 6; certification gates remain closed unless independent criteria are actually met.
- This means tomorrow's upcoming fixtures are intended to be included automatically: the seven-day capture window covers them, then the daily shadow run refreshes the next forecast set. The 36-hour API freshness change prevents the newly generated report from expiring after six hours.
- The inference workflow's max snapshot age remains six hours; this is an input-quality guard, not the API response expiry. Do not widen it without evidence that it blocks valid snapshots.
- The inference workflow can be triggered both by Stage 6 completion and its daily cron. Its concurrency group prevents overlap but does not necessarily eliminate sequential duplicate runs; inspect tomorrow's run history for this behavior before changing it.
- Verification still outstanding: production deployment readiness; live unauthenticated production endpoint response; Android screen display after app restart. No provider/Odds API credits were spent by this repair.
- Safety unchanged: research forecasts remain unpublished; production promotion and value betting remain LOCKED.

- Final production deployment read-back: deployment `dpl_AAya7HfvdnabnZfZnwPpHtRFALsn` reached `READY` on production alias `veltrix-ai-analyst-api.vercel.app`, commit `bf6986d03d3687f36dbd7e84de7adb148e93c64d`.
- Attempted direct external GET of `/v1/research/predictions`; the available page-fetch path returned an internal access error. Vercel runtime logs for the deployment showed no requests in the 30-minute window. Therefore HTTP status/payload and physical Android rendering remain unverified; deployment readiness alone does not prove either.
