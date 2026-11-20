# 2026-11-20 — Retrospective rebuild failure: scheduled fixtures classified explicitly

## Run evidence

- Workflow: [44711913137](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44711913137)
- Branch/head: `stage-8b-statistics-ci-release` / `7efdc786fb6809add93a346e89281cb28fb5f022`.
- Import validator passed read-only for runs 19–25: 1,601 seen, 595 inserted, zero rejected/quarantined, zero unresolved quarantine; zero database writes and zero provider requests.
- Statistics-aware retrospective feature dataset build passed.
- Training step failed with `UNEXPECTED_STATUS_OR_SCORE_ROWS:2`; paired diagnostics and all uploads were skipped.

## Read-only root-cause audit

The training script selected every provider fixture in competition `522514093`, then allowed only FINISHED-with-two-scores or UNKNOWN-with-no-scores. A read-only Neon query established the complete status distribution:

| Status | Rows | Scored |
|---|---:|---:|
| FINISHED | 380 | 380 |
| UNKNOWN | 4 | 0 |
| SCHEDULED | 2 | 0 |

The two unexpected rows are scheduled fixtures on 2026-11-22:
- `732226564`, kickoff 19:00 UTC.
- `4215081994`, kickoff 21:30 UTC.

They are valid upcoming fixtures, not malformed results. They must be excluded from retrospective outcome training and accounted separately. No production data was changed.

## Corrective implementation

On this branch:
- Added `app/models/retrospective_source.py` with explicit FINISHED / UNKNOWN / SCHEDULED / INVALID row classification.
- Added unit tests for finished, unknown, scheduled, missing-score and partial-score cases.
- Updated the retrospective runner to exclude SCHEDULED rows separately, preserving the four UNKNOWN exclusions and rejecting inconsistent score/status combinations.
- Updated report source accounting to include `scheduled_unlabeled_rows_excluded`; the accounting invariant is now source rows = finished + unknown + scheduled + invalid.
- Added report-validator tests for separately accounted scheduled rows and mismatched accounting.

Expected corpus accounting after correction: 386 source rows = 380 finished labels + 4 unknown unlabeled + 2 scheduled unlabeled + 0 invalid. The 380 finished rows remain the only training/evaluation labels in this report. This expected count must be confirmed by the next run.

## Next gates

1. Run full CI on the updated branch head; require backend tests, Ruff and Android build to pass.
2. Only after CI passes, rerun the retrospective rebuild workflow on the same latest head.
3. Confirm the report includes 380 finished labels, 4 UNKNOWN exclusions, 2 SCHEDULED exclusions and zero invalid rows; inspect report hash and paired diagnostics.
4. Confirm all three artifacts upload successfully, then inspect statistics-aware dataset coverage, null rates, provenance and rights.

No repeat historical collection, 5Dollar requests, Odds API requests or production DB writes are needed. No merge, deployment, production publishing or value-bet unlock.
