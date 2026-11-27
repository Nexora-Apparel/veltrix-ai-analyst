# 2026-11-27 — WAT daily slate release verification

## Verified merges
- PR #179 (WAT daily-slate correction) merged to `main` at `9837395b28b238700b6ab10c817ea2424ed74245`.
- PR #180 (manual read-only candidate validation workflow) merged to `main` at `66940e70b9c96b8dd03886f23e9057c1c1e134eb`.
- PR #181 (validator checkout working-directory fix) merged to `main` at `325c2cd29e303ff9a019ee1b3ec8d8b34372f9a3`.
- PR #181 head was `ded14bd3cd0f893ce1c0b484f84e5b3c83de1ce1`. The change removes job-level `working-directory: backend` and scopes it to the backend install and validator steps, so SHA validation and checkout execute from the repository root.
- PR #181 was mergeable and GitHub confirmed successful squash merge. No PR-triggered workflow runs were returned for its head commit; do not represent that as a passing CI check.
- The WAT correction and read-only validator workflow are now present on `main`.

## Prior post-merge CI — PASS
- GitHub Actions run [#45975833233](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45975833233) ran against merge commit `9837395b28b238700b6ab10c817ea2424ed74245`.
- Backend tests and lint job: completed successfully. Steps included actionlint, Python compilation, pytest, and Ruff.
- Android debug build job: completed successfully; APK assembled and uploaded.
- Artifact `veltrix-ai-analyst-debug-apk`, artifact ID `15187725268`, SHA-256 `806cca8b62e327e48ba7b814dc21290be27e75b3512c26ea49ad49f0cc832b9c`; expires 2026-12-04.
- Both jobs completed with conclusion `success`.

## Production deployment — READY (prior WAT correction commit)
- Vercel deployment `dpl_FzbGexPsmeadqRUWA1iAhYo2i1z6` for project `veltrix-ai-analyst-api` is `READY`, target `production`.
- Deployment metadata confirms exact Git commit `9837395b28b238700b6ab10c817ea2424ed74245` on `main`.
- Deployment URL: https://veltrix-ai-analyst-9608qma7g-nexora-apparel.vercel.app
- This verifies deployment readiness and commit identity, not the live API's fixture-date response or Android runtime rendering.

## Read-only validator dispatch — PASS
- Initial manual dispatch run [#45977944979](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45977944979) failed before checkout. Its SHA input was valid: `7fffc7fc05743f3b7fe70c4c7d2505eb7bbe40a8`.
- Root cause from job logs: job-level `defaults.run.working-directory: backend` caused the first shell step to start in a directory that did not exist before checkout.
- PR #181 corrected this workflow configuration and is merged as `325c2cd29e303ff9a019ee1b3ec8d8b34372f9a3`.
- Post-fix manual dispatch [#45978626314](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45978626314), job `140436590689`, completed successfully. Exact candidate SHA `7fffc7fc05743f3b7fe70c4c7d2505eb7bbe40a8` validated and checked out; all validator steps and artifact upload succeeded.
- Artifact `veltrix-wat-daily-slate-readonly-validation`, ID `15188397754`, size 1,211 bytes, SHA-256 `3085398969fa58e90ac10504fb18aa6a27bcb7862451033c0d42b002e1d63464`; expires 2026-12-27.
- Downloaded and inspected JSON manifest: `status=PASS`; WAT date `2026-11-27`; four selected fixtures and four forecasts; cap 25; max snapshot age 6 hours. All four kickoff timestamps fall within the WAT UTC window `2026-11-26T23:00:00Z` through exclusive `2026-11-27T23:00:00Z`.
- Manifest checks passed for current WAT day only, no tomorrow fill, date filtering before cap, chronological ordering, unique fixture IDs, selector/inference count agreement, and read-only DB transaction. It records provider calls 0, DB writes 0, research-ledger writes 0, odds unused, publication `NOT_PUBLISHED`, production promotion `LOCKED`, and Value Betting `LOCKED`.
- `checks.empty_slate_allowed` is `false` in this run because four eligible fixtures existed; it is a condition (`selected_count == 0`), not a failure. Source inspection confirms `_select_daily_targets` returns an empty list when no rows qualify and `build_stage7_shadow_predictions` returns a zero-forecast `NO_FRESH_UPCOMING_SNAPSHOTS` report when targets are empty. This run did not exercise the zero-fixture path, so empty-slate behavior remains unverified by runtime test.

## New coverage diagnostic — PR #182 OPEN
- PR [#182](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/182), branch `diagnostics/wat-slate-rejection-reasons-20261127`, adds mutually exclusive first-failure counts for the daily-slate selector predicates. It reports total candidate rows, each rejection category, and eligible rows before the 25-fixture cap; it does not relax eligibility rules.
- Added unit tests cover all rejection categories and verify counts are exhaustive and mutually exclusive. PR head at this checkpoint: `78c717df9ed1c612395abda649c9a5fb27791f56`; PR is draft/open. First CI attempt (run `46000312460`) had Android debug build success but backend tests failed in the new rejection-diagnostics test. Root cause: fixtures did not respect predicate ordering (`cutoff_in_future` is checked before `cutoff_not_before_kickoff`) and the outside-WAT fixture was inside the UTC WAT window. Corrected fixtures and expected count in commits `107c18bb1e54e7a1dd0855ed73571c3400a3b64c` and `78c717df9ed1c612395abda649c9a5fb27791f56`; the corrected head triggered PR CI run `46001949257` (run number 1387). The subsequent CI run [#46002052460](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/46002052460) completed: Android debug build PASS; backend job FAILED with 593 passed / 1 failed. The sole failure was this test's fixture ordering: the intended `cutoff_not_before_kickoff` row had kickoff before the generated time but a cutoff earlier than kickoff, so the earlier `kickoff_not_upcoming` predicate correctly won. Corrected the fixture to cutoff 09:59 UTC and kickoff 09:58 UTC for a 10:00 UTC generation time, making the cutoff-not-before-kickoff reason the first failing predicate. This correction is committed after run #46002052460; fresh CI is required. Vercel preview deployment `dpl_CMag3VzGxixYTWqvLNmQMhL1Jtgy` is READY. Its research endpoint returns `MODEL_QUARANTINED` because preview has no research-display enablement; this is expected isolation and does not affect the production endpoint.
- Source inspection identifies the selector's exact gates: validation eligibility, unlabeled fixture, non-null prediction cutoff, canonical fixture and competition IDs, cutoff not in future and strictly before kickoff, kickoff still upcoming, kickoff inside current WAT day, and snapshot age at most six hours. These are candidate rejection reasons, not measured counts; the DB-backed diagnostics have not yet run.
- Correction: the research prediction API admission predicate requires the admission record to have `app_display_enabled=false` (not true). The committed record satisfies this safe-state predicate. Production research endpoint evidence below confirms four research-only forecasts are served; the published-predictions API remains empty and publication disabled.

## Android feed-source trace — 2026-11-27
- Inspected `android/app/src/main/java/com/veltrix/aianalyst/PredictionApi.kt`: the app requests `GET /v1/predictions` (published feed) and `GET /v1/research/predictions` (shadow research feed). There is no local fixture-generation or hard-coded sample prediction fallback in this API client.
- Inspected `VeltrixDashboard.kt`: Home, BTTS, and Over/Under merge published predictions with research predictions; published fixture IDs take precedence on duplicates. Research entries are tagged `researchOnly=true` and the card displays `RESEARCH ONLY`; published entries display `1X2`.
- Correction from live production verification at 2026-11-27 12:48 UTC: the earlier interpretation of the admission predicate was wrong. The predicate explicitly requires \`record.get("app_display_enabled") is False\`; this is the intended safe state and does NOT reject the current admission record. Production \`GET /v1/research/predictions\` returned HTTP 200 and \`SHADOW_FORECASTS_READY\`, with four records from \`hierarchical-poisson-newton-shadow-v2\`, generated at \`2026-11-27T09:18:44.714641+00:00\`, trained on 1,463 fixtures, marked research-only / retrospective-not-PIT-certified / not-published / production-promotion locked / value-betting locked.
- The four live research fixtures were Werder Bremen–Borussia M'gladbach (19:30 UTC), Venezia–Bologna (19:45 UTC), Levante–Racing Santander (20:00 UTC), and Nottm Forest–Chelsea (20:00 UTC), all on 2026-11-27. Their prediction IDs and full market probabilities were returned by the production API at the time of the probe.
- Independently downloaded and parsed validator artifact `15188397754` (run `45978626314`; SHA-256 `3085398969fa58e90ac10504fb18aa6a27bcb7862451033c0d42b002e1d63464`). Its four selected canonical fixture IDs are exactly `152eb358-5e20-48b3-9653-6edbf16a6200`, `26e7cff2-ae95-40a0-85a2-f4976c64c7d2`, `ba208902-76fb-449a-806b-ab8de64c7011`, and `17f5a3cd-cf73-4507-bbab-0bf3f3bad8b0`. These match the four canonical fixture IDs returned by the live research API exactly (set equality, all four). This joins the read-only eligible slate to the model forecast response; the forecast run is distinct in time from the validator manifest and both retain the same four canonical fixtures.
- Production \`GET /v1/predictions\` returned HTTP 200 with \`{"predictions":[]}\`. Thus the four records are not published predictions; they are exclusively the current research shadow feed.
- APK provenance: successful Android build run \`45975833233\`, commit \`9837395b28b238700b6ab10c817ea2424ed74245\`, artifact \`15187725268\`, SHA-256 \`806cca8b62e327e48ba7b814dc21290be27e75b3512c26ea49ad49f0cc832b9c\`. The exact source at that build commit contains \`PredictionApi.fetchResearchUpcoming()\` calling \`/v1/research/predictions\`; its Dashboard merges research forecasts into Home, BTTS and Over/Under and marks them \`RESEARCH ONLY\`. The CI workflow at that commit embeds \`https://veltrix-ai-analyst-api.vercel.app\` as \`API_BASE_URL\`. This proves the built APK is wired to the same live research endpoint and is capable of displaying these four model forecasts. Physical-device runtime/cache verification is still not available, so it does not prove the installed APK has fetched the current response on-device.
- The current production Vercel deployment is READY and points to main commit \`49e71753a5295633a94acc27eae9915a8a043d2f\`; the live API response above was fetched directly through the Vercel deployment URL. No production settings were changed.
- Final provenance conclusion: the backend's four current forecasts are genuine outputs from the named hierarchical Poisson shadow model, not the published feed. The Android APK build is wired to retrieve and label them as research-only. The remaining gap is physical-device confirmation that the installed APK has refreshed and is showing the current four API records.

## Remaining validation blockers
- Execute PR #182's read-only candidate validator and inspect the new rejection counts before deciding which data-coverage issue to address.
- Production API health/date-membership smoke test has not yet been recorded. Vercel READY metadata is not proof of live API response correctness.
- Android physical-device runtime verification remains outstanding. The APK artifact from run `45975833233` was built with the research-feed integration and production API URL. Physical-device refresh/display confirmation remains outstanding.
- Runtime test the zero-fixture path; current source and unit tests support an empty slate, but the successful live validator run had four eligible fixtures.
- Keep research display, publication, Telegram, production promotion, and Value Betting locked until their independent gates and owner controls are explicitly satisfied.

## Safety and model status
- Research predictions remain research-only; publication remains disabled.
- Value Betting remains LOCKED; model certification and promotion remain blocked by independent evidence thresholds.
- No Odds API credits were used for this WAT correction.
- This release changes calendar-day fixture selection only; it does not certify prediction quality or authorize Telegram delivery.

## Next actions
1. Dispatch the read-only validation workflow from `main` with candidate SHA `7fffc7fc05743f3b7fe70c4c7d2505eb7bbe40a8`, then inspect the manifest artifact.
2. Perform a read-only live API response check against the production deployment and verify every returned kickoff date against the current WAT date.
3. Install the successful debug APK on Android and verify date membership, tomorrow exclusion, and empty-slate behavior.
4. Keep publication, Telegram, model promotion, and Value Betting locked until their separate gates pass.


## CI follow-up — 2026-11-27
- PR CI run [#46001949257](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/46001949257) was cancelled when a newer commit superseded it; it is not a validation result.
- PR CI run [#46002052460](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/46002052460): Android debug build PASS; backend tests FAILED with 593 passed and one failed. The failing case was an incorrectly constructed test row, not a production selector regression: with generated=10:00, cutoff=09:30 and kickoff=09:59, kickoff is already past and the cutoff is still before kickoff, so `kickoff_not_upcoming` is the first failure. The corrected row uses cutoff=09:59 and kickoff=09:58, so `cutoff_not_before_kickoff` is the first failure. No eligibility logic was changed.
- The PR ledger had a stale contradictory sentence claiming the admission record required `app_display_enabled=true`; corrected it to the verified predicate `app_display_enabled=false`. The production API evidence and the APK feed-source trace remain as previously recorded.
- PR remains draft/open/unmerged pending fresh backend + Android CI after this correction. No production settings, publication, Telegram, or model-promotion state changed.
