"""Production readiness probe for the public prediction service.

This endpoint is operational metadata only. It never returns credentials, raw
database errors, prediction content, or model diagnostics.
"""
from __future__ import annotations

import os

import psycopg
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/ready", tags=["operations"])

DATABASE_NAME = "veltrix_ai_analyst"
REQUIRED_MIGRATIONS = (
    "012_database_observed_timestamps.sql",
    "013_target_fixture_pre_match_gate.sql",
    "014_prediction_publication_storage.sql",
)
PREDICTION_RELATIONS = (
    "veltrix_ai_analyst.published_predictions",
    "veltrix_ai_analyst.published_prediction_markets",
)


@router.get("")
def readiness() -> JSONResponse:
    """Report whether the database schema required by V1 is ready."""
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "veltrix-ai-analyst-api",
                "checks": {
                    "database": "not_configured",
                    "migrations": "unavailable",
                    "prediction_storage": "unavailable",
                },
            },
        )

    try:
        with psycopg.connect(dsn) as connection:
            if connection.info.dbname != DATABASE_NAME:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "service": "veltrix-ai-analyst-api",
                        "checks": {
                            "database": "wrong_database",
                            "migrations": "unavailable",
                            "prediction_storage": "unavailable",
                        },
                    },
                )
            row = connection.execute(
                """
                SELECT
                    current_database(),
                    COALESCE(
                        (
                            SELECT array_agg(version)
                            FROM public.schema_migrations
                            WHERE version = ANY(%s)
                        ),
                        ARRAY[]::text[]
                    ),
                    to_regclass(%s) IS NOT NULL,
                    to_regclass(%s) IS NOT NULL
                """,
                (list(REQUIRED_MIGRATIONS), *PREDICTION_RELATIONS),
            ).fetchone()
    except (psycopg.Error, ValueError):
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "veltrix-ai-analyst-api",
                "checks": {
                    "database": "unavailable",
                    "migrations": "unavailable",
                    "prediction_storage": "unavailable",
                },
            },
        )

    database_ok = row[0] == DATABASE_NAME
    migrations_ok = set(row[1] or ()) == set(REQUIRED_MIGRATIONS)
    storage_ok = bool(row[2]) and bool(row[3])
    ready = database_ok and migrations_ok and storage_ok
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "service": "veltrix-ai-analyst-api",
            "checks": {
                "database": "connected" if database_ok else "wrong_database",
                "migrations": "current" if migrations_ok else "pending",
                "prediction_storage": "available" if storage_ok else "pending",
            },
        },
    )
