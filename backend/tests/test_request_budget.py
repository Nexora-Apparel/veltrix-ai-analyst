import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest

from app.db.migrations import apply_migrations
from app.db.request_budget import (
    PostgresRequestBudget,
    RequestBudgetError,
    RequestBudgetExceeded,
    ReservationConflict,
)
from app.db.store import PostgresIngestionStore
from app.providers.collection_plan import build_date_windows
from app.providers.approvals import FIVEDOLLAR_COMMUNITY_APPROVAL


@pytest.fixture
def database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not url or not database:
        pytest.skip("PostgreSQL integration service is not configured")
    apply_migrations(url, expected_database=database)
    return url


def make_run(database_url: str, budget: int) -> int:
    approval = replace(
        FIVEDOLLAR_COMMUNITY_APPROVAL,
        approval_id=f"test-budget-approval-{uuid4().hex}",
        source_id=f"test-budget-source-{uuid4().hex}",
    )
    with psycopg.connect(database_url) as conn:
        return PostgresIngestionStore(conn).create_import_run(
            approval,
            scope_value="522514093",
            data_type="fixtures_and_results",
            import_type="historical_backfill",
            boundary_start=datetime(2026, 3, 21, tzinfo=UTC),
            boundary_end=datetime(2026, 11, 9, tzinfo=UTC),
            request_budget=budget,
            importer_version="request-budget-test-v1",
            started_at=datetime.now(UTC),
        )


def reserve_one(database_url: str, run_id: int, index: int):
    now = datetime.now(UTC)
    with psycopg.connect(database_url, autocommit=True) as conn:
        return PostgresRequestBudget(conn).reserve(
            import_run_id=run_id,
            request_key=f"window-0-page-{index}",
            window_start=datetime(2026, 3, 21, tzinfo=UTC),
            window_end=datetime(2026, 3, 28, tzinfo=UTC),
            page_number=index,
            endpoint="/v1/leagues/522514093/fixtures",
            request_params={"page": index, "per_page": 100},
            reserved_at=now,
        )


def test_budget_reservations_are_atomic_under_concurrency(database_url: str) -> None:
    run_id = make_run(database_url, 10)
    with ThreadPoolExecutor(max_workers=16) as pool:
        outcomes = list(
            pool.map(
                lambda index: _reserve_outcome(database_url, run_id, index),
                range(1, 17),
            )
        )

    assert sum(outcome == "reserved" for outcome in outcomes) == 10
    assert sum(outcome == "exhausted" for outcome in outcomes) == 6
    with psycopg.connect(database_url) as conn:
        run = conn.execute(
            "SELECT requests_used, request_budget FROM veltrix_ai_analyst.import_runs WHERE id = %s",
            (run_id,),
        ).fetchone()
        reservations = conn.execute(
            "SELECT COUNT(*) FROM veltrix_ai_analyst.import_request_reservations WHERE import_run_id = %s",
            (run_id,),
        ).fetchone()
    assert run == (10, 10)
    assert reservations == (10,)


def _reserve_outcome(database_url: str, run_id: int, index: int) -> str:
    try:
        reservation = reserve_one(database_url, run_id, index)
        assert reservation.created
        return "reserved"
    except RequestBudgetExceeded:
        return "exhausted"


def test_same_key_concurrent_reservation_creates_only_one_http_permit(
    database_url: str,
) -> None:
    run_id = make_run(database_url, 5)
    with ThreadPoolExecutor(max_workers=12) as pool:
        reservations = list(
            pool.map(lambda _: reserve_one(database_url, run_id, 1), range(12))
        )

    assert len({reservation.reservation_id for reservation in reservations}) == 1
    assert sum(reservation.created for reservation in reservations) == 1
    with psycopg.connect(database_url) as conn:
        assert conn.execute(
            "SELECT requests_used FROM veltrix_ai_analyst.import_runs WHERE id = %s",
            (run_id,),
        ).fetchone() == (1,)


def test_reservation_is_idempotent_and_rejects_changed_payload(database_url: str) -> None:
    run_id = make_run(database_url, 2)
    first = reserve_one(database_url, run_id, 1)
    repeated = reserve_one(database_url, run_id, 1)
    assert first.reservation_id == repeated.reservation_id
    assert first.created is True
    assert repeated.created is False

    now = datetime.now(UTC)
    with (
        psycopg.connect(database_url, autocommit=True) as conn,
        pytest.raises(ReservationConflict),
    ):
        PostgresRequestBudget(conn).reserve(
            import_run_id=run_id,
            request_key="window-0-page-1",
            window_start=datetime(2026, 3, 21, tzinfo=UTC),
            window_end=datetime(2026, 3, 28, tzinfo=UTC),
            page_number=1,
            endpoint="/v1/leagues/522514093/fixtures",
            request_params={"page": 99, "per_page": 100},
            reserved_at=now,
        )
    with psycopg.connect(database_url) as conn:
        assert conn.execute(
            "SELECT requests_used FROM veltrix_ai_analyst.import_runs WHERE id = %s",
            (run_id,),
        ).fetchone() == (1,)


def test_reservation_refuses_non_running_run(database_url: str) -> None:
    run_id = make_run(database_url, 1)
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "UPDATE veltrix_ai_analyst.import_runs SET status = 'PAUSED' WHERE id = %s",
            (run_id,),
        )
    now = datetime.now(UTC)
    with (
        psycopg.connect(database_url, autocommit=True) as conn,
        pytest.raises(RequestBudgetError, match="IMPORT_RUN_NOT_RUNNING"),
    ):
        PostgresRequestBudget(conn).reserve(
            import_run_id=run_id,
            request_key=uuid4().hex,
            window_start=now,
            window_end=now + timedelta(days=1),
            page_number=1,
            endpoint="/v1/leagues/522514093/fixtures",
            request_params={"page": 1},
        )



def test_controlled_collection_dry_run_resumes_34_checkpoints_and_stops_at_40(
    database_url: str,
) -> None:
    run_id = make_run(database_url, 40)
    windows = build_date_windows(
        datetime(2026, 3, 21, tzinfo=UTC),
        datetime(2026, 11, 9, tzinfo=UTC),
    )
    assert len(windows) == 34

    for index, window in enumerate(windows):
        with psycopg.connect(database_url, autocommit=True) as quota_connection:
            first = PostgresRequestBudget(quota_connection).reserve(
                import_run_id=run_id,
                request_key=f"window-{index}-page-1",
                window_start=window.start_at,
                window_end=window.end_at,
                page_number=1,
                endpoint="/v1/leagues/522514093/fixtures",
                request_params={"page": 1, "per_page": 100},
            )
            assert first.created

        requests_for_window = 1
        cursor = "page=1"
        if index < 6:
            with psycopg.connect(database_url, autocommit=True) as quota_connection:
                second = PostgresRequestBudget(quota_connection).reserve(
                    import_run_id=run_id,
                    request_key=f"window-{index}-page-2",
                    window_start=window.start_at,
                    window_end=window.end_at,
                    page_number=2,
                    endpoint="/v1/leagues/522514093/fixtures",
                    request_params={"page": 2, "per_page": 100},
                )
                assert second.created
            requests_for_window = 2
            cursor = "page=2"

        # Commit each window checkpoint before the next budget reservation.
        with psycopg.connect(database_url) as store_connection:
            PostgresIngestionStore(store_connection).save_checkpoint(
                import_run_id=run_id,
                window_start=window.start_at,
                window_end=window.end_at,
                status="COMPLETED",
                records_seen=0,
                requests_used=requests_for_window,
                cursor_value=cursor,
            )

    with psycopg.connect(database_url) as store_connection:
        recovered = PostgresIngestionStore(store_connection).load_checkpoints(
            import_run_id=run_id
        )
        assert len(recovered) == 34
        assert all(checkpoint["status"] == "COMPLETED" for checkpoint in recovered)
        assert sum(checkpoint["requests_used"] for checkpoint in recovered) == 40

    last_window = windows[-1]
    with (
        psycopg.connect(database_url, autocommit=True) as quota_connection,
        pytest.raises(RequestBudgetExceeded, match="PERSISTED_REQUEST_BUDGET_EXHAUSTED"),
    ):
        PostgresRequestBudget(quota_connection).reserve(
            import_run_id=run_id,
            request_key="window-33-page-2",
            window_start=last_window.start_at,
            window_end=last_window.end_at,
            page_number=2,
            endpoint="/v1/leagues/522514093/fixtures",
            request_params={"page": 2, "per_page": 100},
        )

    with psycopg.connect(database_url) as conn:
        assert conn.execute(
            "SELECT requests_used, request_budget FROM veltrix_ai_analyst.import_runs WHERE id = %s",
            (run_id,),
        ).fetchone() == (40, 40)



def test_database_rejects_request_budget_above_40(database_url: str) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        make_run(database_url, 41)
