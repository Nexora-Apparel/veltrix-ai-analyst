# 2026-11-23 — Capture → Stage 6 → Stage 7 runtime verification

## Repository and documentation state
- Repository: `Nexora-Apparel/veltrix-ai-analyst`.
- Main head after documentation PR #152: `f849d546e73bd3ff8a882d0b1275b4fd0ec39fa0`.
- PR #152 (post-merge workflow-definition audit) was merged after all listed checks passed; merge commit: `f849d546e73bd3ff8a882d0b1275b4fd0ec39fa0`.
- PR #152 changed documentation only: `docs/ledger/2026-11-23-postmerge-automation-audit.md`.
- No production deployment, release-gate change, production publication, value-betting unlock, or Odds API request was initiated.

## Manual capture run
- Workflow: VELTRIX prospective 5Dollar evidence capture.
- Run: [45257630040](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45257630040).
- Event: `workflow_dispatch`; branch: `main`; conclusion: `success`.
- Six approved competitions were processed by the workflow wrapper; all six returned `SKIPPED_ALREADY_VALIDATED`.
- The log reused import run IDs 45–50. A read-only query of `import_runs` confirms those rows were created earlier on 23 Nov between 12:06:23Z and 12:16:07Z, finished by 12:17:57Z, with boundary 22 Nov 00:00Z through 1 Dec 00:00Z.
- The manual dispatch at 20:16Z did not create new import runs or refresh the underlying evidence timestamps. The previous import runs show 2 requests each; these are historical usage, not new requests from the manual dispatch.
- The capture workflow conclusion `success` therefore means the idempotent collector completed without failed competitions; it does not mean fresh evidence was fetched.

## Stage 6 materialization
- Automatically triggered child: [45257770836](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45257770836), event `workflow_run`, conclusion `success`.
- Dataset hash: `7e8a158b168d7c894220ebaa1e56ecfd81cbfbd5a31e9ff6b3b7840fc7d93e91`.
- 14 eligible rows / 14 distinct fixtures; 145 feature-lineage records.
- Persistence: 0 inserted, 14 unchanged; 0 settled label events.
- Append-only and identity verification passed; status `DAILY_MATERIALIZATION_VERIFIED`.
- Release eligibility false; production promotion and value betting remained `LOCKED`.

## Stage 7 automatic inference
- Automatically triggered child: [45258094322](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45258094322), event `workflow_run`, conclusion `success`.
- Shadow report status: `NO_FRESH_UPCOMING_SNAPSHOTS`.
- Fixtures considered/fitted/shown: 0 / 0 / 0. Forecast count: 0. Provider calls: 0. Research-only; production promotion and value betting locked.
- The run was recorded in the isolated research ledger with run key `aceb48c26f7398828cc80ba03494eba8a1d7049112a7d77ca15bb809c450d786`, status `NO_FRESH_UPCOMING_SNAPSHOTS`, forecast count 0, abstention count 0, code commit `4fbdbc9bab83cf04f2d4a423ee83de7388c3ca8e`.
- Separate Stage 7 evaluation: [45258094289](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45258094289), conclusion `success`. It evaluated 0 fixtures and 0 folds; 0 settled labels across all monitored markets. Result: `INSUFFICIENT_PROSPECTIVE_DATA`; production certification blocked; production promotion and value betting locked.
- The auxiliary daily prospective shadow-forecast workflow [45258094335](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/45258094335) was skipped by its trigger conditions; this did not replace the automatic inference run above.

## Read-only production database diagnosis
Database: `veltrix_ai_analyst`, default branch. Queries were SELECT-only.

Snapshot inventory:
- 130 prospective snapshots total.
- 8 snapshots refer to upcoming fixtures at query time.
- 130/130 cutoffs were already reached; 0 had a future cutoff.
- 0 upcoming snapshots met the Stage 7 six-hour freshness condition.
- Latest snapshot creation: 23 Nov 12:19:44Z.
- Latest upcoming-fixture cutoff: 23 Nov 12:06:27Z.
- At Stage 7 generation time (20:21:14Z), that cutoff was about 8.27 hours old.
- The other historical versions of those same upcoming fixture snapshots had cutoffs 37.62, 62.68, and 110.74 hours old.
- The exact research run row was independently read back and confirmed `NO_FRESH_UPCOMING_SNAPSHOTS`, forecast count 0, provider calls 0, production promotion `LOCKED`, and value betting `LOCKED`.

## Interpretation
- The six-hour Stage 7 gate behaved correctly and prevented forecasts from being generated from stale pre-match snapshots.
- The manual capture occurred later on the same UTC date and was idempotently skipped because the six competitions had already been validated for the existing 22 Nov–1 Dec import boundary. It therefore did not refresh source sightings or prediction cutoffs.
- The earlier scheduled capture on 23 Nov had run at approximately 12:06Z. Stage 6 materialized snapshots at approximately 12:18Z. The new Stage 7 automatic inference subscription was merged later that day, so manually replaying capture was useful to test the new chain but too late to satisfy the six-hour snapshot-age requirement.
- This runtime test does not establish a defect in the model or justify weakening the freshness threshold. It establishes that same-day replay of an already-validated capture is not a way to refresh evidence.
- It is expected, but not yet verified, that the next date-scoped scheduled capture will create a new import boundary and fresh evidence timestamps. The next run must prove this rather than relying on assumption.

## Next verification
1. Inspect the next scheduled capture run, distinguishing `schedule` from `workflow_dispatch`.
2. Confirm new import-run IDs, fresh provider-response/sighting timestamps, nonzero newly captured evidence where available, and the actual capture run's event lineage.
3. Verify the exact Stage 6 child run creates fresh snapshot cutoffs and passes append-only/persistence checks.
4. Verify the exact Stage 7 child is triggered from that Stage 6 run and its selected snapshot age is within six hours.
5. Confirm forecast count, team-history abstentions, model monitor, sanitized artifact, and isolated research-ledger row. If no eligible fixtures remain, keep the abstention and investigate source freshness; do not relax the six-hour gate.
6. Reconfirm release eligibility false, production promotion `LOCKED`, and value betting `LOCKED`.

## Known limitations and warnings
- GitHub scheduled workflows are best-effort; this schedule cannot guarantee an exact execution minute.
- A successful capture workflow can be an idempotent no-op. Always inspect import-run IDs, requests, and evidence timestamps, not only the Actions conclusion.
- No claim of production predictions, model certification, or user-facing publication is made from this run.
