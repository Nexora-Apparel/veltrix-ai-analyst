from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta

import httpx
import psycopg
import pytest

from app.db.migrations import apply_migrations
from app.db.request_budget import PostgresRequestBudget
from app.db.store import PostgresIngestionStore
from app.providers import historical_import, historical_validation
from app.providers.collection_plan import DateWindow
from app.providers.five_dollar import FiveDollarFootballProvider
from app.providers.historical_import import (
    IMPORT_APPROVAL,
    FixturePagePersister,
    HistoricalImportError,
    _replay_captured_page,
    run_brazil_serie_b_historical_import,
)


@pytest.fixture
def database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not url or not database:
        pytest.skip("PostgreSQL integration service is not configured")
    apply_migrations(url, expected_database=database)
    return url


def _fixture(fixture_id: int, kickoff: str) -> dict[str, object]:
    return {
        "id": fixture_id,
        "league": {"id": 522514093, "name": "Brazil Serie B", "season": "2026"},
        "teams": {
            "home": {"id": 1101, "name": "Home FC"},
            "away": {"id": 1102, "name": "Away FC"},
        },
        "kickoff_utc": kickoff,
        "status": "finished",
        "goals": {"home": 2, "away": 1},
        "corners": {"home": 5, "away": 3},
        "cards": {
            "home": {"yellow": 1, "red": 0},
            "away": {"yellow": 2, "red": 0},
        },
    }


def test_importer_uses_the_exact_registered_community_approval() -> None:
    assert IMPORT_APPROVAL.approval_id == "approval-5dollar-community-fixtures-2026-11-12"
    assert IMPORT_APPROVAL.provider == "5DollarFootballAPI"
    assert IMPORT_APPROVAL.source_id == "5dollarfootballapi"
    assert "522514093" in IMPORT_APPROVAL.scope_values
    assert "fixtures_and_results" in IMPORT_APPROVAL.data_types


def test_historical_import_persists_page_evidence_and_checkpoints(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION", "true")
    monkeypatch.setattr(historical_import, "EXPECTED_DATABASE_NAME", "veltrix_test")
    monkeypatch.setattr(historical_validation, "EXPECTED_DATABASE_NAME", "veltrix_test")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        start = int(request.url.params["start_time"])
        kickoff = datetime.fromtimestamp(start + 3600, tz=UTC).isoformat()
        fixture_id = 700000 + len(requests)
        return httpx.Response(
            200,
            json={
                "success": 1,
                "data": [_fixture(fixture_id, kickoff)],
                "pagination": {
                    "page": int(request.url.params["page"]),
                    "per_page": 100,
                    "count": 1,
                    "has_more": False,
                },
            },
            headers={"X-Request-Id": f"mock-request-{fixture_id}"},
        )

    provider = FiveDollarFootballProvider(
        api_key="test-only-key",
        transport=httpx.MockTransport(handler),
    )
    run_id = asyncio.run(
        run_brazil_serie_b_historical_import(
            database_url,
            api_key="test-only-key",
            execute=True,
            approval=IMPORT_APPROVAL,
            provider=provider,
        )
    )

    assert len(requests) == 34
    assert all(request.url.path == "/v1/leagues/522514093/fixtures" for request in requests)
    assert all(request.url.params["per_page"] == "100" for request in requests)

    with psycopg.connect(database_url) as connection:
        run = connection.execute(
            """
            SELECT status, request_budget, requests_used, records_seen,
                   records_inserted, rights_approval_id
            FROM veltrix_ai_analyst.import_runs WHERE id = %s
            """,
            (run_id,),
        ).fetchone()
        checkpoints = connection.execute(
            """
            SELECT COUNT(*), COUNT(*) FILTER (WHERE status = 'COMPLETED'),
                   SUM(requests_used)
            FROM veltrix_ai_analyst.import_checkpoints WHERE import_run_id = %s
            """,
            (run_id,),
        ).fetchone()
        response_count = connection.execute(
            """
            SELECT COUNT(*) FROM veltrix_ai_analyst.provider_responses
            WHERE rights_approval_id = %s
            """,
            (IMPORT_APPROVAL.approval_id,),
        ).fetchone()[0]
        fixture_count = connection.execute(
            """
            SELECT COUNT(*) FROM veltrix_ai_analyst.provider_fixtures
            WHERE rights_approval_id = %s
            """,
            (IMPORT_APPROVAL.approval_id,),
        ).fetchone()[0]
        linked_observations = connection.execute(
            """
            SELECT COUNT(*) FROM veltrix_ai_analyst.source_observations
            WHERE rights_approval_id = %s AND provider_response_id IS NOT NULL
            """,
            (IMPORT_APPROVAL.approval_id,),
        ).fetchone()[0]

        sighting_times = connection.execute(
            """
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE s.available_at IS NOT NULL),
                COUNT(*) FILTER (WHERE s.source_published_at IS NULL),
                COUNT(*) FILTER (
                    WHERE s.availability_basis = 'RETRIEVED_AT_ONLY'
                      AND s.point_in_time_certifiable IS FALSE
                ),
                COUNT(*) FILTER (WHERE s.point_in_time_certifiable IS TRUE)
            FROM veltrix_ai_analyst.source_observation_sightings s
            WHERE s.provider_response_id IN (
                SELECT provider_response_id
                FROM veltrix_ai_analyst.import_request_reservations
                WHERE import_run_id = %s AND provider_response_id IS NOT NULL
            )
            """,
            (run_id,),
        ).fetchone()

    assert run == (
        "COMPLETED",
        40,
        34,
        34,
        34,
        IMPORT_APPROVAL.approval_id,
    )
    assert checkpoints == (34, 34, 34)
    assert response_count == 34
    assert fixture_count == 34
    assert linked_observations >= 34
    assert sighting_times[0] > 0
    assert sighting_times[1] == sighting_times[0]  # exact system-observed availability
    assert sighting_times[2] == sighting_times[0]  # provider exposes no verified publication time
    assert sighting_times[3] == sighting_times[0]  # retrieval-only evidence is not PIT
    assert sighting_times[4] == 0
    with psycopg.connect(database_url) as connection:
        report = historical_validation.validate_brazil_serie_b_import(connection, run_id)
    assert report["passed"] is True
    assert report["checkpoints"] == 34
    assert report["request_events_with_raw_response"] == 34
    assert report["fixture_sightings"] == 34


def test_live_import_requires_both_explicit_execution_gates(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION", raising=False)
    with pytest.raises(HistoricalImportError, match="LIVE_COLLECTION_NOT_EXPLICITLY_ENABLED"):
        asyncio.run(
            run_brazil_serie_b_historical_import(
                database_url,
                api_key="test-only-key",
                execute=False,
                approval=IMPORT_APPROVAL,
            )
        )



def test_malformed_provider_page_is_saved_and_quarantined(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION", "true")
    monkeypatch.setattr(historical_import, "EXPECTED_DATABASE_NAME", "veltrix_test")
    monkeypatch.setattr(historical_validation, "EXPECTED_DATABASE_NAME", "veltrix_test")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b'{"success":1,"data":',
            headers={
                "Content-Type": "application/json",
                "X-Request-Id": "malformed-page-request",
            },
        )

    provider = FiveDollarFootballProvider(
        api_key="test-only-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(HistoricalImportError, match="COLLECTION_PAUSED:ProviderAPIError"):
        asyncio.run(
            run_brazil_serie_b_historical_import(
                database_url,
                api_key="test-only-key",
                execute=True,
                approval=IMPORT_APPROVAL,
                provider=provider,
            )
        )

    with psycopg.connect(database_url) as connection:
        run_id = connection.execute(
            """
            SELECT id FROM veltrix_ai_analyst.import_runs
            WHERE rights_approval_id = %s
            ORDER BY id DESC LIMIT 1
            """,
            (IMPORT_APPROVAL.approval_id,),
        ).fetchone()[0]
        run = connection.execute(
            """
            SELECT status, request_budget, requests_used, records_seen,
                   records_quarantined
            FROM veltrix_ai_analyst.import_runs WHERE id = %s
            """,
            (run_id,),
        ).fetchone()
        quarantine = connection.execute(
            """
            SELECT reason_code, http_status, provider_response_id, response_sha256
            FROM veltrix_ai_analyst.ingestion_quarantine
            WHERE import_run_id = %s
            """,
            (run_id,),
        ).fetchone()
        raw_body = connection.execute(
            """
            SELECT raw_body FROM veltrix_ai_analyst.provider_responses
            WHERE request_id = 'malformed-page-request'
            """
        ).fetchone()[0]

    assert run == ("PAUSED", 40, 1, 1, 1)
    assert quarantine is not None
    assert quarantine[0] == "PAGE_PROVIDERAPIERROR"
    assert quarantine[1] == 200
    assert quarantine[2] is not None
    assert quarantine[3] is not None
    assert bytes(raw_body) == b'{"success":1,"data":'
    with (
        psycopg.connect(database_url) as connection,
        pytest.raises(
            historical_validation.HistoricalValidationError,
            match="IMPORT_RUN_NOT_COMPLETED",
        ),
    ):
        historical_validation.validate_brazil_serie_b_import(connection, run_id)


def test_resume_replays_reserved_response_without_repeating_provider_http(
    database_url: str,
) -> None:
    window = DateWindow(
        start_at=datetime(2026, 8, 29, tzinfo=UTC),
        end_at=datetime(2026, 9, 5, tzinfo=UTC),
    )
    now = datetime.now(UTC)
    params = {
        "start_time": int(window.start_at.timestamp()),
        "end_time": int(window.end_at.timestamp()),
        "status": "all",
        "page": 1,
        "per_page": 100,
    }
    endpoint = "/leagues/522514093/fixtures"
    request_key = (
        f"522514093:{window.start_at.isoformat()}:{window.end_at.isoformat()}:page:1"
    )
    with psycopg.connect(database_url) as connection:
        store = PostgresIngestionStore(connection)
        run_id = store.create_import_run(
            IMPORT_APPROVAL,
            scope_value="522514093",
            data_type="fixtures_and_results",
            import_type="historical_backfill",
            boundary_start=historical_import.BOUNDARY_START,
            boundary_end=historical_import.BOUNDARY_END,
            request_budget=40,
            importer_version="replay-regression-test",
            started_at=now,
        )
        store.save_checkpoint(
            import_run_id=run_id,
            window_start=window.start_at,
            window_end=window.end_at,
            status="RUNNING",
            cursor_value="1",
        )

    with psycopg.connect(database_url, autocommit=True) as connection:
        reservation = PostgresRequestBudget(connection).reserve(
            import_run_id=run_id,
            request_key=request_key,
            window_start=window.start_at,
            window_end=window.end_at,
            page_number=1,
            endpoint=endpoint,
            request_params=params,
            reserved_at=now,
        )
        assert reservation.created is True
        persister = FixturePagePersister(
            connection,
            import_run_id=run_id,
            approval=IMPORT_APPROVAL,
            window=window,
        )
        body = json.dumps(
            {
                "success": 1,
                "data": [_fixture(99887766, "2026-08-30T12:00:00+00:00")],
                "pagination": {
                    "page": 1,
                    "per_page": 100,
                    "count": 1,
                    "has_more": False,
                },
            },
            separators=(",", ":"),
        ).encode()
        response_id = persister.record_raw_response(
            {
                "request_key": request_key,
                "window_start": window.start_at,
                "window_end": window.end_at,
                "page_number": 1,
                "endpoint": endpoint,
                "request_params": params,
                "request_started_at": now,
                "fetched_at": now,
                "http_status": 200,
                "raw_body": body,
                "response_headers": {"x-request-id": "replay-regression-response"},
            }
        )
        assert response_id is not None
        has_more = _replay_captured_page(
            connection,
            import_run_id=run_id,
            window=window,
            page_number=1,
            persister=persister,
        )
        assert has_more is False

        linked_response = connection.execute(
            """
            SELECT provider_response_id
            FROM veltrix_ai_analyst.import_request_reservations
            WHERE import_run_id = %s AND request_key = %s
            """,
            (run_id, request_key),
        ).fetchone()
        checkpoint = connection.execute(
            """
            SELECT status, records_seen, records_inserted, requests_used
            FROM veltrix_ai_analyst.import_checkpoints
            WHERE import_run_id = %s AND window_start = %s AND window_end = %s
            """,
            (run_id, window.start_at, window.end_at),
        ).fetchone()
        fixture = connection.execute(
            """
            SELECT provider_fixture_id
            FROM veltrix_ai_analyst.provider_fixtures
            WHERE provider = '5DollarFootballAPI'
              AND source_id = '5dollarfootballapi'
              AND provider_fixture_id = '99887766'
            """
        ).fetchone()
        request_count = connection.execute(
            """
            SELECT COUNT(*) FROM veltrix_ai_analyst.provider_request_events
            WHERE provider = '5DollarFootballAPI'
              AND source_id = '5dollarfootballapi'
              AND provider_response_id = %s
            """,
            (response_id,),
        ).fetchone()[0]

    assert linked_response == (response_id,)
    assert checkpoint == ("COMPLETED", 1, 1, 1)
    assert fixture == ("99887766",)
    assert request_count == 1



def test_incremental_import_uses_requested_window_and_small_request_budget(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION", "true")
    monkeypatch.setattr(historical_import, "EXPECTED_DATABASE_NAME", "veltrix_test")
    monkeypatch.setattr(historical_validation, "EXPECTED_DATABASE_NAME", "veltrix_test")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        start = int(request.url.params["start_time"])
        kickoff = datetime.fromtimestamp(start + 3600, tz=UTC).isoformat()
        fixture_id = 880000 + len(requests)
        return httpx.Response(
            200,
            json={
                "success": 1,
                "data": [_fixture(fixture_id, kickoff)],
                "pagination": {
                    "page": int(request.url.params["page"]),
                    "per_page": 100,
                    "count": 1,
                    "has_more": False,
                },
            },
            headers={"X-Request-Id": f"round38-request-{fixture_id}"},
        )

    provider = FiveDollarFootballProvider(
        api_key="test-only-key",
        transport=httpx.MockTransport(handler),
    )
    start = datetime(2026, 11, 9, tzinfo=UTC)
    end = datetime(2026, 11, 17, tzinfo=UTC)
    run_id = asyncio.run(
        run_brazil_serie_b_historical_import(
            database_url,
            api_key="test-only-key",
            execute=True,
            approval=IMPORT_APPROVAL,
            provider=provider,
            boundary_start=start,
            boundary_end=end,
            request_budget=4,
        )
    )

    assert len(requests) == 2
    assert [request.url.params["start_time"] for request in requests] == [
        str(int(start.timestamp())),
        str(int(datetime(2026, 11, 16, tzinfo=UTC).timestamp())),
    ]
    assert all(request.url.params["per_page"] == "100" for request in requests)

    with psycopg.connect(database_url) as connection:
        run = connection.execute(
            """
            SELECT status, boundary_start, boundary_end, request_budget,
                   requests_used, records_seen, records_inserted
            FROM veltrix_ai_analyst.import_runs WHERE id = %s
            """,
            (run_id,),
        ).fetchone()
        report = historical_validation.validate_brazil_serie_b_import(connection, run_id)

    assert run == ("COMPLETED", start, end, 4, 2, 2, 2)
    assert report["passed"] is True
    assert report["checkpoints"] == 2
    assert report["fixture_sightings"] == 2
    assert report["request_budget"] == 4


def test_incremental_import_rejects_naive_or_oversized_boundaries(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION", "true")
    with pytest.raises(HistoricalImportError, match="IMPORT_BOUNDARIES_MUST_BE_TIMEZONE_AWARE"):
        asyncio.run(
            run_brazil_serie_b_historical_import(
                database_url,
                api_key="test-only-key",
                execute=True,
                boundary_start=datetime(2026, 11, 9),
                boundary_end=datetime(2026, 11, 17, tzinfo=UTC),
                request_budget=4,
            )
        )
    with pytest.raises(HistoricalImportError, match="REQUEST_BUDGET_OUTSIDE_HARD_CAP"):
        asyncio.run(
            run_brazil_serie_b_historical_import(
                database_url,
                api_key="test-only-key",
                execute=True,
                boundary_start=datetime(2026, 11, 9, tzinfo=UTC),
                boundary_end=datetime(2026, 11, 17, tzinfo=UTC),
                request_budget=41,
            )
        )



def test_future_fixture_capture_records_system_observed_pit_evidence(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION", "true")
    monkeypatch.setattr(historical_import, "EXPECTED_DATABASE_NAME", "veltrix_test")
    monkeypatch.setattr(historical_validation, "EXPECTED_DATABASE_NAME", "veltrix_test")
    start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
    end = start + timedelta(days=1)

    def handler(request: httpx.Request) -> httpx.Response:
        kickoff = datetime.fromtimestamp(
            int(request.url.params["start_time"]) + 3600,
            tz=UTC,
        ).isoformat()
        fixture = _fixture(990001, kickoff)
        fixture["status"] = "scheduled"
        fixture["goals"] = {"home": None, "away": None}
        return httpx.Response(
            200,
            json={
                "success": 1,
                "data": [fixture],
                "pagination": {
                    "page": int(request.url.params["page"]),
                    "per_page": 100,
                    "count": 1,
                    "has_more": False,
                },
            },
            headers={"X-Request-Id": "future-system-observed-capture"},
        )

    provider = FiveDollarFootballProvider(
        api_key="test-only-key",
        transport=httpx.MockTransport(handler),
    )
    run_id = asyncio.run(
        run_brazil_serie_b_historical_import(
            database_url,
            api_key="test-only-key",
            execute=True,
            approval=IMPORT_APPROVAL,
            provider=provider,
            boundary_start=start,
            boundary_end=end,
            request_budget=4,
        )
    )

    with psycopg.connect(database_url) as connection:
        row = connection.execute(
            """
            SELECT
                f.kickoff_at,
                o.retrieved_at,
                o.source_published_at,
                o.available_at,
                o.availability_basis,
                o.point_in_time_certifiable,
                s.retrieved_at,
                s.available_at,
                s.availability_basis,
                s.point_in_time_certifiable,
                s.provider_response_id
            FROM veltrix_ai_analyst.provider_fixtures f
            JOIN veltrix_ai_analyst.source_observations o
              ON o.id = f.source_observation_id
            JOIN veltrix_ai_analyst.source_observation_sightings s
              ON s.source_observation_id = o.id
            WHERE f.provider = '5DollarFootballAPI'
              AND f.source_id = '5dollarfootballapi'
              AND f.provider_fixture_id = '990001'
            ORDER BY s.id DESC
            LIMIT 1
            """
        ).fetchone()
        run_status = connection.execute(
            "SELECT status FROM veltrix_ai_analyst.import_runs WHERE id = %s",
            (run_id,),
        ).fetchone()[0]
        related_entity_evidence = connection.execute(
            """
            SELECT entity_type, COUNT(*),
                   BOOL_AND(point_in_time_certifiable IS TRUE),
                   BOOL_AND(availability_basis = 'SYSTEM_OBSERVED_AT'),
                   BOOL_AND(available_at = retrieved_at)
            FROM veltrix_ai_analyst.source_observations
            WHERE provider_response_id = %s
              AND entity_type IN ('competition', 'team', 'fixture')
            GROUP BY entity_type
            """,
            (row[10],),
        ).fetchall() if row is not None else []

    assert run_status == "COMPLETED"
    assert row is not None
    assert row[0] > row[1]  # fixture kickoff is still in the future at capture
    assert row[2] is None
    assert row[3] == row[1]
    assert row[4] == "SYSTEM_OBSERVED_AT"
    assert row[5] is True
    assert row[6] == row[7]
    assert row[8] == "SYSTEM_OBSERVED_AT"
    assert row[9] is True
    assert row[10] is not None
    assert {item[0]: item[1:] for item in related_entity_evidence} == {
        "competition": (1, True, True, True),
        "team": (2, True, True, True),
        "fixture": (1, True, True, True),
    }
