# 2026-11-23 — Android kickoff-aware forecast display

## Verified repository work

- PR #154 was merged earlier; `main` uses the 01:00 WAT daily capture cron.
- PR #156 documentation-only audit was squash-merged as `e6de1084b15cbe9828563847b6465b2f97072036`.
- Stale duplicate PR #149 was closed; its newer backend implementation remains in PR #155.
- PR #155 exact-head CI run `45263698136` completed successfully on commit `15ebbc406b698afd202ed0078095a74a28937c7b`: backend tests/lint and Android debug build passed.
- PR #155 remains draft and unmerged because the backend daily feed intentionally retains today's matches after kickoff; Android must suppress probability displays for those records first.

## Android implementation submitted

- PR #157: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/157
- Branch: `fix/android-hide-past-kickoff-forecasts`.
- Current head at ledger time: `050e937119753668be86275d73bd0465ea108271`.
- Existing Compose dashboard layout is preserved.
- Home section renamed from "Upcoming predictions" to "Today's matches".
- Home 1X2, BTTS and Over/Under probability visualizations are hidden at or after kickoff.
- Match names, competition and kickoff metadata remain visible; neutral KICKOFF state is shown.
- Invalid/unparseable kickoff timestamps fail closed by hiding probabilities.
- Added JUnit coverage for future, exact-kickoff, past-kickoff and invalid timestamps.
- Exact-head CI run `45265469390` for commit `050e937119753668be86275d73bd0465ea108271` was queued/in progress at audit time. Earlier attempts on intermediate commits were cancelled when new commits were pushed; they are not pass evidence.
- No CI pass is claimed for the current head yet.

## Manual verification blocker

- Physical-device installation and confirmation remain outstanding.
- Before merge/release, verify on an Android device that:
  1. a future kickoff shows probabilities;
  2. a kickoff at or before current time hides all probability chips/rings/bars;
  3. match identity and kickoff metadata remain visible;
  4. the dashboard refresh does not reintroduce stale forecast displays.
- CI success alone does not satisfy this device check.

## Runtime and safety

- No provider or Odds API requests; no Odds API credits consumed.
- No manual workflow dispatch/rerun.
- No production database writes or deployments.
- No model promotion, forecast publication, certification or value-betting unlock.
- Research and production data paths remain separate; production/value-betting locks remain unchanged.

## Next sequence

1. Finish exact-head CI for PR #157 and fix any test/build failures.
2. Complete physical-device confirmation; merge PR #157 only when safe.
3. Then reconcile and review PR #155 against current `main`; merge the WAT backend feed change only after Android kickoff suppression is integrated.
4. Inspect the first scheduled 01:00 WAT capture and its automatic Stage 6/7 descendants read-only; distinguish fresh imports from already-validated reuse.
5. Continue research forecast validation. Production forecasting remains a separate, locked track.
