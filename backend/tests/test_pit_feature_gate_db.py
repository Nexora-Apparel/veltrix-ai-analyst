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


@pytest.fixture
def database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not url or not database:
        pytest.skip("PostgreSQL integration service is not configured")
    apply_migrations(url, expected_database=database)
    return url


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

            connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.pre_match_feature_observations (
                    source_observation_id, source_sighting_id, feature_key,
                    feature_value, prediction_cutoff_at
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    eligible_observation_id,
                    eligible_sighting_id,
                    "test.feature",
                    Jsonb({"value": 1}),
                    cutoff_at,
                ),
            )

            with (
                pytest.raises(
                    psycopg.errors.RaiseException,
                    match="PRE_MATCH_SOURCE_PUBLICATION_EVIDENCE_REQUIRED",
                ),
                connection.transaction(),
            ):
                connection.execute(
                        """
                        INSERT INTO veltrix_ai_analyst.pre_match_feature_observations (
                            source_observation_id, source_sighting_id, feature_key,
                            feature_value, prediction_cutoff_at
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                    (
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
