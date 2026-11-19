from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest

from app.canonicalization import (
    BRAZIL_SERIE_B_RUN_3,
    CanonicalMaterializationScope,
    _identity_collision_fixture_ids,
    SUPPORTED_FIXTURE_STATUSES,
    materialize_brazil_serie_b_canonical_entities,
)
from app.db.migrations import apply_migrations
from app.db.store import PostgresIngestionStore
from app.providers.approvals import FIVEDOLLAR_COMMUNITY_APPROVAL
from app.providers.contracts import ProviderCompetition, ProviderFixture, SourceProvenance


@pytest.fixture
def connection():
    import os

    database_url = os.getenv("DATABASE_URL", "")
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not database_url or not expected_database:
        pytest.skip("PostgreSQL integration service is not configured")
    apply_migrations(database_url, expected_database=expected_database)
    with psycopg.connect(database_url) as conn:
        yield conn


def test_production_scope_is_pinned_to_brazil_serie_b_run_three() -> None:
    assert BRAZIL_SERIE_B_RUN_3.provider == "5DollarFootballAPI"
    assert BRAZIL_SERIE_B_RUN_3.source_id == "5dollarfootballapi"
    assert BRAZIL_SERIE_B_RUN_3.competition_id == "522514093"
    assert BRAZIL_SERIE_B_RUN_3.import_run_id == 3
    assert BRAZIL_SERIE_B_RUN_3.expected_fixture_count == 374
    assert BRAZIL_SERIE_B_RUN_3.expected_team_count == 21


def test_materializer_defaults_to_read_only() -> None:
    assert inspect.signature(materialize_brazil_serie_b_canonical_entities).parameters[
        "execute"
    ].default is False

def test_supported_fixture_statuses_match_database_contract() -> None:
    assert SUPPORTED_FIXTURE_STATUSES == {
        "SCHEDULED",
        "LIVE",
        "FINISHED",
        "POSTPONED",
        "CANCELLED",
        "ABANDONED",
        "UNKNOWN",
    }


def test_identity_collision_detection_requires_exact_provider_ids_and_opponent() -> None:
    kickoff = datetime(2026, 3, 22, 21, tzinfo=UTC)
    fixtures = [
        {
            "provider_fixture_id": "known-america-mg",
            "home_team_provider_id": "goias-id",
            "away_team_provider_id": "1102583842",
            "kickoff_at": kickoff,
        },
        {
            "provider_fixture_id": "known-america-mineiro",
            "home_team_provider_id": "goias-id",
            "away_team_provider_id": "3808811746",
            "kickoff_at": kickoff + timedelta(seconds=85),
        },
        {
            "provider_fixture_id": "unrelated-same-name",
            "home_team_provider_id": "goias-id",
            "away_team_provider_id": "america-mg",
            "kickoff_at": kickoff + timedelta(seconds=20),
        },
    ]
    assert _identity_collision_fixture_ids(fixtures, (("1102583842", "3808811746"),)) == (
        "known-america-mg",
        "known-america-mineiro",
    )


def _record_response(
    store: PostgresIngestionStore,
    approval,
    *,
    data_type: str,
    suffix: str,
    now: datetime,
) -> int:
    return store.record_provider_response(
        approval,
        scope_value="522514093",
        data_type=data_type,
        endpoint=f"/test/canonical/{suffix}",
        request_id=f"canonical-test-{suffix}-{uuid4().hex}",
        request_params={"test_case": suffix},
        http_status=200,
        raw_body=f'{{"case":"{suffix}"}}'.encode(),
        response_headers={"content-type": "application/json"},
        fetched_at=now,
    )


def test_dry_run_and_materialization_are_provenance_bound_and_idempotent(
    connection: psycopg.Connection,
) -> None:
    now = datetime.now(UTC)
    approval = replace(
        FIVEDOLLAR_COMMUNITY_APPROVAL,
        approval_id=f"canonical-materialization-{uuid4().hex}",
        source_id=f"canonical-test-source-{uuid4().hex}",
    )
    store = PostgresIngestionStore(connection)
    store.sync_source_approval(approval)

    competition_response = _record_response(
        store, approval, data_type="competition_catalogue", suffix="competition", now=now
    )
    competition_observation = store.record_source_observation(
        approval,
        scope_value="522514093",
        data_type="competition_catalogue",
        entity_type="competition",
        provider_entity_id="522514093",
        schema_version="canonical-test-v1",
        retrieved_at=now,
        payload={"competition_id": "522514093", "name": "Brazil Serie B"},
        provider_response_id=competition_response,
    )
    competition = ProviderCompetition(
        provenance=SourceProvenance(
            provider=approval.provider,
            provider_record_id="522514093",
            retrieved_at=now,
        ),
        competition_id="522514093",
        name="Brazil Serie B",
    )
    store.upsert_provider_competition(
        competition,
        source_id=approval.source_id,
        source_observation_id=competition_observation,
        approval=approval,
    )

    team_ids = ("test-home-team", "test-away-team")
    team_names = ("Home Test FC", "Away Test FC")
    for team_id, team_name in zip(team_ids, team_names, strict=True):
        response_id = _record_response(
            store, approval, data_type="team_catalogue", suffix=team_id, now=now
        )
        observation_id = store.record_source_observation(
            approval,
            scope_value="522514093",
            data_type="team_catalogue",
            entity_type="team",
            provider_entity_id=team_id,
            schema_version="canonical-test-v1",
            retrieved_at=now,
            payload={"team_id": team_id, "name": team_name},
            provider_response_id=response_id,
        )
        store.upsert_provider_team(
            source_id=approval.source_id,
            competition_id="522514093",
            provider_team_id=team_id,
            name=team_name,
            source_observation_id=observation_id,
            approval=approval,
            first_seen_at=now,
            last_seen_at=now,
        )

    for index, (status, goals) in enumerate(
        (
            ("finished", (2, 1)),
            ("scheduled", (None, None)),
            ("unknown", (None, None)),
        ),
        start=1,
    ):
        fixture_id = f"test-fixture-{index}"
        response_id = _record_response(
            store, approval, data_type="fixtures_and_results", suffix=fixture_id, now=now
        )
        kickoff = now + timedelta(days=index)
        fixture = ProviderFixture(
            provenance=SourceProvenance(
                provider=approval.provider,
                provider_record_id=fixture_id,
                retrieved_at=now,
            ),
            competition_id="522514093",
            competition_name="Brazil Serie B",
            season_id="2026",
            home_team_id=team_ids[0],
            home_team_name=team_names[0],
            away_team_id=team_ids[1],
            away_team_name=team_names[1],
            kickoff_at=kickoff,
            status=status,
            home_goals=goals[0],
            away_goals=goals[1],
        )
        observation_id = store.record_source_observation(
            approval,
            scope_value="522514093",
            data_type="fixtures_and_results",
            entity_type="fixture",
            provider_entity_id=fixture_id,
            schema_version="canonical-test-v1",
            retrieved_at=now,
            payload=fixture.model_dump(mode="json"),
            provider_response_id=response_id,
        )
        store.upsert_provider_fixture(
            fixture,
            source_id=approval.source_id,
            source_observation_id=observation_id,
            approval=approval,
        )

    scope = CanonicalMaterializationScope(
        provider=approval.provider,
        source_id=approval.source_id,
        competition_id="522514093",
        rights_approval_id=approval.approval_id,
        import_run_id=None,
        expected_fixture_count=3,
        expected_team_count=2,
    )

    preview = materialize_brazil_serie_b_canonical_entities(
        connection, scope=scope
    )
    assert preview["mode"] == "DRY_RUN"
    assert preview["plan"]["ready"] is True
    assert preview["plan"]["team_count"] == 2
    assert preview["plan"]["competition_count"] == 1
    assert preview["plan"]["fixture_count"] == 3
    assert preview["plan"]["finished_fixture_count"] == 1
    assert preview["plan"]["unknown_fixture_count"] == 1
    assert preview["plan"]["non_pit_observation_count"] == 6

    first = materialize_brazil_serie_b_canonical_entities(
        connection, execute=True, scope=scope
    )
    assert first["mode"] == "APPLIED"
    assert first["competition_created"] is True
    assert first["teams_created"] == 2
    assert first["fixtures_created"] == 3
    assert first["identity_reviews_created"] == 0
    assert first["pit_observations_promoted"] == 0
    assert first["provider_requests_made"] == 0

    second = materialize_brazil_serie_b_canonical_entities(
        connection, execute=True, scope=scope
    )
    assert second["competition_created"] is False
    assert second["teams_created"] == 0
    assert second["fixtures_created"] == 0
    assert second["fixtures_reused"] == 3

    counts = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_teams),
            (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_competitions),
            (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_fixtures),
            (SELECT COUNT(*) FROM veltrix_ai_analyst.provider_team_identity_links),
            (SELECT COUNT(*) FROM veltrix_ai_analyst.provider_competition_identity_links),
            (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_fixture_sources),
            (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_identity_review_events)
        """
    ).fetchone()
    assert counts == (2, 1, 3, 2, 1, 3, 0)

    unknown = connection.execute(
        """
        SELECT status, home_goals, away_goals, identity_status, completeness_status
        FROM veltrix_ai_analyst.canonical_fixtures
        WHERE status = 'UNKNOWN'
        """
    ).fetchone()
    assert unknown == (
        "UNKNOWN",
        None,
        None,
        "IDENTITY_REVIEW_REQUIRED",
        "SOURCE_ROW_ONLY",
    )
