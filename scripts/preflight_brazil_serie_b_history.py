"""Read-only preflight for the gated Brazil Serie B historical importer.

This command performs PostgreSQL SELECTs only. It never calls 5DollarFootballAPI,
creates import runs, reserves quota, or writes fixture data.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlsplit

import psycopg

EXPECTED_DATABASE = "veltrix_ai_analyst"
APPROVAL_ID = "approval-5dollar-community-fixtures-2026-11-12"
COMPETITION_ID = "522514093"
PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"

EXPECTED_MIGRATIONS = {
    "001_provenance_ingestion.sql": "11516fc36e78cca9d0a47f677e2ab451fc1beb6b899d74f9f007b979c98ebf07",
    "002_source_observation_sightings.sql": "a5389d81f7816837c0dfedd35784f8834c4484c13a946ea166dd6d55615c4285",
    "003_import_request_reservations.sql": "fa841cf34fe836f3d7d7251edd36e4d5e619d185f6adf4585ac851ebcdc0560e",
    "004_ingestion_quarantine.sql": "567fc4c0f85e0b228591bda0888b76a82b92cb799b129197d8e4aae3404997cf",
}


def _items(value: object) -> set[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return set()
    if not isinstance(value, list):
        return set()
    return {str(item) for item in value}


def main() -> int:
    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    expected_name = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_name != EXPECTED_DATABASE:
        print("PREFLIGHT_FAILED:CONFIGURATION_MISSING_OR_INVALID")
        return 2

    parsed = urlsplit(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        print("PREFLIGHT_FAILED:INVALID_DATABASE_URL_SCHEME")
        return 2
    if parsed.path.lstrip("/").split("?", 1)[0] != EXPECTED_DATABASE:
        print("PREFLIGHT_FAILED:DATABASE_URL_TARGET_MISMATCH")
        return 2

    checks: dict[str, str] = {}
    try:
        with psycopg.connect(database_url, connect_timeout=10) as connection:
            connection.execute("SET TRANSACTION READ ONLY")
            identity = connection.execute(
                "SELECT current_database(), current_setting('server_version')"
            ).fetchone()
            if identity[0] != EXPECTED_DATABASE:
                raise RuntimeError("DATABASE_IDENTITY_MISMATCH")
            checks["database_identity"] = "PASS"
            checks["postgresql"] = str(identity[1]).split()[0]

            schema_exists = connection.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'veltrix_ai_analyst')"
            ).fetchone()[0]
            if not schema_exists:
                raise RuntimeError("PROJECT_SCHEMA_MISSING")
            checks["project_schema"] = "PASS"

            applied = dict(
                connection.execute(
                    "SELECT version, trim(checksum) FROM public.schema_migrations"
                ).fetchall()
            )
            mismatches = [
                version
                for version, checksum in EXPECTED_MIGRATIONS.items()
                if applied.get(version) != checksum
            ]
            if mismatches:
                raise RuntimeError("MIGRATION_CHECKSUM_OR_VERSION_MISMATCH")
            checks["migrations_001_004"] = "PASS"

            approval = connection.execute(
                """
                SELECT a.status, a.scope_type, a.scope_values, a.data_types,
                       a.commercial_use_allowed, a.attribution_required,
                       a.raw_redistribution_allowed, a.valid_from, a.valid_until,
                       COALESCE(
                           (
                               SELECT event.status
                               FROM veltrix_ai_analyst.source_approval_status_events event
                               WHERE event.approval_id = a.approval_id
                                 AND event.effective_at <= statement_timestamp()
                               ORDER BY event.effective_at DESC, event.id DESC
                               LIMIT 1
                           ),
                           a.status
                       ) AS effective_status
                FROM veltrix_ai_analyst.source_approvals a
                WHERE a.approval_id = %s
                  AND a.provider = %s
                  AND a.source_id = %s
                """,
                (APPROVAL_ID, PROVIDER, SOURCE_ID),
            ).fetchone()
            if approval is None:
                raise RuntimeError("SOURCE_APPROVAL_MISSING")
            (
                status, scope_type, scope_values, data_types,
                commercial, attribution, raw_redistribution,
                valid_from, valid_until, effective_status,
            ) = approval
            if (
                status != "APPROVED"
                or effective_status != "APPROVED"
                or scope_type != "competition_id"
                or COMPETITION_ID not in _items(scope_values)
                or not {"fixtures_and_results", "competition_catalogue", "team_catalogue"}.issubset(_items(data_types))
                or commercial
                or not attribution
                or raw_redistribution
                or valid_from > connection.execute("SELECT statement_timestamp()").fetchone()[0]
                or (valid_until is not None and valid_until <= connection.execute("SELECT statement_timestamp()").fetchone()[0])
            ):
                raise RuntimeError("SOURCE_APPROVAL_SCOPE_OR_VALIDITY_MISMATCH")
            checks["source_approval"] = "PASS"

            open_quarantines = connection.execute(
                """
                SELECT COUNT(*)
                FROM veltrix_ai_analyst.ingestion_quarantine
                WHERE provider = %s AND source_id = %s AND resolved_at IS NULL
                """,
                (PROVIDER, SOURCE_ID),
            ).fetchone()[0]
            if int(open_quarantines) != 0:
                raise RuntimeError("UNRESOLVED_PROVIDER_QUARANTINE_PRESENT")
            checks["unresolved_quarantines"] = "0"

            active_runs = connection.execute(
                """
                SELECT COUNT(*)
                FROM veltrix_ai_analyst.import_runs
                WHERE provider = %s AND source_id = %s
                  AND status IN ('PLANNED', 'RUNNING')
                """,
                (PROVIDER, SOURCE_ID),
            ).fetchone()[0]
            if int(active_runs) != 0:
                raise RuntimeError("ACTIVE_IMPORT_RUN_ALREADY_EXISTS")
            checks["active_import_runs"] = "0"

    except Exception as exc:
        # Deliberately suppress exception text: driver exceptions can contain connection data.
        code = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        print(f"PREFLIGHT_FAILED:{code}")
        return 1

    print("PREFLIGHT_PASSED")
    for name, value in checks.items():
        print(f"{name}={value}")
    print("provider_http_requests=0")
    print("database_writes=0")
    print("fixture_rows_written=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
