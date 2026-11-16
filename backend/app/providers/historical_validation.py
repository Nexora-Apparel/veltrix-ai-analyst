"""Read-only quality gate for a completed Brazil Serie B historical import."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.providers.collection_plan import build_date_windows
from app.providers.historical_import import (
    BOUNDARY_END,
    BOUNDARY_START,
    COMPETITION_ID,
    EXPECTED_DATABASE_NAME,
    PROVIDER_NAME,
    REQUEST_BUDGET,
    SOURCE_ID,
)

PAGE_SIZE = 100


class HistoricalValidationError(RuntimeError):
    """Raised when a completed import fails one or more quality gates."""


def validate_brazil_serie_b_import(
    connection: psycopg.Connection[Any], import_run_id: int
) -> dict[str, Any]:
    database_name = connection.execute("SELECT current_database()").fetchone()[0]
    if database_name != EXPECTED_DATABASE_NAME:
        raise HistoricalValidationError("EXPECTED_DATABASE_IDENTITY_MISMATCH")

    run = connection.execute(
        """
        SELECT status, boundary_start, boundary_end, provider, source_id,
               request_budget, requests_used, records_seen, records_inserted,
               records_duplicate, records_rejected, records_quarantined,
               rights_approval_id
        FROM veltrix_ai_analyst.import_runs
        WHERE id = %s
        """,
        (import_run_id,),
    ).fetchone()
    if run is None:
        raise HistoricalValidationError("IMPORT_RUN_NOT_FOUND")

    (
        status,
        boundary_start,
        boundary_end,
        provider,
        source_id,
        request_budget,
        requests_used,
        records_seen,
        records_inserted,
        records_duplicate,
        records_rejected,
        records_quarantined,
        approval_id,
    ) = run
    failures: list[str] = []
    if status != "COMPLETED":
        failures.append("IMPORT_RUN_NOT_COMPLETED")
    if (boundary_start, boundary_end) != (BOUNDARY_START, BOUNDARY_END):
        failures.append("IMPORT_BOUNDARY_MISMATCH")
    if (provider, source_id) != (PROVIDER_NAME, SOURCE_ID):
        failures.append("PROVIDER_SOURCE_MISMATCH")
    if request_budget != REQUEST_BUDGET or requests_used > REQUEST_BUDGET:
        failures.append("REQUEST_BUDGET_VIOLATION")
    if records_quarantined or records_rejected:
        failures.append("REJECTED_OR_QUARANTINED_RECORDS_PRESENT")
    if records_seen != records_inserted + records_duplicate + records_rejected + records_quarantined:
        failures.append("IMPORT_COUNTER_RECONCILIATION_FAILED")

    expected_windows = build_date_windows(
        BOUNDARY_START, BOUNDARY_END, window_days=7
    )
    checkpoints = connection.execute(
        """
        SELECT window_start, window_end, status, records_seen, records_inserted,
               records_duplicate, records_rejected, records_quarantined,
               requests_used
        FROM veltrix_ai_analyst.import_checkpoints
        WHERE import_run_id = %s
        ORDER BY window_start
        """,
        (import_run_id,),
    ).fetchall()
    if len(checkpoints) != len(expected_windows):
        failures.append("CHECKPOINT_COUNT_MISMATCH")
    if len(checkpoints) == len(expected_windows):
        for actual, expected in zip(checkpoints, expected_windows, strict=True):
            if (actual[0], actual[1]) != (expected.start_at, expected.end_at):
                failures.append("CHECKPOINT_BOUNDARY_MISMATCH")
                break
        if any(row[2] != "COMPLETED" for row in checkpoints):
            failures.append("INCOMPLETE_CHECKPOINTS")
        if sum(int(row[8]) for row in checkpoints) != int(requests_used):
            failures.append("CHECKPOINT_REQUEST_TOTAL_MISMATCH")
        if sum(int(row[3]) for row in checkpoints) != int(records_seen):
            failures.append("CHECKPOINT_RECORD_TOTAL_MISMATCH")

    reservations = connection.execute(
        """
        SELECT request_key, window_start, window_end, page_number, endpoint,
               params_sha256, reserved_at
        FROM veltrix_ai_analyst.import_request_reservations
        WHERE import_run_id = %s
        ORDER BY window_start, page_number
        """,
        (import_run_id,),
    ).fetchall()
    if len(reservations) != requests_used:
        failures.append("RESERVATION_COUNT_MISMATCH")
    if len(reservations) > REQUEST_BUDGET:
        failures.append("RESERVATION_HARD_CAP_EXCEEDED")

    response_ids: list[int] = []
    response_count = 0
    for request_key, window_start, window_end, page_number, endpoint, params_hash, reserved_at in reservations:
        expected_key = (
            f"{COMPETITION_ID}:{window_start.isoformat()}:"
            f"{window_end.isoformat()}:page:{page_number}"
        )
        if request_key != expected_key:
            failures.append("RESERVATION_IDEMPOTENCY_KEY_MISMATCH")
        if endpoint != f"/leagues/{COMPETITION_ID}/fixtures":
            failures.append("UNEXPECTED_PROVIDER_ENDPOINT")
        params = {
            "end_time": int(window_end.timestamp()),
            "page": int(page_number),
            "per_page": PAGE_SIZE,
            "start_time": int(window_start.timestamp()),
            "status": "all",
        }
        canonical = json.dumps(params, sort_keys=True, separators=(",", ":")).encode()
        if hashlib.sha256(canonical).hexdigest() != str(params_hash).strip():
            failures.append("RESERVATION_PARAMS_HASH_MISMATCH")
        event = connection.execute(
            """
            SELECT http_status, provider_response_id
            FROM veltrix_ai_analyst.provider_request_events
            WHERE endpoint = %s AND request_params = %s
              AND started_at >= %s
            ORDER BY started_at DESC LIMIT 1
            """,
            (endpoint, Jsonb(params), reserved_at),
        ).fetchone()
        if event is None:
            failures.append("REQUEST_EVENT_MISSING")
            continue
        if event[0] is None or not 200 <= int(event[0]) < 300:
            failures.append("NON_SUCCESS_HTTP_RESPONSE")
        if event[1] is None:
            failures.append("RAW_PROVIDER_RESPONSE_MISSING")
            continue
        response = connection.execute(
            """
            SELECT response_sha256, raw_body
            FROM veltrix_ai_analyst.provider_responses
            WHERE id = %s
            """,
            (event[1],),
        ).fetchone()
        if response is None:
            failures.append("PROVIDER_RESPONSE_RECORD_MISSING")
            continue
        body_hash = hashlib.sha256(bytes(response[1])).hexdigest()
        if body_hash != str(response[0]).strip():
            failures.append("PROVIDER_RESPONSE_CHECKSUM_MISMATCH")
        response_ids.append(int(event[1]))
        response_count += 1

    fixture_sightings = 0
    fixture_rows = 0
    non_pit_observations = 0
    if response_ids:
        fixture_sightings = connection.execute(
            """
            SELECT COUNT(*)
            FROM veltrix_ai_analyst.source_observation_sightings s
            JOIN veltrix_ai_analyst.source_observations o
              ON o.id = s.source_observation_id
            WHERE s.provider_response_id = ANY(%s)
              AND o.rights_approval_id = %s
              AND o.data_type = 'fixtures_and_results'
              AND o.entity_type = 'fixture'
            """,
            (response_ids, approval_id),
        ).fetchone()[0]
        fixture_rows = connection.execute(
            """
            SELECT COUNT(DISTINCT f.id)
            FROM veltrix_ai_analyst.provider_fixtures f
            JOIN veltrix_ai_analyst.source_observation_sightings s
              ON s.source_observation_id = f.source_observation_id
            WHERE s.provider_response_id = ANY(%s)
              AND f.provider = %s AND f.source_id = %s
              AND f.provider_competition_id = %s
              AND f.kickoff_at >= %s AND f.kickoff_at < %s
            """,
            (
                response_ids,
                PROVIDER_NAME,
                SOURCE_ID,
                COMPETITION_ID,
                BOUNDARY_START,
                BOUNDARY_END,
            ),
        ).fetchone()[0]
        non_pit_observations = connection.execute(
            """
            SELECT COUNT(*)
            FROM veltrix_ai_analyst.source_observation_sightings s
            JOIN veltrix_ai_analyst.source_observations o
              ON o.id = s.source_observation_id
            WHERE s.provider_response_id = ANY(%s)
              AND o.data_type = 'fixtures_and_results'
              AND o.entity_type = 'fixture'
              AND (
                s.point_in_time_certifiable IS TRUE
                OR s.availability_basis <> 'RETRIEVED_AT_ONLY'
                OR s.available_at IS NOT NULL
                OR s.source_published_at IS NOT NULL
              )
            """,
            (response_ids,),
        ).fetchone()[0]
    if int(fixture_sightings) != int(records_inserted):
        failures.append("FIXTURE_SIGHTING_COUNT_MISMATCH")
    if int(non_pit_observations) != 0:
        failures.append("UNVERIFIED_POINT_IN_TIME_FEATURES_PRESENT")

    bad_fixtures = connection.execute(
        """
        SELECT COUNT(*)
        FROM veltrix_ai_analyst.provider_fixtures f
        JOIN veltrix_ai_analyst.source_observation_sightings s
          ON s.source_observation_id = f.source_observation_id
        WHERE s.provider_response_id = ANY(%s)
          AND (
            f.kickoff_at < %s OR f.kickoff_at >= %s
            OR (f.status = 'FINISHED' AND (f.home_goals IS NULL OR f.away_goals IS NULL))
          )
        """,
        (response_ids or [0], BOUNDARY_START, BOUNDARY_END),
    ).fetchone()[0]
    if int(bad_fixtures) != 0:
        failures.append("FIXTURE_DATA_QUALITY_FAILURE")

    quarantine_count = connection.execute(
        """
        SELECT COUNT(*) FROM veltrix_ai_analyst.ingestion_quarantine
        WHERE import_run_id = %s AND resolved_at IS NULL
        """,
        (import_run_id,),
    ).fetchone()[0]
    if quarantine_count:
        failures.append("UNRESOLVED_QUARANTINE_PRESENT")

    report = {
        "passed": not failures,
        "import_run_id": import_run_id,
        "database": database_name,
        "status": status,
        "boundary_start": BOUNDARY_START.isoformat(),
        "boundary_end": BOUNDARY_END.isoformat(),
        "request_budget": int(request_budget),
        "requests_used": int(requests_used),
        "checkpoints": len(checkpoints),
        "completed_checkpoints": sum(row[2] == "COMPLETED" for row in checkpoints),
        "records_seen": int(records_seen),
        "records_inserted": int(records_inserted),
        "records_duplicate": int(records_duplicate),
        "records_quarantined": int(records_quarantined),
        "request_events_with_raw_response": response_count,
        "fixture_sightings": int(fixture_sightings),
        "fixture_rows": int(fixture_rows),
        "non_pit_observations": int(non_pit_observations),
        "unresolved_quarantine": int(quarantine_count),
        "failures": sorted(set(failures)),
    }
    if failures:
        raise HistoricalValidationError(json.dumps(report, sort_keys=True))
    return report
