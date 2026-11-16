# 2026-11-16 — Historical import attempt #1 stopped before provider HTTP

## Workflow evidence

- Run: https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43954509888
- Job: https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43954509888/job/133605398471
- Commit: `dc5a653186a2ea6b7842c45fc912e59f82d086dd`
- Conclusion: failed at the bounded-import step; post-import validator skipped.

## Failure

The importer raised `EvidenceConflict: SOURCE_APPROVAL_ID_ALREADY_EXISTS_WITH_DIFFERENT_EVIDENCE` in `PostgresIngestionStore.sync_source_approval()`, called by `create_import_run()`. It failed before reaching the provider fixture-fetch loop.

## Root cause

`SourceApproval.scope_values`, `data_types`, and `permitted_uses` are Python sets. The writer sorts these collections when building the expected comparison tuple. PostgreSQL JSONB arrays preserve array order, and the existing-row comparison did not normalize the retrieved arrays. The existing registered grant contained the same members but in a different order, causing a false evidence conflict.

A read-only query of `veltrix_ai_analyst.source_approvals` confirmed the registered approval matches the code grant semantically: same provider/source, competition scope and seven IDs, data types, approved status, terms URL/version, evidence URI/hash, review metadata, permitted uses, non-commercial setting, attribution and raw-redistribution restrictions.

## Post-failure database verification

Read-only counters:

| Metric | Value |
|---|---:|
| Fixture request events | 0 |
| Fixture response records | 0 |
| Imported provider fixtures | 0 |
| Import runs | 2 |
| Request reservations | 80 |
| Checkpoints | 68 |

The two import runs, 80 reservations and 68 checkpoints are the earlier database-only dry-run/rehearsal records. No external provider requests were made by this failed attempt. No odds requests or model operations occurred.

## Corrective change

PR #10: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/10

- Normalize persisted `scope_values`, `data_types`, and `permitted_uses` by sorting before comparison.
- Keep all scalar evidence fields and evidence hashes under strict equality.
- Add an integration regression test that persists the same three collections in reverse order and asserts that synchronizing the unchanged approval succeeds.
- Do not alter the approved grant, scope, purposes, rights basis or commercial restrictions.

## Gate

Historical collection remains paused until PR #10 CI passes, the fix is merged, and the read-only approval preflight succeeds. Afterward, resume only the explicitly authorized Brazil Serie B scope and enforce the original 40-request ceiling. No odds or model training are in scope.
