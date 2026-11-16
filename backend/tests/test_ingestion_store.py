import hashlib
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest

from app.db.migrations import apply_migrations
from app.db.store import EvidenceConflict, IngestionStoreError, PostgresIngestionStore, RightsDenied
from app.providers.approvals import FIVEDOLLAR_COMMUNITY_APPROVAL
from app.providers.rights import SourceApproval
from app.providers.contracts import ProviderCompetition, ProviderFixture, SourceProvenance


@pytest.fixture
def connection():
    database_url = os.getenv("DATABASE_URL", "")
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not database_url or not expected_database:
        pytest.skip("PostgreSQL integration service is not configured")
    apply_migrations(database_url, expected_database=expected_database)
    with psycopg.connect(database_url) as conn:
        yield conn


def new_approval() -> SourceApproval:
    suffix = uuid4().hex
    return replace(
        FIVEDOLLAR_COMMUNITY_APPROVAL,
        approval_id=f"test-store-approval-{suffix}",
        source_id=f"test-store-source-{suffix}",
    )


def test_store_records_provider_response_and_normalized_observation(connection) -> None:
    approval = new_approval()
    store = PostgresIngestionStore(connection)
    now = datetime.now(UTC)
    competition_id = "522514093"
    request_id = f"fixture-request-{uuid4().hex}"
    raw_body = b'{"success":true,"data":[{"id":"fixture-1"}]}'

    response_id = store.record_provider_response(
        approval,
        scope_value=competition_id,
        data_type="fixtures_and_results",
        endpoint=f"/leagues/{competition_id}/fixtures",
        request_id=request_id,
        request_params={"start_time": "2026-11-01T00:00:00Z", "per_page": 100},
        http_status=200,
        raw_body=raw_body,
        response_headers={
            "Content-Type": "application/json",
            "X-RateLimit-Remaining": "299",
            "Authorization": "Bearer must-not-persist",
            "Set-Cookie": "session=private",
        },
        fetched_at=now,
        quota_limit=300,
        quota_remaining=299,
    )
    repeated_response_id = store.record_provider_response(
        approval,
        scope_value=competition_id,
        data_type="fixtures_and_results",
        endpoint=f"/leagues/{competition_id}/fixtures",
        request_id=request_id,
        request_params={"start_time": "2026-11-01T00:00:00Z", "per_page": 100},
        http_status=200,
        raw_body=raw_body,
        response_headers={"Content-Type": "application/json"},
        fetched_at=now,
        quota_limit=300,
        quota_remaining=299,
    )
    assert response_id == repeated_response_id

    response = connection.execute(
        """
        SELECT response_sha256, response_headers, raw_body
        FROM veltrix_ai_analyst.provider_responses
        WHERE id = %s
        """,
        (response_id,),
    ).fetchone()
    assert response is not None
    assert response[0].strip() == hashlib.sha256(raw_body).hexdigest()
    assert "authorization" not in response[1]
    assert "set-cookie" not in response[1]
    assert response[1]["x-ratelimit-remaining"] == "299"
    assert bytes(response[2]) == raw_body

    payload = {"fixture_id": "fixture-1", "status": "finished", "home_goals": 2, "away_goals": 1}
    observation_id = store.record_source_observation(
        approval,
        scope_value=competition_id,
        data_type="fixtures_and_results",
        entity_type="fixture",
        provider_entity_id="fixture-1",
        schema_version="provider-fixture-v1",
        retrieved_at=now,
        payload=payload,
        provider_response_id=response_id,
    )
    repeated_observation_id = store.record_source_observation(
        approval,
        scope_value=competition_id,
        data_type="fixtures_and_results",
        entity_type="fixture",
        provider_entity_id="fixture-1",
        schema_version="provider-fixture-v1",
        retrieved_at=now + timedelta(seconds=1),
        payload=payload,
        provider_response_id=response_id,
    )
    assert observation_id == repeated_observation_id
    sightings = connection.execute(
        """
        SELECT COUNT(*)
        FROM veltrix_ai_analyst.source_observation_sightings
        WHERE source_observation_id = %s
        """,
        (observation_id,),
    ).fetchone()
    assert sightings == (2,)

    with pytest.raises(IngestionStoreError, match="PIT_CERTIFICATION_REQUIRES_VERIFIED_PUBLICATION_TIME"):
        store.record_source_observation(
            approval,
            scope_value=competition_id,
            data_type="fixtures_and_results",
            entity_type="fixture",
            provider_entity_id="fixture-pit-invalid",
            schema_version="provider-fixture-v1",
            retrieved_at=now,
            payload={"fixture_id": "fixture-pit-invalid"},
            point_in_time_certifiable=True,
        )

    with pytest.raises(IngestionStoreError, match="SENSITIVE_REQUEST_PARAMETER_REJECTED"):
        store.record_provider_response(
            approval,
            scope_value=competition_id,
            data_type="fixtures_and_results",
            endpoint="/fixtures",
            request_id=f"secret-request-{uuid4().hex}",
            request_params={"api_key": "must-not-persist"},
            http_status=200,
            raw_body=b"{}",
            response_headers={},
            fetched_at=now,
        )


def test_store_upserts_provider_entities_and_fixture_with_settlement_guard(connection) -> None:
    approval = new_approval()
    store = PostgresIngestionStore(connection)
    now = datetime.now(UTC)
    competition_id = "522514093"
    home_id = f"home-{uuid4().hex}"
    away_id = f"away-{uuid4().hex}"
    fixture_id = f"fixture-{uuid4().hex}"

    competition = ProviderCompetition(
        provenance=SourceProvenance(
            provider=approval.provider,
            provider_record_id=competition_id,
            retrieved_at=now,
        ),
        competition_id=competition_id,
        name="Brazil Serie B",
        country_code="BR",
        country_name="Brazil",
        seasons=("2026",),
    )
    competition_observation = store.record_source_observation(
        approval,
        scope_value=competition_id,
        data_type="competition_catalogue",
        entity_type="competition",
        provider_entity_id=competition_id,
        schema_version="provider-competition-v1",
        retrieved_at=now,
        payload=competition.model_dump(mode="json"),
    )
    competition_row_id = store.upsert_provider_competition(
        competition,
        source_id=approval.source_id,
        source_observation_id=competition_observation,
        approval=approval,
    )
    assert competition_row_id > 0

    for team_id, team_name in ((home_id, "Home FC"), (away_id, "Away FC")):
        team_observation = store.record_source_observation(
            approval,
            scope_value=competition_id,
            data_type="team_catalogue",
            entity_type="team",
            provider_entity_id=team_id,
            schema_version="provider-team-v1",
            retrieved_at=now,
            payload={"team_id": team_id, "name": team_name},
        )
        assert store.upsert_provider_team(
            source_id=approval.source_id,
            competition_id=competition_id,
            provider_team_id=team_id,
            name=team_name,
            source_observation_id=team_observation,
            approval=approval,
            country_code="BR",
            first_seen_at=now,
            last_seen_at=now,
        ) > 0

    fixture = ProviderFixture(
        provenance=SourceProvenance(
            provider=approval.provider,
            provider_record_id=fixture_id,
            retrieved_at=now,
        ),
        competition_id=competition_id,
        competition_name="Brazil Serie B",
        season_id="2026",
        home_team_id=home_id,
        home_team_name="Home FC",
        away_team_id=away_id,
        away_team_name="Away FC",
        kickoff_at=now - timedelta(days=1),
        status="finished",
        home_goals=2,
        away_goals=1,
    )
    fixture_observation = store.record_source_observation(
        approval,
        scope_value=competition_id,
        data_type="fixtures_and_results",
        entity_type="fixture",
        provider_entity_id=fixture_id,
        schema_version="provider-fixture-v1",
        retrieved_at=now,
        payload=fixture.model_dump(mode="json"),
    )
    fixture_row_id = store.upsert_provider_fixture(
        fixture,
        source_id=approval.source_id,
        source_observation_id=fixture_observation,
        approval=approval,
    )
    assert fixture_row_id > 0

    saved = connection.execute(
        """
        SELECT status, home_goals, away_goals
        FROM veltrix_ai_analyst.provider_fixtures
        WHERE id = %s
        """,
        (fixture_row_id,),
    ).fetchone()
    assert saved == ("FINISHED", 2, 1)


def test_store_creates_bounded_import_checkpoints_and_quarantine(connection) -> None:
    approval = new_approval()
    store = PostgresIngestionStore(connection)
    now = datetime.now(UTC)
    run_id = store.create_import_run(
        approval,
        scope_value="522514093",
        data_type="fixtures_and_results",
        import_type="historical_backfill",
        boundary_start=now - timedelta(days=30),
        boundary_end=now,
        request_budget=40,
        importer_version="stage2-store-v1",
        started_at=now,
    )
    store.save_checkpoint(
        import_run_id=run_id,
        window_start=now - timedelta(days=1),
        window_end=now,
        status="COMPLETED",
        records_seen=3,
        records_inserted=1,
        records_duplicate=1,
        records_rejected=0,
        records_quarantined=1,
        requests_used=1,
        response_sha256="a" * 64,
    )
    checkpoint = connection.execute(
        """
        SELECT records_seen, records_inserted, records_duplicate, records_quarantined
        FROM veltrix_ai_analyst.import_checkpoints
        WHERE import_run_id = %s
        """,
        (run_id,),
    ).fetchone()
    assert checkpoint == (3, 1, 1, 1)

    quarantine_id = store.quarantine_record(
        provider=approval.provider,
        source_id=approval.source_id,
        provider_entity_id="bad-score-row",
        reason_code="TEAM_SCORE_MISMATCH",
        details={"match": "Example 0-3 Match", "row_count": 2},
        import_run_id=run_id,
    )
    assert quarantine_id > 0


def test_store_rejects_scope_escape_and_database_revocation(connection) -> None:
    approval = new_approval()
    store = PostgresIngestionStore(connection)
    now = datetime.now(UTC)

    with pytest.raises(RightsDenied, match="SOURCE_SCOPE_NOT_APPROVED"):
        store.record_provider_response(
            approval,
            scope_value="not-entitled-competition",
            data_type="fixtures_and_results",
            endpoint="/fixtures",
            request_id=f"out-of-scope-{uuid4().hex}",
            request_params={},
            http_status=200,
            raw_body=b"{}",
            response_headers={},
            fetched_at=now,
        )

    store.sync_source_approval(approval)
    connection.execute(
        """
        INSERT INTO veltrix_ai_analyst.source_approval_status_events (
            approval_id, status, evidence_uri, evidence_sha256, effective_at, reason_code
        ) VALUES (%s, 'REVOKED', 'https://example.test/revocation', %s, %s, 'TEST_REVOKED')
        """,
        (approval.approval_id, "e" * 64, now),
    )

    with pytest.raises(RightsDenied, match="SOURCE_RIGHTS_NOT_EFFECTIVE"):
        store.record_provider_response(
            approval,
            scope_value="522514093",
            data_type="fixtures_and_results",
            endpoint="/fixtures",
            request_id=f"revoked-{uuid4().hex}",
            request_params={},
            http_status=200,
            raw_body=b"{}",
            response_headers={},
            fetched_at=now + timedelta(seconds=1),
        )


def test_store_refuses_changed_approval_under_same_id(connection) -> None:
    approval = new_approval()
    store = PostgresIngestionStore(connection)
    store.sync_source_approval(approval)
    changed = replace(approval, evidence_sha256="d" * 64)

    with pytest.raises(EvidenceConflict, match="SOURCE_APPROVAL_ID_ALREADY_EXISTS_WITH_DIFFERENT_EVIDENCE"):
        store.sync_source_approval(changed)
