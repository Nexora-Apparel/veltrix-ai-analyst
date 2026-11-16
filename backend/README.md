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
