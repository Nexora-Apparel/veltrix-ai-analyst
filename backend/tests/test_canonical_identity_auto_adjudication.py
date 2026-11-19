from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest


def _insert_pit_case(connection: psycopg.Connection, label: str) -> int:
    row = connection.execute(
        """
        INSERT INTO veltrix_ai_analyst.canonical_identity_review_cases (
            case_key,
            case_type,
            recommended_action,
            evidence_uris,
            evidence_summary
        )
        VALUES (%s, 'PIT_TIMESTAMP_GAP', 'EXCLUDE_FROM_PIT_FEATURES', ARRAY['urn:test:evidence'], %s)
        RETURNING id
        """,
        (f"AUTO_ADJUDICATION_TEST_{label}_{uuid4().hex}", "Synthetic PIT case for automated disposition tests."),
    ).fetchone()
    assert row is not None
    return int(row[0])


def test_automated_deferred_disposition_closes_human_action_queue(connection) -> None:
    case_id = _insert_pit_case(connection, "DEFERRED")
    connection.execute(
        """
        INSERT INTO veltrix_ai_analyst.canonical_identity_review_case_events (
            case_id, event_type, reviewer_type, reviewer_id, reviewed_at,
            evidence_uri, evidence_sha256, notes, policy_version, confidence, decision_basis
        )
        VALUES (
            %s, 'AUTOMATED_DEFERRED', 'AUTOMATED_SYSTEM', 'test-policy-deferred',
            %s, 'urn:test:pit-audit', %s, 'Historical PIT evidence is absent; exclude the rows.',
            'test-policy-v1', 1.0000, 'MISSING_SOURCE_AVAILABILITY_TIMESTAMPS'
        )
        """,
        (case_id, datetime.now(UTC), "a" * 64),
    )
    row = connection.execute(
        """
        SELECT effective_case_status, effective_human_review_required,
               latest_policy_version, latest_confidence, latest_decision_basis
        FROM veltrix_ai_analyst.effective_canonical_identity_review_cases
        WHERE id = %s
        """,
        (case_id,),
    ).fetchone()
    assert row is not None
    assert row[0] == "AUTOMATED_DEFERRED"
    assert row[1] is False
    assert row[2] == "test-policy-v1"
    assert float(row[3]) == 1.0
    assert row[4] == "MISSING_SOURCE_AVAILABILITY_TIMESTAMPS"


def test_automated_confirmation_requires_policy_and_evidence(connection) -> None:
    case_id = _insert_pit_case(connection, "INVALID")
    with pytest.raises(psycopg.errors.CheckViolation):
        with connection.transaction():
            connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.canonical_identity_review_case_events (
                    case_id, event_type, reviewer_type, reviewer_id, reviewed_at,
                    evidence_uri, evidence_sha256, notes
                )
                VALUES (
                    %s, 'AUTOMATED_CONFIRMED', 'AUTOMATED_SYSTEM', 'test-policy-invalid',
                    %s, 'urn:test:evidence', %s, 'Missing policy metadata must fail.'
                )
                """,
                (case_id, datetime.now(UTC), "b" * 64),
            )


def test_automated_case_confirmation_does_not_enable_automatic_merges(connection) -> None:
    alias_view = connection.execute(
        "SELECT pg_get_viewdef('veltrix_ai_analyst.effective_canonical_team_aliases'::regclass)"
    ).fetchone()[0]
    fixture_view = connection.execute(
        "SELECT pg_get_viewdef('veltrix_ai_analyst.effective_canonical_fixture_deduplication'::regclass)"
    ).fetchone()[0]
    assert "HUMAN_CONFIRMED" in alias_view
    assert "AUTOMATED_CONFIRMED" not in alias_view
    assert "HUMAN_CONFIRMED" in fixture_view
    assert "AUTOMATED_CONFIRMED" not in fixture_view
