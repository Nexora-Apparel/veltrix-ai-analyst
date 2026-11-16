import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from app.db.migrations import MigrationError, apply_migrations


def database_config() -> tuple[str, str]:
    url = os.getenv("DATABASE_URL", "")
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    if not url or not expected_database:
        pytest.skip("PostgreSQL integration service is not configured")
    return url, expected_database


def seed_approval(connection: psycopg.Connection, approval_id: str, source_id: str) -> None:
    now = datetime.now(UTC)
    connection.execute(
        """
        INSERT INTO veltrix_ai_analyst.source_approvals (
            approval_id, provider, source_id, scope_type, scope_values, data_types,
            status, rights_basis, terms_url, terms_version, evidence_uri,
            evidence_sha256, reviewed_at, reviewer_id, valid_from, permitted_uses
        ) VALUES (
            %s, 'test-provider', %s, 'competition_id',
            '["league-1"]'::jsonb, '["fixtures_and_results"]'::jsonb,
            'APPROVED', 'TERMS', 'https://example.test/terms', 'v1',
            'https://example.test/evidence', %s, %s, 'ci-test', %s,
            '["COLLECTION","STORAGE"]'::jsonb
        )
        """,
        (approval_id, source_id, "a" * 64, now, now),
    )


def seed_fixture_dependencies(
    connection: psycopg.Connection, approval_id: str, source_id: str, suffix: str
) -> tuple[int, int]:
    now = datetime.now(UTC)
    raw = b'{"success":1,"data":[]}'
    response_hash = hashlib.sha256(raw).hexdigest()
    response = connection.execute(
        """
        INSERT INTO veltrix_ai_analyst.provider_responses (
            provider, source_id, endpoint, request_id, http_status,
            response_sha256, raw_body, rights_approval_id, fetched_at
        ) VALUES (
            'test-provider', %s, '/fixtures', %s,
            200, %s, %s, %s, %s
        ) RETURNING id
        """,
        (source_id, f"request-{suffix}", response_hash, raw, approval_id, now),
    ).fetchone()
    assert response is not None

    payload = {"fixture": "fixture-1"}
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    observation = connection.execute(
        """
        INSERT INTO veltrix_ai_analyst.source_observations (
            provider, source_id, data_type, entity_type, provider_entity_id,
            payload_sha256, schema_version, retrieved_at, availability_basis,
            rights_approval_id, provider_response_id, payload
        ) VALUES (
            'test-provider', %s, 'fixtures_and_results', 'fixture',
            %s, %s, 'v1', %s, 'RETRIEVED_AT_ONLY',
            %s, %s, %s
        ) RETURNING id
        """,
        (source_id, f"fixture-{suffix}", payload_hash, now, approval_id, response[0], json.dumps(payload)),
    ).fetchone()
    assert observation is not None

    connection.execute(
        """
        INSERT INTO veltrix_ai_analyst.provider_competitions (
            provider, source_id, provider_competition_id, name,
            source_observation_id, rights_approval_id, first_seen_at, last_seen_at
        ) VALUES (
            'test-provider', %s, 'league-1', 'Test League',
            %s, %s, %s, %s
        )
        """,
        (source_id, observation[0], approval_id, now, now),
    )
    for team_id, team_name in (("home", "Home FC"), ("away", "Away FC")):
        connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.provider_teams (
                provider, source_id, provider_team_id, name,
                source_observation_id, rights_approval_id, first_seen_at, last_seen_at
            ) VALUES (
                'test-provider', %s, %s, %s,
                %s, %s, %s, %s
            )
            """,
            (source_id, f"{team_id}-{suffix}", team_name, observation[0], approval_id, now, now),
        )
    return int(observation[0]), int(response[0])


def test_migrations_are_idempotent_and_provenance_constraints_hold() -> None:
    database_url, expected_database = database_config()
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"

    applied = apply_migrations(
        database_url,
        expected_database=expected_database,
        migrations_dir=migrations_dir,
    )
    assert set(applied).issubset({"001_provenance_ingestion.sql"})

    assert apply_migrations(
        database_url,
        expected_database=expected_database,
        migrations_dir=migrations_dir,
    ) == []

    with psycopg.connect(database_url) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'veltrix_ai_analyst'
                """
            ).fetchall()
        }
        assert {
            "source_approvals",
            "provider_responses",
            "provider_entitlement_observations",
            "source_observations",
            "provider_competitions",
            "provider_teams",
            "provider_fixtures",
            "import_runs",
            "import_checkpoints",
            "sync_watermarks",
            "ingestion_quarantine",
        }.issubset(tables)

        suffix = uuid4().hex
        approval_id = f"test-approval-{suffix}"
        source_id = f"test-source-{suffix}"
        seed_approval(connection, approval_id, source_id)
        observation_id, _ = seed_fixture_dependencies(
            connection, approval_id, source_id, suffix
        )
        now = datetime.now(UTC)

        with pytest.raises(psycopg.errors.CheckViolation):
            with connection.transaction():
                connection.execute(
                    """
                    INSERT INTO veltrix_ai_analyst.provider_fixtures (
                        provider, source_id, provider_fixture_id, provider_competition_id,
                        home_team_provider_id, away_team_provider_id, kickoff_at, status,
                        source_observation_id, rights_approval_id, first_seen_at, last_seen_at
                    ) VALUES (
                        'test-provider', %s, %s, 'league-1',
                        %s, %s, %s, 'FINISHED', %s, %s, %s, %s
                    )
                    """,
                    (
                        source_id,
                        f"fixture-{suffix}",
                        f"home-{suffix}",
                        f"away-{suffix}",
                        now,
                        observation_id,
                        approval_id,
                        now,
                        now,
                    ),
                )

        with pytest.raises(psycopg.errors.RaiseException):
            with connection.transaction():
                connection.execute(
                    """
                    UPDATE veltrix_ai_analyst.source_observations
                    SET payload = '{"tampered":true}'::jsonb
                    WHERE id = %s
                    """,
                    (observation_id,),
                )


def test_migration_runner_rejects_wrong_database_target() -> None:
    database_url, expected_database = database_config()
    with pytest.raises(MigrationError, match="DATABASE_TARGET_NAME_MISMATCH"):
        apply_migrations(
            database_url,
            expected_database=f"{expected_database}_wrong",
        )



def test_migration_runner_refuses_remote_database_without_opt_in() -> None:
    with pytest.raises(MigrationError, match="REMOTE_DATABASE_MIGRATIONS_DISABLED"):
        apply_migrations(
            "postgresql://user:password@db.example.test:5432/veltrix_ai_analyst",
            expected_database="veltrix_ai_analyst",
        )
