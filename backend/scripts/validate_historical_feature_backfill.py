"""Read-only end-to-end validator for the seven historical feature backfill runs."""
from __future__ import annotations

import json
import os

import psycopg

from app.providers.historical_validation import validate_competition_import

DATABASE_NAME = "veltrix_ai_analyst"
EXPECTED_SCOPES = {
    "3118717965",
    "522514093",
    "4160026622",
    "3614399544",
    "686337048",
    "3405541143",
    "4212821298",
}


def main() -> int:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL_REQUIRED")
    reports = []
    with psycopg.connect(dsn) as connection:
        if connection.info.dbname != DATABASE_NAME:
            raise RuntimeError("DATABASE_IDENTITY_MISMATCH")
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            runs = connection.execute(
                """
                SELECT id, scope_value
                FROM veltrix_ai_analyst.import_runs
                WHERE import_type = 'historical_feature_backfill'
                  AND id BETWEEN 19 AND 25
                ORDER BY id
                """
            ).fetchall()
            if len(runs) != 7 or {str(scope) for _, scope in runs} != EXPECTED_SCOPES:
                raise RuntimeError("HISTORICAL_BACKFILL_RUN_SCOPE_MISMATCH")
            for run_id, scope in runs:
                reports.append(
                    validate_competition_import(connection, int(run_id), str(scope))
                )
    if len(reports) != 7 or any(not report["passed"] for report in reports):
        raise RuntimeError("HISTORICAL_BACKFILL_VALIDATION_FAILED")
    print(
        json.dumps(
            {
                "status": "ALL_SEVEN_HISTORICAL_IMPORTS_VALIDATED",
                "runs": reports,
                "database_writes": 0,
                "provider_requests": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
