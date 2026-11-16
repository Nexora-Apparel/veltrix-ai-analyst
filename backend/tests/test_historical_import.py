from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

import httpx
import psycopg
import pytest

from app.providers import historical_import
from app.db.migrations import apply_migrations
from app.providers.five_dollar import FiveDollarFootballProvider
from app.providers.historical_import import (
    IMPORT_APPROVAL,
    HistoricalImportError,
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


def test_historical_import_persists_page_evidence_and_checkpoints(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION", "true")
    monkeypatch.setattr(historical_import, "EXPECTED_DATABASE_NAME", "veltrix_test")
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
