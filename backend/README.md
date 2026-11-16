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
