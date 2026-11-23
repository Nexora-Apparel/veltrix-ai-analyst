# 2026-11-23 — Stage B1 WAT daily-feed backend implementation

## Scope and status

Backend-only implementation of the canonical Africa/Lagos calendar-day window for published and research daily feeds. This branch is based directly on the current `main` head to retain the merged Stage 7 automation and its tests. Stage B remains incomplete: Android past-kickoff presentation, research history/settlement, and physical app verification are separate follow-ups.

## Repository baseline

- Repository: `Nexora-Apparel/veltrix-ai-analyst`.
- Base branch: `main`.
- Base commit at branch creation: `f849d546e73bd3ff8a882d0b1275b4fd0ec39fa0`.
- Working branch: `fix/wat-daily-feed-mainline`.
- Earlier draft PR #149 was based on an older mainline and diverged after Stage 7 automation merged. Its code was transplanted onto this current-mainline branch; the old draft is not the integration target.

## Changes

1. Added `backend/app/wat_calendar.py`.
   - Uses `ZoneInfo("Africa/Lagos")`.
   - Returns inclusive WAT-midnight UTC start and exclusive next-WAT-midnight UTC end.
   - Rejects naive datetimes.
2. Updated published prediction daily list to use `kickoff_at >= start_utc AND kickoff_at < end_utc`.
3. Updated research daily list to use the same WAT window while preserving the 36-hour latest-run freshness check, 25-fixture cap, research-only marker, unpublished status, production lock, and value-betting lock.
4. Added WAT boundary tests for UTC rollover, same-WAT-day stability, timezone awareness, and both feed-query contracts.
5. Preserved the current mainline Stage 7 automation assertions while updating research-query tests for the third bound parameter.

## CI evidence and correction

- Earlier PR #149 CI run #45248461122: Android debug build passed; backend tests failed only because two research-query tests still expected the old two-parameter UTC-now query.
- Follow-up CI run #45262980770 after correcting those assertions: **546 backend tests passed** and Android debug build passed. Ruff then identified import ordering in the two route files.
- The import ordering was corrected in the source carried to this mainline branch. The current branch still requires its own exact-head CI result; no pass is claimed yet.

## Semantics and remaining review

- The daily API uses a WAT calendar-day window with an inclusive start and exclusive end.
- Today's match records remain in the daily feed even after kickoff; tomorrow's records are excluded.
- Published and research data stores remain separate. Research records remain unpublished and cannot unlock production promotion or value betting.
- **Review blocker:** the existing Android dashboard labels the feed "Upcoming predictions" and currently renders probability chips for every returned row. Past-kickoff rows must retain their match record while hiding forecast probabilities. That UI behavior requires a separate, tested Android change and physical app confirmation; this backend PR does not claim to solve it.
- Research-history settlement must remain isolated from published prediction history and requires verified result lineage before implementation.

## Safety

- No production database writes, provider requests, Odds API requests, workflow dispatches/reruns, deployment, model promotion, or release-gate changes were performed.
- Production forecasts and value betting remain locked.
- Do not merge or deploy this work until exact-head CI, diff review, and the past-kickoff feed/UI contract are reconciled.
