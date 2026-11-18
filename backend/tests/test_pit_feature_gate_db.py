from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from app.db.migrations import apply_migrations
from app.db.store import PostgresIngestionStore
from app.providers.approvals import FIVEDOLLAR_COMMUNITY_APPROVAL
from app.providers.contracts import ProviderFixture, SourceProvenance


@pytest.fixture
def database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not url or not database:
        pytest.skip("PostgreSQL integration service is not configured")
    apply_migrations(url, expected_database=database)
    return url


def _seed_target_teams(
    store: PostgresIngestionStore,
    *,
    now: datetime,
    response_id: int,
    marker: str,
    home_team_id: str,
    away_team_id: str,
) -> None:
    for team_id, name in (
        (home_team_id, f"Home {marker}"),
        (away_team_id, f"Away {marker}"),
    ):
        observation_id = store.record_source_observation(
            FIVEDOLLAR_COMMUNITY_APPROVAL,
            scope_value="522514093",
            data_type="team_catalogue",
            entity_type="team",
            provider_entity_id=team_id,
            schema_version="pit-gate-team-v1",
            retrieved_at=now,
            availability_basis="SYSTEM_OBSERVED_AT",
            point_in_time_certifiable=True,
            payload={"team_id": team_id, "team_name": name},
            provider_response_id=response_id,
        )
        store.upsert_provider_team(
            source_id="5dollarfootballapi",
            competition_id="522514093",
            provider_team_id=team_id,
            name=name,
            source_observation_id=observation_id,
            approval=FIVEDOLLAR_COMMUNITY_APPROVAL,
            first_seen_at=now,
            last_seen_at=now,
        )


def test_database_gate_accepts_verified_publication_and_rejects_retrieval_only(
    database_url: str,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    published_at = now - timedelta(hours=2)
    cutoff_at = now - timedelta(hours=1)
    marker = uuid4().hex
    with psycopg.connect(database_url) as connection:
        store = PostgresIngestionStore(connection)
        with connection.transaction():
            store.sync_source_approval(FIVEDOLLAR_COMMUNITY_APPROVAL)
            response_id = store.record_provider_response(
                FIVEDOLLAR_COMMUNITY_APPROVAL,
                scope_value="522514093",
                data_type="fixtures_and_results",
                endpoint="/v1/test/pit-gate",
                request_id=f"pit-gate-{marker}",
                request_params={"test": marker},
                http_status=200,
                raw_body=f'{{"test":"{marker}"}}'.encode(),
                response_headers={"content-type": "application/json"},
                fetched_at=now,
            )
            eligible_observation_id = store.record_source_observation(
                FIVEDOLLAR_COMMUNITY_APPROVAL,
                scope_value="522514093",
                data_type="fixtures_and_results",
                entity_type="fixture",
                provider_entity_id=f"pit-eligible-{marker}",
                schema_version="pit-gate-test-v1",
                retrieved_at=now,
                source_published_at=published_at,
                available_at=published_at,
                availability_basis="SOURCE_PUBLISHED_AT",
                point_in_time_certifiable=True,
                payload={"test": marker, "case": "eligible"},
                provider_response_id=response_id,
            )
            ineligible_observation_id = store.record_source_observation(
                FIVEDOLLAR_COMMUNITY_APPROVAL,
                scope_value="522514093",
                data_type="fixtures_and_results",
                entity_type="fixture",
                provider_entity_id=f"pit-ineligible-{marker}",
                schema_version="pit-gate-test-v1",
                retrieved_at=now,
                availability_basis="RETRIEVED_AT_ONLY",
                point_in_time_certifiable=False,
                payload={"test": marker, "case": "retrieval-only"},
                provider_response_id=response_id,
            )

            _seed_target_teams(
                store,
                now=now,
                response_id=response_id,
                marker=marker,
                home_team_id=f"home-{marker}",
                away_team_id=f"away-{marker}",
            )
            target_fixture_id = store.upsert_provider_fixture(
                ProviderFixture(
                    provenance=SourceProvenance(
                        provider="5DollarFootballAPI",
                        provider_record_id=f"pit-eligible-{marker}",
                        retrieved_at=now,
                    ),
                    competition_id="522514093",
                    home_team_id=f"home-{marker}",
                    away_team_id=f"away-{marker}",
                    kickoff_at=now + timedelta(hours=1),
                    status="scheduled",
                ),
                source_id="5dollarfootballapi",
                source_observation_id=eligible_observation_id,
                approval=FIVEDOLLAR_COMMUNITY_APPROVAL,
            )

            eligible_sighting_id = connection.execute(
                """
                SELECT id FROM veltrix_ai_analyst.source_observation_sightings
                WHERE source_observation_id = %s
                """,
                (eligible_observation_id,),
            ).fetchone()[0]
            ineligible_sighting_id = connection.execute(
                """
                SELECT id FROM veltrix_ai_analyst.source_observation_sightings
                WHERE source_observation_id = %s
                """,
                (ineligible_observation_id,),
            ).fetchone()[0]

            store.record_pre_match_feature_observation(
                target_fixture_id=target_fixture_id,
                source_observation_id=eligible_observation_id,
                source_sighting_id=eligible_sighting_id,
                feature_key="test.feature",
                feature_value={"value": 1},
                prediction_cutoff_at=cutoff_at,
            )

            with (
                pytest.raises(
                    psycopg.errors.RaiseException,
                    match="PRE_MATCH_SOURCE_AVAILABILITY_EVIDENCE_REQUIRED",
                ),
                connection.transaction(),
            ):
                connection.execute(
                        """
                        INSERT INTO veltrix_ai_analyst.pre_match_feature_observations (
                            target_fixture_id, source_observation_id, source_sighting_id,
                            feature_key, feature_value, prediction_cutoff_at
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                    (
                        target_fixture_id,
                        ineligible_observation_id,
                        ineligible_sighting_id,
                        "test.must_be_rejected",
                        Jsonb({"value": 2}),
                        cutoff_at,
                    ),
                    )

            stored = connection.execute(
                """
                SELECT COUNT(*) FROM veltrix_ai_analyst.pre_match_feature_observations
                WHERE source_observation_id = %s
                """,
                (eligible_observation_id,),
            ).fetchone()[0]
            rejected = connection.execute(
                """
                SELECT COUNT(*) FROM veltrix_ai_analyst.pre_match_feature_observations
                WHERE source_observation_id = %s
                """,
                (ineligible_observation_id,),
            ).fetchone()[0]

    assert stored == 1
    assert rejected == 0



def test_database_gate_accepts_system_observed_payload_only_after_capture(
    database_url: str,
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    marker = uuid4().hex
    with psycopg.connect(database_url) as connection:
        store = PostgresIngestionStore(connection)
        with connection.transaction():
            store.sync_source_approval(FIVEDOLLAR_COMMUNITY_APPROVAL)
            response_id = store.record_provider_response(
                FIVEDOLLAR_COMMUNITY_APPROVAL,
                scope_value="522514093",
                data_type="fixtures_and_results",
                endpoint="/v1/test/system-observed-pit",
                request_id=f"system-observed-pit-{marker}",
                request_params={"test": marker},
                http_status=200,
                raw_body=f'{{"test":"{marker}"}}'.encode(),
                response_headers={"content-type": "application/json"},
                fetched_at=now,
            )
            observation_id = store.record_source_observation(
                FIVEDOLLAR_COMMUNITY_APPROVAL,
                scope_value="522514093",
                data_type="fixtures_and_results",
                entity_type="fixture",
                provider_entity_id=f"system-observed-{marker}",
                schema_version="system-observed-pit-v1",
                retrieved_at=now,
                availability_basis="SYSTEM_OBSERVED_AT",
                point_in_time_certifiable=True,
                payload={"test": marker, "case": "system-observed"},
                provider_response_id=response_id,
            )
            _seed_target_teams(
                store,
                now=now,
                response_id=response_id,
                marker=marker,
                home_team_id=f"system-home-{marker}",
                away_team_id=f"system-away-{marker}",
            )
            target_fixture_id = store.upsert_provider_fixture(
                ProviderFixture(
                    provenance=SourceProvenance(
                        provider="5DollarFootballAPI",
                        provider_record_id=f"system-observed-{marker}",
                        retrieved_at=now,
                    ),
                    competition_id="522514093",
                    home_team_id=f"system-home-{marker}",
                    away_team_id=f"system-away-{marker}",
                    kickoff_at=now + timedelta(hours=1),
                    status="scheduled",
                ),
                source_id="5dollarfootballapi",
                source_observation_id=observation_id,
                approval=FIVEDOLLAR_COMMUNITY_APPROVAL,
            )
            sighting_id = connection.execute(
                """
                SELECT id FROM veltrix_ai_analyst.source_observation_sightings
                WHERE source_observation_id = %s
                """,
                (observation_id,),
            ).fetchone()[0]
            payload_hash = connection.execute(
                """
                SELECT payload_sha256
                FROM veltrix_ai_analyst.source_observations
                WHERE id = %s
                """,
                (observation_id,),
            ).fetchone()[0]
            response_observed_at = connection.execute(
                """
                SELECT system_observed_at
                FROM veltrix_ai_analyst.provider_responses
                WHERE id = %s
                """,
                (response_id,),
            ).fetchone()[0]
            mismatched_sighting_id = connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.source_observation_sightings (
                    source_observation_id, provider_response_id, retrieved_at,
                    available_at, availability_basis, point_in_time_certifiable,
                    payload_sha256, system_observed_at
                ) VALUES (%s, %s, %s, %s, 'SYSTEM_OBSERVED_AT', TRUE, %s, %s)
                RETURNING id
                """,
                (
                    observation_id,
                    response_id,
                    now + timedelta(seconds=1),
                    response_observed_at,
                    payload_hash,
                    response_observed_at,
                ),
            ).fetchone()[0]

            store.record_pre_match_feature_observation(
                target_fixture_id=target_fixture_id,
                source_observation_id=observation_id,
                source_sighting_id=sighting_id,
                feature_key="system_observed.allowed",
                feature_value={"value": 1},
                prediction_cutoff_at=now + timedelta(minutes=5),
            )

            with (
                pytest.raises(
                    psycopg.errors.RaiseException,
                    match="PRE_MATCH_RESPONSE_PROVENANCE_INVALID",
                ),
                connection.transaction(),
            ):
                connection.execute(
                    """
                    INSERT INTO veltrix_ai_analyst.pre_match_feature_observations (
                        target_fixture_id, source_observation_id, source_sighting_id,
                    feature_key, feature_value, prediction_cutoff_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        target_fixture_id,
                        observation_id,
                        mismatched_sighting_id,
                        "system_observed.response_time_mismatch",
                        Jsonb({"value": 3}),
                        now + timedelta(minutes=5),
                    ),
                )

            with (
                pytest.raises(
                    psycopg.errors.RaiseException,
                    match="PRE_MATCH_SYSTEM_OBSERVATION_NOT_AVAILABLE_AT_CUTOFF",
                ),
                connection.transaction(),
            ):
                connection.execute(
                    """
                    INSERT INTO veltrix_ai_analyst.pre_match_feature_observations (
                        target_fixture_id, source_observation_id, source_sighting_id,
                    feature_key, feature_value, prediction_cutoff_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        target_fixture_id,
                        observation_id,
                        sighting_id,
                        "system_observed.must_be_rejected",
                        Jsonb({"value": 2}),
                        now - timedelta(seconds=1),
                    ),
                )

            counts = connection.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE feature_key = 'system_observed.allowed'),
                    COUNT(*) FILTER (WHERE feature_key = 'system_observed.must_be_rejected')
                FROM veltrix_ai_analyst.pre_match_feature_observations
                WHERE source_observation_id = %s
                """,
                (observation_id,),
            ).fetchone()

    assert counts == (1, 0)
