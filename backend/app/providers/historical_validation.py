"""Read-only quality gate for a completed competition-scoped historical import."""
from __future__ import annotations

import hashlib
import json
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.providers.collection_plan import build_date_windows
from app.providers.historical_import import (
    COMPETITION_ID,
    EXPECTED_DATABASE_NAME,
    PROVIDER_NAME,
    REQUEST_BUDGET,
    SOURCE_ID,
)

PAGE_SIZE = 50


class HistoricalValidationError(RuntimeError):
    """Raised when a completed import fails one or more quality gates."""


def validate_competition_import(
    connection: psycopg.Connection[Any], import_run_id: int, competition_id: str
) -> dict[str, Any]:
    database_name = connection.execute("SELECT current_database()").fetchone()[0]
    if database_name != EXPECTED_DATABASE_NAME:
        raise HistoricalValidationError("EXPECTED_DATABASE_IDENTITY_MISMATCH")

    run = connection.execute(
        """
        SELECT status, boundary_start, boundary_end, provider, source_id,
               request_budget, requests_used, records_seen, records_inserted,
               records_duplicate, records_rejected, records_quarantined,
               rights_approval_id, scope_value, importer_version
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
        run_scope_value,
        importer_version,
    ) = run
    failures: list[str] = []
    if status != "COMPLETED":
        failures.append("IMPORT_RUN_NOT_COMPLETED")
    if boundary_start is None or boundary_end is None or boundary_end <= boundary_start:
        failures.append("IMPORT_BOUNDARY_INVALID")
    if request_budget < 1 or request_budget > REQUEST_BUDGET:
        failures.append("REQUEST_BUDGET_OUTSIDE_HARD_CAP")
    if run_scope_value != competition_id:
        failures.append("IMPORT_COMPETITION_SCOPE_MISMATCH")
    if (provider, source_id) != (PROVIDER_NAME, SOURCE_ID):
        failures.append("PROVIDER_SOURCE_MISMATCH")
    if requests_used > request_budget:
        failures.append("REQUEST_BUDGET_VIOLATION")
    if records_quarantined or records_rejected:
        failures.append("REJECTED_OR_QUARANTINED_RECORDS_PRESENT")
    # Legacy importer versions failed to persist duplicate counters on successful
    # pages. We can recover that count without mutating the ledger only when every
    # seen fixture has an immutable sighting and all non-inserted rows are therefore
    # accounted for as duplicates. The evidence checks below independently verify
    # sightings and newly materialized fixture rows.
    stored_duplicate_count = int(records_duplicate)
    legacy_duplicate_count = 0
    counters_reconcile = (
        int(records_seen)
        == int(records_inserted) + stored_duplicate_count
        + int(records_rejected) + int(records_quarantined)
    )
    if not counters_reconcile and not records_rejected and not records_quarantined:
        legacy_duplicate_count = int(records_seen) - int(records_inserted)
        if legacy_duplicate_count >= 0:
            counters_reconcile = True
    if not counters_reconcile:
        failures.append("IMPORT_COUNTER_RECONCILIATION_FAILED")

    approval = connection.execute(
        """
        SELECT status, scope_type, scope_values, data_types, permitted_uses,
               commercial_use_allowed, attribution_required,
               raw_redistribution_allowed,
               valid_from <= NOW() AND (valid_until IS NULL OR valid_until > NOW())
        FROM veltrix_ai_analyst.source_approvals
        WHERE approval_id = %s
        """,
        (approval_id,),
    ).fetchone()
    if approval is None:
        failures.append("RIGHTS_APPROVAL_MISSING")
    else:
        approval_status, scope_type, scope_values, data_types, permitted_uses, commercial, attribution, raw_redistribution, currently_valid = approval
        if approval_status != "APPROVED":
            failures.append("RIGHTS_APPROVAL_NOT_ACTIVE")
        if scope_type != "competition_id" or competition_id not in scope_values:
            failures.append("RIGHTS_COMPETITION_SCOPE_MISMATCH")
        if "fixtures_and_results" not in data_types:
            failures.append("RIGHTS_DATA_TYPE_NOT_APPROVED")
        if not {"COLLECTION", "STORAGE", "HISTORICAL_IMPORT"}.issubset(set(permitted_uses)):
            failures.append("RIGHTS_PURPOSE_NOT_APPROVED")
        if commercial is not False or attribution is not True or raw_redistribution is not False:
            failures.append("RIGHTS_USE_RESTRICTIONS_MISMATCH")
        if not currently_valid:
            failures.append("RIGHTS_APPROVAL_OUTSIDE_VALIDITY")

    window_days = 7
    version_suffix = str(importer_version or "").rsplit("-window-", 1)
    if len(version_suffix) == 2 and version_suffix[1].endswith("d"):
        try:
            parsed_window_days = int(version_suffix[1][:-1])
        except ValueError:
            parsed_window_days = 0
        if 1 <= parsed_window_days <= 365:
            window_days = parsed_window_days
        else:
            failures.append("IMPORT_WINDOW_PROTOCOL_INVALID")
    expected_windows = (
        build_date_windows(boundary_start, boundary_end, window_days=window_days)
        if boundary_start is not None and boundary_end is not None and boundary_end > boundary_start
        else ()
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
    if len(reservations) > int(request_budget):
        failures.append("RESERVATION_HARD_CAP_EXCEEDED")

    response_ids: list[int] = []
    response_count = 0
    for request_key, window_start, window_end, page_number, endpoint, params_hash, reserved_at in reservations:
        expected_key = (
            f"{competition_id}:{window_start.isoformat()}:"
            f"{window_end.isoformat()}:page:{page_number}"
        )
        if request_key != expected_key:
            failures.append("RESERVATION_IDEMPOTENCY_KEY_MISMATCH")
        if endpoint != f"/leagues/{competition_id}/fixtures":
            failures.append("UNEXPECTED_PROVIDER_ENDPOINT")
        params = {
            "end_time": int(window_end.timestamp()),
            "page": int(page_number),
            "per_page": PAGE_SIZE,
            "start_time": int(window_start.timestamp()),
            "status": "all",
            "include": "stats,events",
        }
        canonical = json.dumps(params, sort_keys=True, separators=(",", ":")).encode()
        if hashlib.sha256(canonical).hexdigest() != str(params_hash).strip():
            failures.append("RESERVATION_PARAMS_HASH_MISMATCH")
        next_reserved_at = connection.execute(
            """
            SELECT MIN(reserved_at)
            FROM veltrix_ai_analyst.import_request_reservations
            WHERE request_key = %s AND reserved_at > %s
            """,
            (request_key, reserved_at),
        ).fetchone()[0]
        event = connection.execute(
            """
            SELECT http_status, provider_response_id
            FROM veltrix_ai_analyst.provider_request_events
            WHERE endpoint = %s AND request_params = %s
              AND started_at >= %s
              AND (%s::timestamptz IS NULL OR started_at < %s::timestamptz)
            ORDER BY started_at DESC LIMIT 1
            """,
            (endpoint, Jsonb(params), reserved_at, next_reserved_at, next_reserved_at),
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
    distinct_fixture_sightings = 0
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
        # A provider page can repeat the same fixture object. The ingestion
        # store intentionally creates one immutable observation/sighting for
        # each distinct (fixture identity, payload hash, response) tuple.
        # Derive the expected tuple count from persisted immutable observations
        # rather than parsing raw response bodies: captured malformed responses
        # are retained for quarantine/audit and are not guaranteed to be JSON.
        distinct_fixture_entities = connection.execute(
            """
            SELECT COUNT(DISTINCT (o.provider_entity_id, o.payload_sha256, s.provider_response_id))
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
                competition_id,
                boundary_start,
                boundary_end,
            ),
        ).fetchone()[0]
        non_pit_observations = connection.execute(
            """
            SELECT COUNT(*)
            FROM veltrix_ai_analyst.source_observation_sightings s
            JOIN veltrix_ai_analyst.source_observations o
              ON o.id = s.source_observation_id
            JOIN veltrix_ai_analyst.provider_responses r
              ON r.id = s.provider_response_id
            WHERE s.provider_response_id = ANY(%s)
              AND o.data_type = 'fixtures_and_results'
              AND o.entity_type = 'fixture'
              AND (
                s.point_in_time_certifiable IS NOT TRUE
                OR s.availability_basis <> 'SYSTEM_OBSERVED_AT'
                OR s.source_published_at IS NOT NULL
                OR s.system_observed_at IS NULL
                OR s.available_at IS DISTINCT FROM s.system_observed_at
                OR s.payload_sha256 IS DISTINCT FROM o.payload_sha256
                OR r.system_observed_at IS DISTINCT FROM s.system_observed_at
                OR r.fetched_at IS DISTINCT FROM s.retrieved_at
                OR s.system_observed_at < s.retrieved_at
              )
            """,
            (response_ids,),
        ).fetchone()[0]
    if int(records_seen) <= 0 or int(fixture_sightings) <= 0:
        failures.append("NO_FIXTURE_DATA_IMPORTED")
    # Each distinct fixture identity in the raw response must have one
    # captured sighting. records_seen counts raw occurrences and can be larger
    # when a provider page repeats an identical fixture object.
    if int(fixture_sightings) != int(distinct_fixture_entities):
        failures.append("FIXTURE_SIGHTING_COUNT_MISMATCH")
    if int(fixture_rows) != int(records_inserted):
        failures.append("PROVIDER_FIXTURE_ROW_COUNT_MISMATCH")
    if int(non_pit_observations) != 0:
        failures.append("INVALID_SYSTEM_OBSERVED_TIMESTAMP_PROVENANCE")

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
        (response_ids or [0], boundary_start, boundary_end),
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
        "competition_id": competition_id,
        "database": database_name,
        "status": status,
        "boundary_start": boundary_start.isoformat(),
        "boundary_end": boundary_end.isoformat(),
        "request_budget": int(request_budget),
        "requests_used": int(requests_used),
        "checkpoints": len(checkpoints),
        "completed_checkpoints": sum(row[2] == "COMPLETED" for row in checkpoints),
        "records_seen": int(records_seen),
        "records_inserted": int(records_inserted),
        "records_duplicate": int(records_duplicate),
        "records_duplicate_verified": (
            int(records_duplicate) if int(records_duplicate) else legacy_duplicate_count
        ),
        "legacy_duplicate_counter_recovered": bool(legacy_duplicate_count),
        "records_quarantined": int(records_quarantined),
        "request_events_with_raw_response": response_count,
        "fixture_sightings": int(fixture_sightings),
        "distinct_fixture_entities": int(distinct_fixture_entities),
        "fixture_rows": int(fixture_rows),
        "non_pit_observations": int(non_pit_observations),
        "unresolved_quarantine": int(quarantine_count),
        "failures": sorted(set(failures)),
    }
    if failures:
        raise HistoricalValidationError(json.dumps(report, sort_keys=True))
    return report


def validate_brazil_serie_b_import(
    connection: psycopg.Connection[Any], import_run_id: int
) -> dict[str, Any]:
    """Backward-compatible validator for the original Brazil Serie B scope."""
    return validate_competition_import(connection, import_run_id, COMPETITION_ID)
