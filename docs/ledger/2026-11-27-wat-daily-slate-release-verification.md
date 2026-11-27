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
- Added unit tests cover all rejection categories and verify counts are exhaustive and mutually exclusive. PR head: `38ddd8a5c7fbe5a2f150f9ff339f746748db456d`; PR is draft/open; no GitHub Actions workflow runs have been returned yet. Vercel preview check was still pending at last inspection.
- Source inspection identifies the selector's exact gates: validation eligibility, unlabeled fixture, non-null prediction cutoff, canonical fixture and competition IDs, cutoff not in future and strictly before kickoff, kickoff still upcoming, kickoff inside current WAT day, and snapshot age at most six hours. These are candidate rejection reasons, not measured counts; the DB-backed diagnostics have not yet run.
- The research prediction API additionally requires `VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED=true` and an admission record with `app_display_enabled=true`; the committed admission record currently sets `app_display_enabled=false`. Therefore the four Stage 7 shadow forecasts in the validator manifest must not be equated with four predictions currently served to the Android app. The published-predictions API reads only published rows, and publication remains disabled.

## Remaining validation blockers
- Execute PR #182's read-only candidate validator and inspect the new rejection counts before deciding which data-coverage issue to address.
- Production API health/date-membership smoke test has not yet been recorded. Vercel READY metadata is not proof of live API response correctness.
- Android physical-device runtime verification remains outstanding. The current APK was built on the earlier commit and is not evidence that the live research pipeline is connected to the app.
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
