# 2026-11-26 — WAT daily slate selection correction

## Scope
Correct the confirmed defect where the Stage 7 daily forecast slate could include fixtures from later WAT calendar dates.

## Repository state
- Repository: `Nexora-Apparel/veltrix-ai-analyst`
- PR: [#160 — Restrict daily Stage 7 forecasts and feeds to the WAT calendar day](https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/160)
- Branch: `fix/wat-daily-feed-current-mainline`
- Latest implementation head at ledger creation: `88faef149c06e8da21c5921aacc2b67199f780a9`
- PR remains draft and is not merged.

## Changes
1. Reused the canonical `Africa/Lagos` WAT day-window helper.
2. Added a pure Stage 7 daily-target selector that:
   - preserves existing validation eligibility, PIT cutoff, kickoff-before-prediction, and six-hour snapshot-age requirements;
   - includes only fixtures with kickoff in the current WAT calendar day;
   - sorts eligible same-day fixtures by kickoff and fixture ID;
   - applies the maximum-25 cap after date filtering.
3. The selector returns no targets when there are no eligible fixtures today. Tomorrow's fixtures cannot fill the daily slate.
4. The existing PR feed changes apply the same inclusive-start/exclusive-end WAT window to published and research API queries.
5. Added unit tests for tomorrow exclusion, no-today empty slate, and cap-after-filter behavior.

## Verification evidence
- Earlier feed-only PR head `12dcb369a44f120ee7be048d56ddfac0ae984ee7` passed backend tests/lint and Android debug build in CI run [#45265970048](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45265970048).
- The Stage 7 selector and its new tests were added after that run. Exact-head CI for the latest implementation has **not** been observed; do not claim those tests passed.
- Vercel preview deployment for the latest head was pending at the last status check.
- No live provider, The Odds API, database, production deployment, workflow dispatch, model promotion, publication, or Value Betting action was performed.

## Safety and blockers
- Research forecasts remain `RESEARCH ONLY` and `NOT_PUBLISHED`.
- Production promotion and Value Betting remain `LOCKED`.
- Do not merge or release until exact-head backend tests/lint and Android debug build pass, the PR base is reconciled with current main, and physical Android feed behavior is verified.
- The six-hour PIT freshness and all existing eligibility gates are preserved.
