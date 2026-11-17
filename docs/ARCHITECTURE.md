# VELTRIX AI ANALYST — Architecture

## System boundary

VELTRIX AI ANALYST is a personal-use, cloud-backed football intelligence product. The Android application is the native client. The backend owns provider communication, data normalization, research orchestration, prediction computation, and historical records.

```text
Android app (Kotlin / Compose)
        |
        | HTTPS + authenticated API
        v
FastAPI backend
        |
        +--> Domain services
        +--> Data provider adapters
        +--> Research and intelligence pipeline
        +--> Prediction and evaluation engines
        |
        +--> PostgreSQL (system of record)
        +--> Optional Redis (cache/queue when justified)
        +--> Background worker(s)
```

## Android client

- Kotlin and Jetpack Compose.
- MVVM with clear separation between presentation, domain, and data layers.
- Retrofit/OkHttp for backend communication when API integration is introduced.
- Room for deliberately selected local/offline data.
- WorkManager for durable client-side background work where appropriate.
- No prediction mathematics or provider credentials embedded in the client.

## Backend

- Python 3.11+, FastAPI, and Pydantic.
- Versioned API contracts and explicit request/response models.
- Provider adapters isolate provider-specific schemas and failure behaviour.
- PostgreSQL stores canonical entities, source provenance, snapshots, predictions, and settlements.
- Redis and distributed task infrastructure are optional, not default dependencies.

## Data pipeline

Ingestion must be incremental, deduplicated, rate-limited, and provenance-aware. Store provider identity, retrieval timestamps, source event timestamps when available, normalized identifiers, and quality flags. Never silently fill missing values with fabricated data.

## Prediction intelligence

All prediction calculations, feature engineering, calibration, consensus logic, and publication gates are new implementations. Candidate models are admitted only after chronological out-of-sample evaluation. No legacy prediction priors, weights, calibration parameters, or decision rules are imported.

## Reliability and security

- Secrets are supplied at runtime through environment variables or managed secret storage.
- All production API access is authenticated and transported over HTTPS.
- Database migrations are version-controlled.
- Logs are structured and scrubbed of credentials and sensitive payloads.
- Health/liveness is distinguished from dependency readiness.
- Backups, restore checks, and auditability are required before production.

## Cost controls

Start with a single API service, PostgreSQL, and a simple worker. Add Redis, queues, object storage, or separate services only when usage and reliability requirements justify them. Cache provider responses and avoid repeated full-history downloads.

## Current implementation boundary

Stage 2 has provisioned the dedicated `veltrix_ai_analyst` database and completed 384-fixture ingestion, provenance and canonical source-row materialization. The backend currently exposes liveness and contains provider/ingestion foundations plus the original timestamp-only eligibility guard. Stage 3 PR #23 adds immutable prediction/evidence contracts and a stricter application admission validator that additionally requires active rights for feature engineering and model training, verified canonical identity, exact sighting/response lineage and non-quarantined status. Elo, Poisson, Dixon–Coles, chronological evaluation and prediction publication remain unimplemented. Current historical observations are not PIT feature eligible. See [ADR-001](ADR-001-PREDICTION-ENGINE-ARCHITECTURE.md) and [Prediction Engine Contracts](PREDICTION_ENGINE_CONTRACTS.md).
