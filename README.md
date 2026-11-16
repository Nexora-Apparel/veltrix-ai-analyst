# VELTRIX AI ANALYST

A personal-use, cloud-backed football analysis and prediction platform with a native Android client.

## Project status

**Stage 1 of 10 is complete. Stage 2 — data integrations, source qualification and historical-data foundation — is in progress.** The backend and Android foundations exist, but no production database, live provider import, prediction model, or prediction service is claimed to be operational.

## Project records

- [Project Progress Register](docs/PROJECT_PROGRESS.md) — canonical stage status, completed work, current work, blockers and next tasks.
- [System Architecture](docs/ARCHITECTURE.md) — application and service boundaries.
- [ML Model Architecture](docs/ML_MODEL_ARCHITECTURE.md) — candidate statistical/ML portfolio, ensemble, calibration, evaluation and model-admission specification.
- [Project Ledger Entries](docs/ledger/) — dated, append-only records of material decisions and implementation progress.
- [Stage 2 Data Model](docs/DATA_MODEL.md) — provenance-first PostgreSQL schema and ingestion invariants.
- [Provider Qualification](docs/providers/PROVIDER_QUALIFICATION.md) — approved sources, entitlements, limitations and data-rights decisions.
- [5DollarFootballAPI Terms Review](docs/providers/5DOLLAR_TERMS_REVIEW.md) — Community attribution, scope and retention restrictions.

## Core principles

- Native Android application backed by online services.
- Broad global competition coverage with transparent data-quality tiers.
- Independent prediction intelligence built and validated from scratch.
- Selective reuse of reviewed data-provider and infrastructure utilities only.
- Provenance, point-in-time correctness, chronological validation, and market-specific publication gates.
- Cost-conscious infrastructure and incremental data ingestion.
- Public source repository; never commit secrets, API keys, passwords, raw restricted data, private records, or production credentials.

## Development status

The current implementation boundary and next execution queue are recorded in [docs/PROJECT_PROGRESS.md](docs/PROJECT_PROGRESS.md). Review it before beginning new work.
