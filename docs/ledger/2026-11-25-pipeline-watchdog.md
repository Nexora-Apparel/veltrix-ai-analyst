# 2026-11-25 — Pipeline watchdog and Stage 7 verification

## Verified Stage 6 / Stage 7 chain
- Capture run [45647801888](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45647801888) succeeded, but all six competitions returned `SKIPPED_ALREADY_VALIDATED`; no fresh provider observations were captured.
- Stage 6 run [45647925344](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45647925344), job 139323867954, passed persistence and read-back. Artifact 15039492090, SHA-256 `4272c728b121c8d0dc40ffaf4819bb94abab2351e567227a96512c65c115c4c4`: 114 rows (54 settled, 60 unsettled), 1,442 identity rows, 3,038 lineage records, zero invalid system-observed sightings. All 114 snapshots were reused; zero new snapshots. Dataset SHA-256 `414d8333f8f8bf7dd9d2318994ac64521f1448d2c5c04eee34d5297c2e50bd54`.
- Latest unsettled cutoff was `2026-11-25T08:40:05.859675Z`; Stage 6 dataset was created at `2026-11-25T15:51:53.747065Z`. The six-hour freshness rule correctly rejects these targets.
- Exact Stage 7 inference run [45649375866](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45649375866), job 139329344684, completed successfully but returned `NO_FRESH_UPCOMING_SNAPSHOTS`: forecast_count=0, fitted_fixture_count=0, provider_calls=0, odds_used=false, database_writes=0, predictions=[]. Artifact 15039553652, SHA-256 `148cd82f97242f93b1800f614d51c75744d32885359f283220da8e28e227f892`. No prediction rows were produced.
- Stage 7 evaluation [45649375818](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45649375818), job 139329343826, completed successfully. Artifact 15038279867, SHA-256 `4f597f255775a9169e2cce3c55373fe5cf18b0dc02200dc15ad212d8eaf1bb85`: 54 prospective settled fixtures, 6 settled kickoff dates, 3 expanding folds, 54 walk-forward fixtures per market. Required gates remain 1,000 per market, 300 settled selections, 90 dates and 98% timestamped odds coverage. Bookmaker comparison and ROI were not evaluated. Certification remains `BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE`; production promotion and Value Betting LOCKED.
- The 1,408 historical training-only rows remain separate from prospective validation. Shot, possession, attack and event features are captured but not yet used by the hierarchical goal-rate model.

## Watchdog PR #177
- PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/177
- Branch: `feat/daily-pipeline-watchdog`; latest commit at time of this update: `e2ebaedb19b380775df8bf970c2e57cd2b6eaa36`.
- Watchdog runs 04:17 UTC (05:17 WAT), after the 00:17 UTC capture. It recovers a missing run, avoids duplicates while capture is active, retries failed jobs once, and recovers queued runs after 120 minutes. It reuses the existing capture workflow and does not directly call football or odds providers.
- Review found a cross-day edge case: a previous-day queued capture was outside the same-day queued recovery path. The workflow now detects previous-day queued runs, waits for the 120-minute threshold, then dispatches recovery.
- CI was updated to include the watchdog in actionlint and path filters. CI run 45649795235 passed Android and backend jobs on older head `ba257cd4d392954eb3e97c90dd4f3102f3122747`; it does not validate the latest fix. No CI run is visible for latest head `e2ebaedb19b380775df8bf970c2e57cd2b6eaa36`. PR remains open/unmerged; do not merge until exact-head CI and actionlint pass. Watchdog is not active until merged.

## Fresh observation recovery — next implementation
- Stage 6 persistence is not failing. It is correctly replaying the same immutable 114 snapshots.
- Root cause: `completed_run()` skips a validated import for the same competition, exact boundaries and import type without checking observation age. Re-dispatching capture with the same rolling window therefore does not fetch fresh provider evidence.
- Implement an explicit, bounded refresh mode in the existing prospective capture path, guarded by the latest valid capture sighting's database-derived `system_observed_at`. Permit at most one refresh cycle per UTC date and skip if observations are already fresh.
- Preserve the 24-request workflow ceiling, four requests per competition, six approved competitions, 60-second pacing, source approval, import checkpoints and idempotency. Do not use The Odds API for this recovery.
- A refresh must create a real provider response and source-observation sighting. Never rewrite prior sightings, manufacture timestamps, bypass immutable snapshot keys or relax PIT gates.
- Verify new observation timestamps, new Stage 6 PIT cutoffs, Stage 7 report and research-ledger rows, API response, and physical Android rendering before claiming predictions are visible.

## Release status
- Current research inference has zero forecasts; predictions are therefore not currently expected in Android.
- Research-only display remains conditional on valid forecasts. Production publication, Telegram, model promotion, certification and Value Betting remain locked.
- Six-hour freshness, immutable evidence, rights, fixture identity and concentration controls remain unchanged. No Odds API calls were made.
