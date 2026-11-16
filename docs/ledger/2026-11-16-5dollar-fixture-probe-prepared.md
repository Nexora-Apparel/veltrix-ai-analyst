# 5Dollar Brazil Serie B fixture probe prepared

**Date:** 2026-11-16  
**Status:** Implemented; execution pending manual workflow dispatch  
**Scope:** One read-only fixture/results request, one page, no retry, no pagination, no odds, no database writes.

## Source and bounds

- Provider: 5DollarFootballAPI Community.
- Competition: Brazil Serie B, provider ID `522514093` (competition listing visibility was verified in workflow run #43884649616).
- Endpoint: `GET /v1/leagues/522514093/fixtures`.
- Window: `2026-11-07T00:00:00Z` inclusive to `2026-11-09T00:00:00Z` exclusive.
- Page: 1; page size: 100.
- Maximum HTTP requests: 1. Retries: 0. Pagination: never followed.
- Output: a sanitized manifest containing response checksum, response byte count, status, returned field names, pagination metadata and timestamp-like values from the first fixture only. Raw response body and credential are not printed or uploaded.
- Stop conditions: 401/403, 429, redirect, any other non-2xx response, invalid JSON, or unexpected response envelope/schema. A `has_more=true` result is recorded and deliberately not paginated.

## Implementation

- Added `scripts/probe_5dollar_brazil_fixtures.py`.
- Added manual workflow `.github/workflows/5dollar-fixture-probe.yml`.
- Workflow uses the existing Community Actions secret aliases, installs only HTTPX, runs one probe and uploads only the sanitized manifest for 7 days.
- Script and workflow commits: `38968ffd8a6c01ddcbce72a5263b4f47b2c702c8`, `a125f8944cfbb3fb8540bc8960e65a8cd67a10b4`.

## Execution status

The workflow has not yet been dispatched. The available GitHub connection supports repository reads and file writes but does not expose the GitHub Actions `workflow_dispatch` endpoint. Dispatch the workflow manually from the repository Actions tab:

1. Open `https://github.com/Nexora-Apparel/veltrix-ai-analyst/actions/workflows/5dollar-fixture-probe.yml`.
2. Select **Run workflow** on branch `main`.
3. Open the resulting run and inspect the job summary/log and the `5dollar-brazil-serie-b-fixture-probe` artifact.

Do not create a new API key or paste the existing key into chat. The workflow reads the already configured repository secret. No claim is made yet about fixture endpoint access, fields, historical coverage, or timestamp semantics.

## Next gate

After the run completes, inspect the workflow logs and manifest artifact. If the endpoint succeeds, verify schema, counts, timestamp fields and pagination before any larger request budget is proposed. Stop on any declared error condition. No historical import is authorised by this probe.
