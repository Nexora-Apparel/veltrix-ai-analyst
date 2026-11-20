# 2026-11-20 — First-launch activation checkpoint

## Repository state verified

- Default branch: `main`
- Main HEAD: `bea70392e45e97848d0df006ffef7dbb262bcb47` (PR #124 merge)
- Main CI run `44762169304`: completed successfully.
- PR #74 (`feature/hierarchical-sparse-team-rates`) remains open and unmerged. Its base SHA is behind current main; do not merge without rebasing/reconciliation and fresh CI.
- Existing prospective shadow workflow: `.github/workflows/prospective-shadow-predictions.yml`; scheduled daily at 05:00 UTC, manually dispatchable, and triggered after successful Stage 6 completion.
- Existing prospective capture workflow: `.github/workflows/prospective-5dollar-daily-capture.yml`; scheduled daily at 03:00 UTC (04:00 WAT), manually dispatchable.
- Existing shadow builder is read-only: max 25 fixtures, six-hour snapshot freshness, minimum 30 cutoff-valid training labels, no provider calls, no database writes, and all output remains NOT_PUBLISHED / promotion LOCKED / value betting LOCKED.
- Stage 6 output is consumed by the shadow workflow only after successful Stage 6 completion.

## Activation status at 2026-11-20 16:38 WAT

- The latest main commit includes the PR #124 capture reconciliation fix.
- The next scheduled capture opportunity is 2026-11-21 03:00 UTC / 04:00 WAT.
- The existing 19 November snapshots are too old for the six-hour shadow freshness gate. Do not run shadow inference against them as if they were current.
- The 20 November failed capture must not be blindly rerun: it used the pre-fix code and already made 13 provider requests. The France Ligue 1 identity conflict remains excluded.
- The current GitHub integration exposes repository reads and selected GitHub writes, but no workflow-dispatch action. Therefore a manual dispatch cannot be executed from this session. The scheduled capture remains configured; if it is missed, dispatch the existing workflow from GitHub Actions UI rather than repeating the old run.

## Remaining implementation gap

- `backend/app/research/prospective_shadow.py` generates deterministic, cutoff-safe shadow forecasts but does not persist them.
- The production prediction schema in migration 014 requires a PIT-certified, production-approved model artifact before a production prediction can be inserted or published. The current shadow model is explicitly research-only and must not bypass that guard.
- Build a separate append-only research forecast ledger for immutable shadow outputs, with fixture/cutoff/model identity, generated timestamp, training cutoff/hash, dataset and snapshot hashes, full market distributions, code commit, and idempotency constraints.
- Keep shadow research records separate from `predictions`, `published_predictions`, publication events and settlement events.
- Do not apply a new migration or write to production Neon without explicit user approval.

## Next execution sequence

1. Observe the 21 November 03:00 UTC capture on the corrected main commit; verify per-scope provider request counts, inserted/quarantined records and France conflict handling.
2. Verify Stage 6 materializes only independently validated scopes and produces fresh snapshots.
3. Confirm the automatic shadow workflow runs from that successful Stage 6 completion; inspect the artifact for training cutoff, label count, data hash, convergence, abstentions and <=25 forecasts.
4. Implement and test the append-only research forecast ledger separately from production publication.
5. Preserve the existing Android UI. Connect it only to eligible published forecasts once the model release and publication gates are genuinely satisfied.

## Safety boundaries

- No provider request or Odds API credit was spent during this checkpoint.
- No production database write, migration, prediction insert, publication, settlement insert or Vercel deployment occurred.
- Value betting and production promotion remain LOCKED.
- Verified facts are distinguished above from future scheduled actions; no capture or Stage 6 run after PR #124 is claimed as completed.
