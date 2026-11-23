# 2026-11-23 — Post-merge morning readiness audit

## Verified repository changes

- PR #154, `Move VELTRIX capture earlier for 07:00–10:00 WAT readiness`, was squash-merged.
- Merge commit: `0dae617d299aa005a64dea7bf102cb64525b3a8b`.
- Post-merge PR metadata reports `state=closed`, `merged=true`.
- The `main` workflow file was read back after merge and contains cron `0 0 * * *` UTC, equivalent to 01:00 WAT.
- The workflow summary now identifies the 07:00–10:00 WAT downstream readiness target.
- The existing provider, request budget 4, 180-minute timeout, PIT checks, concurrency and Stage 6/7 triggers remain unchanged in the reviewed change.
- PR #154 exact-head CI run `45260639492` completed successfully.

## WAT daily-feed work — not merged

- PR #155: `https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/155`.
- Head commit: `15ebbc406b698afd202ed0078095a74a28937c7b`.
- Exact-head CI run `45263698136` completed successfully: Android debug build passed; backend tests and lint passed.
- PR #155 remains a draft and must not be merged yet.
- Its base was `f849d546e73bd3ff8a882d0b1275b4fd0ec39fa0`; PR #154 has since advanced `main`, so PR #155 needs reconciliation with the new mainline before final review.
- Known product contract blocker remains: the WAT daily feed includes today's records after kickoff, while Android currently labels the section "Upcoming predictions" and renders probabilities for every returned row. Preserve the match record but hide forecast chips after kickoff. This requires a separate Android implementation, tests and physical-device confirmation.
- PR #155's diff also explicitly keeps published and research stores separate and preserves the research freshness check, 25-fixture cap, NOT_PUBLISHED status and production/value-betting locks.

## Runtime verification still pending

The earlier capture schedule is now active on `main`, but a successful scheduled run has not yet been verified by this audit.

1. Inspect the scheduled capture expected at 01:00 WAT on 24 November.
2. Distinguish genuinely fresh provider imports from `SKIPPED_ALREADY_VALIDATED` reuse.
3. Verify Stage 6 materialization, immutable snapshot lineage and artifact.
4. Verify automatic Stage 7 execution, eligible fixture count, persisted research forecasts and research-run artifact.
5. Confirm production publication/model promotion and value betting remain locked.
6. Record actual end-to-end timing against the 07:00–10:00 WAT target.

## Safety and non-actions

- No workflow was manually dispatched or rerun.
- No 5DollarFootballAPI or Odds API request was made as part of this review; no Odds API credits were spent.
- No production database write or deployment was performed.
- No model was promoted; no prediction was published; value betting remains locked.
- No freshness or release gate was weakened.

## Next implementation sequence

1. Rebase/reconcile PR #155 with the new `main` head; keep it draft until the Android past-kickoff contract is fixed and verified.
2. Implement the Android probability-chip suppression while retaining past-kickoff match records, preserving the existing UI design.
3. Add/verify Android tests and build; physical-device confirmation remains a separate required check.
4. Inspect the first scheduled morning capture and its Stage 6/7 child runs read-only.
5. Continue research forecast validation. Production forecast development remains isolated and must not alter the research pipeline.
