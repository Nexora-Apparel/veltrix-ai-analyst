# Brazil Serie B historical import operator runbook

## One-time GitHub secret setup

1. Open the repository settings and create/select the GitHub Actions environment named `veltrix-historical-import`.
2. Add an environment secret named `VELTRIX_AI_ANALYST_DATABASE_URL`.
3. Set its value to the PostgreSQL connection URI for the dedicated Neon database `veltrix_ai_analyst` in Neon resource `young-wind-27772160`.
4. Verify the URI path is exactly `/veltrix_ai_analyst`. Do not use the Vercel integration-generated `POSTGRES_URL` values; those point to `neondb`.
5. Confirm the existing repository secret `FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY` is available to the workflow. Do not paste either secret into issues, pull requests, workflow logs or chat.
6. If available, configure a required environment reviewer for `veltrix-historical-import`.

## Manual execution

1. Open Actions → **Controlled Brazil Serie B Historical Import** → Run workflow.
2. Select `COLLECT_BRAZIL_SERIE_B` in the confirmation input.
3. Leave `resume_run_id` empty for the first run.
4. The workflow imports only Brazil Serie B competition `522514093`, for the fixed interval `[2026-03-21T00:00:00Z, 2026-11-09T00:00:00Z)`.
5. The importer reserves each request before HTTP, uses a maximum of 40 requests and spaces requests by at least 12 seconds.
6. The workflow runs the read-only quality validator only after the importer reports a completed run.

## Stop and recovery rules

- A PAUSED or quarantined run is not automatically replayed.
- A run with unresolved quarantine requires manual reconciliation; the importer refuses automatic resume.
- A 40-request budget stop is not permission to increase the budget.
- Do not rerun the workflow with a new run ID to bypass unresolved reservations or quarantine.
- Do not collect odds, other competitions or other date ranges through this workflow.
- Historical fixture observations are stored with retrieval-time provenance only and are not certified as point-in-time pre-match features.
- A successful import/quality report does not certify bookmaker closing odds, CLV, or prediction-model readiness.
