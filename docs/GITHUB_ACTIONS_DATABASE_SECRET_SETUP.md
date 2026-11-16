# Secure GitHub Actions database connection — historical import

## Purpose

This is the remaining infrastructure gate for the controlled Brazil Serie B historical import. The importer and failed-page quarantine are implemented and merged. This guide configures the dedicated Neon database connection without exposing it in source, logs, artifacts, chat, or Vercel environment output.

## Required GitHub environment

Repository: `Nexora-Apparel/veltrix-ai-analyst`

Environment: `veltrix-historical-import`

Create an **environment secret** with this exact name:

- `VELTRIX_AI_ANALYST_DATABASE_URL`

Its value must be the PostgreSQL connection URI for the dedicated Neon database `veltrix_ai_analyst` in Neon resource `young-wind-27772160`. Do not use the Vercel integration's default `neondb` URI. Prefer the Neon pooled connection URI if supported by the current Neon connection panel; require TLS/SSL.

The repository workflow already reads this environment secret and sets:

- `EXPECTED_DATABASE_NAME=veltrix_ai_analyst`
- `VELTRIX_ENABLE_HISTORICAL_COLLECTION=true` (only inside the manually dispatched job)
- `FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY` from the existing secret.

Do not add the database URI to repository files, GitHub variables, workflow YAML, build artifacts, issue comments, or chat. Do not print it in a diagnostic command.

## Configuration steps

1. Open the repository's **Settings → Environments → veltrix-historical-import**.
2. Create or open the environment named exactly `veltrix-historical-import`.
3. Add `VELTRIX_AI_ANALYST_DATABASE_URL` as an environment **secret**, not a plain variable.
4. Copy the dedicated database URI from the Neon connection panel for database `veltrix_ai_analyst`; verify the selected database in the Neon UI before copying.
5. Save the secret. Never paste its value into a workflow run input or log.
6. Keep the existing `FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY` secret available to the workflow. Do not rotate or replace it as part of this setup.

## Pre-collection verification

After the secret is configured, validate the connection using a non-collection workflow or a dedicated safe preflight job that:

- opens PostgreSQL using the environment secret;
- queries `current_database()` and fails unless it equals `veltrix_ai_analyst`;
- verifies migrations 001–004 and their expected checksums in `veltrix_ai_analyst.schema_migrations`;
- verifies the approved source record and the Brazil Serie B scope;
- verifies there is no unresolved `PROVIDER_PAGE` quarantine for a candidate run;
- reports only pass/fail and sanitized database identity; never prints connection information;
- performs **zero** 5Dollar HTTP requests and makes no fixture writes.

Do not use the collection workflow as a connection test. Its explicit confirmation input is a live-import authorization.

## Live-import controls

The existing workflow `.github/workflows/historical-brazil-serie-b.yml` is manual-only and requires the exact input `COLLECT_BRAZIL_SERIE_B`. It is additionally protected by the environment secret, database-name checks, the importer's execution flag and environment kill-switch, persistent request reservations, and the database-enforced 40-request ceiling.

Before any live dispatch, review the preflight output and the collection plan. A live run may consume up to 40 Community API requests. No automatic retries are permitted. Stop on any HTTP, schema, integrity, rights, database, or checkpoint failure. Never raise the ceiling to complete a partial run.

## Current state

The environment secret was reported saved on 2026-11-16. Its value is not exposed in repository documentation. A successful Actions preflight is still required to validate it. No live import has run.


## Automated read-only preflight

The user confirmed on 2026-11-16 that the GitHub environment secret was saved. The value remains private and has not been validated by a GitHub Actions runner yet.

After the preflight workflow is merged into `main`, run **Actions → Brazil Serie B Historical Import Preflight → Run workflow**. This is separate from the live importer and has no 5Dollar API key or collection confirmation input.

The script performs a read-only PostgreSQL transaction and checks:
- URI target and `current_database()` both identify `veltrix_ai_analyst`;
- project schema and migration checksums 001–004;
- registered approval `approval-5dollar-community-fixtures-2026-11-12` is effective, non-commercial, attributed and includes Brazil Serie B competition `522514093` plus the approved fixture/result and catalogue data types;
- no unresolved 5Dollar quarantine rows;
- no PLANNED or RUNNING 5Dollar import run.

It reports sanitized checks only and makes zero provider requests, zero reservations, zero fixture writes and zero database mutations. A passing preflight does not itself authorize collection.
