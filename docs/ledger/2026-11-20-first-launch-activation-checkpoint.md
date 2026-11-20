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

## Implementation added on PR #125

- Added migration `019_research_shadow_forecast_ledger.sql` defining a dedicated append-only research run ledger. It stores the complete report JSONB plus report hash, dataset/training hashes, model version, code commit, cutoff timestamps, forecast and abstention counts.
- Added `app.research.shadow_ledger` to validate the research-only state, all five market distributions, probability normalization, per-forecast pre-match chronology, model/training lineage, 25-fixture cap and stable idempotency key before any write.
- Added `scripts/persist_prospective_shadow_forecasts.py`. Writes require both the explicit CLI confirmation flag and `VELTRIX_SHADOW_LEDGER_WRITE_ENABLED=true`; the database URL must target `veltrix_ai_analyst`. Repeated identical runs are idempotent; conflicting content under the same run key fails closed.
- Added unit tests for immutable identity, locked publication/value-betting state, market balance, chronology, fixture cap, explicit write opt-in and database target. Extended migration integration assertions to include migration 019 and the append-only trigger.

## Verification boundary

- These changes are committed to the PR #125 feature branch; CI is the next verification gate.
- The scheduled shadow workflow remains read-only and was deliberately not modified to write to production Neon.
- Migration 019 has **not** been applied to production. The writer has **not** been executed. No production database write or provider request was made.
- Before enabling persistent writes, a separately approved migration and explicit production-write authorization are required. Do not add the production DB secret to Preview or automatically run the writer from the scheduled workflow.

## CI iteration

- First full backend test pass completed: **487 passed, 1 warning** on commit `558cb158026e3299505a19549b266dfa53bc06db`.
- Ruff then found three `TRY004` findings in the new validator (invalid input types were raised as `ValueError` rather than `TypeError`). Corrected those exception classes in commit `be89293df48ebdf0ea71b3fe2302648bf6d8a42b`.
- Fresh CI run `44766266221` is in progress against the corrected commit. Do not treat the earlier lint failure as passed; await this rerun's completed checks.


## 2026-11-20 16:5x WAT — PR #125 final CI and migration safety review

- PR #125 head: `0260ce23ef871fc7ef9dc3b632b799dddd4c8f13`; base is current main `bea70392e45e97848d0df006ffef7dbb262bcb47`; PR remains open and GitHub reports it mergeable.
- CI run [44766392542](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44766392542) completed successfully on the exact PR head. Both jobs passed: Backend tests and lint; Android debug build. Earlier interrupted CI attempts are superseded by this completed run.
- The capture workflow remains scheduled for 03:00 UTC / 04:00 WAT daily. The only capture run found in the current recent run inventory is the pre-fix 20 November run [44725750217], which failed. No post-PR #124 capture, Stage 6 materialization or shadow forecast run is verified yet. Next scheduled capture is 21 November 04:00 WAT.
- Critical merge-safety finding: `.github/workflows/apply-database-migrations.yml` has a `push` trigger on `main` for `backend/migrations/*.sql`; its migration job automatically applies all pending migrations using the production database secret. Therefore merging PR #125 would trigger migration 019 against production. This is a production schema write, not a documentation-only merge.
- PR #125 is intentionally **not merged**. Migration 019 has not been applied and the writer has not been run. No production database write, provider request, Odds API credit use or Vercel deployment occurred in this checkpoint.
- Do not merge PR #125 or apply migration 019 without explicit production-write authorization. Safe alternative under evaluation: preserve immutable shadow reports as GitHub Actions artifacts first, with hashes and run metadata, without production Neon persistence. Revisit the DB ledger only through an explicitly approved migration path.
- France Ligue 1 remains excluded for its unresolved provider fixture identity conflict. Publication and value betting remain locked.
