# VELTRIX AI ANALYST

A personal-use, cloud-backed football analysis and prediction platform with a native Android client.

## Project status

**Stage 1 and Stage 2 are complete. Stage 3 — prediction-engine architecture and implementation — is underway.** The dedicated production database and historical ingestion/provenance foundation are operational. Retrospective research candidates (Elo, Poisson and an ensemble) have been fitted and evaluated on the available CBF corpus. They are exploratory, retrospective and non-PIT-certified; no model is approved for production prediction or value betting. The production prediction service and genuine Android prediction integration are not yet ready.

## Project records

- [Project Progress Register](docs/PROJECT_PROGRESS.md) — canonical stage status, completed work, current work, blockers and next tasks.
- [System Architecture](docs/ARCHITECTURE.md) — application and service boundaries.
- [ML Model Architecture](docs/ML_MODEL_ARCHITECTURE.md) — candidate statistical/ML portfolio, ensemble, calibration, evaluation and model-admission specification.
- [Project Ledger Entries](docs/ledger/) — dated, append-only records of material decisions and implementation progress.
- [Stage 2 Data Model](docs/DATA_MODEL.md) — provenance-first PostgreSQL schema and ingestion invariants.
- [Provider Qualification](docs/providers/PROVIDER_QUALIFICATION.md) — approved sources, entitlements, limitations and data-use decisions.
- [5DollarFootballAPI Terms Review](docs/providers/5DOLLAR_TERMS_REVIEW.md) — Community attribution, scope and retention restrictions.

## Core principles

- Native Android application backed by online services.
- Broad global competition coverage with transparent data-quality tiers.
- Independent prediction intelligence built and validated from scratch.
- Selective reuse of reviewed data-provider and infrastructure utilities only.
- Provenance, point-in-time correctness, chronological validation, and market-specific publication gates.
- Cost-conscious infrastructure and incremental data ingestion.
- Never commit secrets, API keys, passwords, raw restricted data, private records, or production credentials.

## Development status

The current implementation boundary and next execution queue are recorded in [docs/PROJECT_PROGRESS.md](docs/PROJECT_PROGRESS.md). Review it before beginning new work.
