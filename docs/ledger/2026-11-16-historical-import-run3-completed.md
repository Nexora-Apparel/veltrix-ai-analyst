# 2026-11-16 — Brazil Serie B historical import run 3 completed and validated

## GitHub Actions evidence

- Workflow: [Controlled Brazil Serie B Historical Import](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b.yml)
- Run: [#43964327879](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43964327879)
- Job: [#133639654596](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43964327879/job/133639654596)
- Event: `workflow_dispatch`, branch `main`, attempt 1.
- Commit: `e1b7a426158b0312f65a4f6369494a93f2c608ee`.
- Workflow conclusion: `success`; all seven job steps completed successfully.
- Migration verification step completed successfully and reported no migrations to apply.
- Importer emitted `HISTORICAL_IMPORT_FINISHED:run_id=3`.
- Automatic validator completed successfully at 2026-11-16T22:04:59Z.

## Final validator result

```json
{
  "boundary_start": "2026-03-21T00:00:00+00:00",
  "boundary_end": "2026-11-09T00:00:00+00:00",
  "checkpoints": 34,
  "completed_checkpoints": 34,
  "database": "veltrix_ai_analyst",
  "failures": [],
  "fixture_rows": 374,
  "fixture_sightings": 374,
  "import_run_id": 3,
  "non_pit_observations": 0,
  "passed": true,
  "records_duplicate": 0,
  "records_inserted": 374,
  "records_quarantined": 0,
  "records_seen": 374,
  "request_budget": 40,
  "request_events_with_raw_response": 34,
  "requests_used": 34,
  "status": "COMPLETED",
  "unresolved_quarantine": 0
}
```

## Recovery and quota outcome

- Run 3 was resumed in place; no new import run was created.
- The interrupted Aug 29–Sep 5 page was reconciled using its reservation-bound captured HTTP 200 response; the reserved request was not repeated.
- The 10 remaining windows completed.
- Final provider request count is 34/40, leaving six unused requests in the approved run budget.
- All 34 request events have raw response evidence.
- No duplicates, quarantines or unresolved quarantine records were reported.
- The job did not exceed the configured request budget.

## Data eligibility and restrictions

- The validator's `non_pit_observations=0` field does not certify provider publication timestamps.
- Provider kickoff/event timestamps are not publication/availability timestamps. This import therefore does not establish point-in-time feature eligibility.
- Do not use these observations as pre-match model features, CLV evidence, or point-in-time backtest inputs unless independent, reliable source-availability timestamps are obtained and validated.
- Descriptive fixture/result history and source-quality research may proceed within the approved non-commercial, attribution-required, no-raw-redistribution terms.
- No odds collection, model training, calibration, prediction publication, or production deployment was performed by this workflow.

## Next engineering stage

1. Audit competition/date coverage, fixture identity stability, team identity consistency, score/status completeness, and duplicate/collision risks.
2. Build a canonical fixture layer with provenance-preserving cross-source matching; do not merge AI Midas and 5Dollar rows without explicit identity and rights checks.
3. Implement point-in-time feature eligibility as a hard gate requiring verifiable source availability timestamps.
4. Only then design chronological training/evaluation datasets. Keep prediction publication disabled until model validation gates are met.
