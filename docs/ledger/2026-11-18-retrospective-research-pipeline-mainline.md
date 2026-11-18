# 2026-11-18 — Retrospective research pipeline mainline port

## Origin and integration

This change ports the owner-authorized retrospective research pipeline from the stale PR #32 branch onto a fresh branch based on current `main`. PR #32 was 57 commits behind main and its CI failed only at Ruff import sorting; its historical test run had 175 backend tests pass and the Android debug build pass. The stale PR is not merged.

## Components

- `backend/app/models/retrospective.py`: provider-local, strictly lagged attack/defence rates, Elo 1X2, Poisson/Dixon-Coles scoreline probabilities and an adaptive Elo/Poisson ensemble.
- `backend/scripts/train_retrospective_research.py`: read-only Neon extraction, score/status checks, exclusion accounting and a deterministic SHA-256 research report.
- `backend/tests/test_retrospective_training.py`: chronology, simultaneous kickoff, draw Elo, duplicate fixture and ensemble regression tests.
- `.github/workflows/retrospective-training.yml`: manual workflow dispatch with explicit research-run confirmation and immutable artifact output.

## Safety boundaries

- The runner reads only `veltrix_ai_analyst` and sets the database transaction READ ONLY.
- FINISHED rows with scores are labels; UNKNOWN rows are excluded.
- Provider-local team IDs remain distinct; no canonical identity or alias merges are performed.
- All results are `RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED`.
- No odds are used as model features, training labels, validation inputs, calibration inputs or inference inputs.
- No prediction API, Android integration, public forecast or value-betting activation is created.
- This is research training on collected historical outcomes, not a reconstruction of what was available to a model at each historical kickoff.

## Validation gate

The port must pass current-main backend tests, Ruff and Android debug build before merge. The manual Neon research workflow must be inspected and explicitly dispatched only after CI passes. Its output is an exploratory retrospective report, not model certification or promotion.
