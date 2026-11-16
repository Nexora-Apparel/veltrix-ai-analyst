# Backend API

FastAPI service foundation for VELTRIX AI ANALYST.

## Local setup

Requires Python 3.11 or newer.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

- Liveness: `GET /health`
- API docs: `GET /docs`
- Tests: `pytest`
- Lint: `ruff check app tests`

The health endpoint reports process liveness only. Database/provider readiness checks will be added when those dependencies are implemented.

## Provider qualification

The isolated 5DollarFootballAPI adapter is in `app/providers/five_dollar.py`.
It uses `FIVE_DOLLAR_FOOTBALL_API_KEY` from the runtime environment; no key is
stored in the repository.

For a safe account/coverage check:

```bash
python -m pip install -e backend
export FIVE_DOLLAR_FOOTBALL_API_KEY="your-key"
python scripts/verify_5dollar_access.py
```

The verifier prints the account plan, quota metadata and Brazil competition
listing only. It does not print the credential or download historical fixtures.
Automated adapter tests use mocked HTTP responses and do not call the provider.

## AI Midas Brazil Serie B snapshot

The approved source is a pinned, non-commercial GitHub CSV snapshot, not a verified live API.
Capture it locally with:

```bash
python -m pip install -e backend
python scripts/collect_aimidas_brazil_serie_b_snapshot.py
```

The raw file is written under `.local-data/`, which is ignored by Git. Do not
upload the raw CSV to this public repository or publish it as a workflow artifact.
The manifest records its source commit, hashes, row/match/team counts, attribution,
non-commercial rights, and point-in-time restrictions. The collector does not
write to a database or admit any fields to prediction features.

## PostgreSQL schema foundation

The first migration creates the `veltrix_ai_analyst` schema for source approvals,
provider responses, entitlement observations, immutable source observations,
provider-local competitions/teams/fixtures, import checkpoints, watermarks and
quarantine records.

Apply migrations only to the explicitly named new database:

```bash
python -m pip install -e backend
export DATABASE_URL="postgresql://USER:PASSWORD@HOST:5432/veltrix_ai_analyst"
export EXPECTED_DATABASE_NAME="veltrix_ai_analyst"
# Remote database targets require this explicit opt-in after verifying the new DB.
export ALLOW_REMOTE_MIGRATIONS="true"
python scripts/apply_migrations.py
```

The runner verifies each SQL file's SHA-256, refuses database-name mismatches, blocks legacy database names, and refuses remote hosts unless `ALLOW_REMOTE_MIGRATIONS=true` is explicitly set.
It explicitly blocks the legacy `veltrix-football` database names. CI validates
the migration against an ephemeral PostgreSQL 16 service. No production database
has been provisioned or connected by this commit.

## Runtime ingestion store

`app.db.store.PostgresIngestionStore` is the rights-aware persistence boundary.
It writes immutable source approvals, raw provider responses, source observations,
provider-local competition/team/fixture projections, import runs/checkpoints and
quarantine records. It validates exact source scope and effective approval status
before writes, strips sensitive response headers, rejects secret-like request
parameters, and prevents provider identity mismatches.

The store accepts an existing `psycopg.Connection`; the caller owns transaction
boundaries. It does not create a production connection or perform automatic
provider downloads. Live ingestion is enabled only after a private database and
provider credentials have been configured and verified.
