# 2026-11-16 — PR #10 merged and Neon preflight passed; historical import awaiting manual dispatch

## CI evidence

- Run: https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/43956828039
- Head: `266182017ffced5b4bec657a26d33f554ad2ad84`
- Conclusion: success.
- Android debug build: passed.
- APK artifact upload: passed.
- Backend tests: passed.
- Ruff lint: passed.

## Merge evidence

- PR: https://github.com/Nexora-Apparel/veltrix-ai-analyst/pull/10
- Merge commit: `6e37dbf7bae782e7b75a1594b69cfa8aab80a422`
- Merged at: 2026-11-16T21:09:10Z.
- Merge method: squash.

## Read-only Neon preflight

- Resource/project: `young-wind-27772160`.
- Database: `veltrix_ai_analyst`.
- PostgreSQL: 18.7.
- Migrations 001–004 are present in `public.schema_migrations`; all recorded checksums match the known repository checksums.
- Canonical approval `approval-5dollar-community-fixtures-2026-11-12` is APPROVED for 5DollarFootballAPI / `5dollarfootballapi`.
- Approved competition scope includes Brazil Serie B ID `522514093`.
- Data types: fixtures/results, competition catalogue and team catalogue.
- Permitted uses include historical import and internal analysis. Commercial use is false; attribution is required; raw redistribution is prohibited.
- Provider request events: 0.
- Provider responses: 0.
- Provider fixture rows: 0.
- Quarantine records: 0.
- Active import runs: 0.
- Existing request reservations: 80.
- Existing checkpoints: 68.
- The 80 reservations and 68 checkpoints are from the previous DB-only dry-run/rehearsal records, not external provider calls.

## Collection scope retained

- Provider: 5DollarFootballAPI, existing Community key via GitHub environment secret only.
- Competition: Brazil Serie B, ID `522514093`.
- UTC interval: `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`.
- 34 contiguous weekly windows.
- Fixtures and results only; no odds calls.
- Maximum 40 fixture endpoint requests, including pagination.
- No retries.
- Maximum 5 requests per minute and at least 12 seconds between requests.
- Durable request reservation must commit before each provider HTTP request. Duplicate reservation must block repeated HTTP.
- Stop and quarantine on the configured error/schema/conflict conditions.
- No model training, calibration or prediction publication until the post-import validator passes and separate PIT/feature eligibility requirements are satisfied.

## Dispatch blocker

The controlled workflow requires manual `workflow_dispatch` with `confirm_collection=COLLECT_BRAZIL_SERIE_B`. Leave optional `resume_run_id` blank because no live import run exists.

Workflow page:
https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/historical-brazil-serie-b.yml

The connected GitHub tools available in this session support workflow reads and reruns but do not expose a workflow-dispatch action. No attempt was made to bypass that gate, and no provider HTTP request was initiated. A human must submit the manual dispatch from the linked Actions page. Once dispatched, inspect the run's reservation count, per-window checkpoints and provider logs, then confirm the workflow's automatic `scripts/validate_brazil_serie_b_import.py` step succeeds. A failed or incomplete validation blocks model training.

## Outcome

- PR #10: merged.
- CI: passed.
- Read-only Neon approval/schema preflight: passed.
- Live historical import: not started; awaiting the required manual workflow dispatch.
- Imported records: 0.
- Model training: not started.
