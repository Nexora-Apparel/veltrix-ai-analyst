# 2026-11-20 — Stage 8B CI passed; retrospective rebuild is next

## Verified CI result

- Workflow run: [44711273673](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/runs/44711273673)
- Workflow: `.github/workflows/ci.yml`, manual dispatch.
- Branch: `stage-8b-statistics-ci-release`.
- Tested head: `6aba288a8d102301329d220bc776fa09faa14fbb` (matches PR #123 head at run time).
- Run conclusion: `success`.
- Backend tests: passed.
- Ruff lint: passed.
- Android debug build: passed; APK artifact `veltrix-ai-analyst-debug-apk`, artifact ID `14617771339`, 16,448,825 bytes, SHA-256 `7c7d62718f06ae0909de2c44bbec2073fd5c5dd90a394666b93b052eaf3e5a90`.
- Both CI jobs and all their steps completed successfully.

## Why this matters

The duplicate-sighting reconciliation regression, malformed raw JSON validator failure, and Ruff script-path error are no longer present in the tested candidate head. The CI run confirms code/test/lint/build health for this exact commit. It does not validate model performance, PIT certification, or production inference.

## Next gate

Manually dispatch [Rebuild retrospective research report](https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/retrospective-research-rebuild.yml) on `stage-8b-statistics-ci-release`. The workflow must:
1. Validate completed import runs 19–25 in a read-only transaction.
2. Build the statistics-aware retrospective feature dataset.
3. Rebuild the retrospective research report.
4. Run paired chronological diagnostics.
5. Upload the statistics-aware feature dataset, paired diagnostics and corrected report.

Inspect artifact row counts, feature coverage/null rates, provenance, rights and chronology before any research conclusion. No new provider collection or Odds API request is needed. Do not merge PR #123, deploy, publish predictions, or unlock value betting on CI success alone. Stage 7 certification remains blocked by prospective evidence requirements.

## Manual blocker

The connected GitHub actions interface in this session supports reading run/job data and logs but exposes no workflow-dispatch action. An operator must click **Run workflow**, select `stage-8b-statistics-ci-release`, and start the workflow. After it finishes, inspect the run and artifacts before proceeding.
