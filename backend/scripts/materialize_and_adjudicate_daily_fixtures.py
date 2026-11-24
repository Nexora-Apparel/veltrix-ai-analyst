"""Materialize approved prospective scopes and adjudicate exact source-local fixture links.

This operation creates no provider requests and performs no cross-provider merges.
It only verifies an exact provider-fixture-ID link when the source evidence,
canonical team/competition mappings, rights and duplicate checks all pass.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlsplit
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.canonical_fixture_adjudication import (
    EVIDENCE_URI,
    POLICY_VERSION,
    REVIEWED_MAPPING_STATUSES,
    REVIEWER_ID,
    evidence_sha256,
    find_fixture_link_collisions,
)
from app.canonicalization import (
    BRAZIL_SERIE_B_RUN_3,
    CanonicalMaterializationScope,
    build_canonical_materialization_plan,
    materialize_canonical_entities,
)
from app.providers.prospective_capture_scope import PROSPECTIVE_CAPTURE_COMPETITIONS

EXPECTED_DATABASE = "veltrix_ai_analyst"
EXPECTED_PROVIDER = "5DollarFootballAPI"
EXPECTED_SOURCE_ID = "5dollarfootballapi"
CONFIRMATION = "RUN_DAILY_EXACT_SOURCE_FIXTURE_LINK_ADJUDICATION_V1"
REQUIRED_USES = {"FEATURE_ENGINEERING", "MODEL_TRAINING", "MODEL_VALIDATION"}


def _approved_scopes(connection: psycopg.Connection[Any]) -> list[CanonicalMaterializationScope]:
    expected_ids = {competition_id for competition_id, _ in PROSPECTIVE_CAPTURE_COMPETITIONS}
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT approval.approval_id, approval.provider, approval.source_id,
                   approval.scope_values, approval.valid_from, approval.valid_until,
                   COALESCE(latest.status, approval.status) AS effective_status
            FROM veltrix_ai_analyst.source_approvals approval
            LEFT JOIN LATERAL (
                SELECT event.status
                FROM veltrix_ai_analyst.source_approval_status_events event
                WHERE event.approval_id = approval.approval_id
                  AND event.effective_at <= statement_timestamp()
                ORDER BY event.effective_at DESC, event.id DESC
                LIMIT 1
            ) latest ON TRUE
            WHERE approval.provider = %s
              AND approval.source_id = %s
              AND approval.scope_type = 'competition_id'
              AND COALESCE(latest.status, approval.status) = 'APPROVED'
              AND approval.valid_from <= statement_timestamp()
              AND (approval.valid_until IS NULL
                   OR approval.valid_until > statement_timestamp())
            ORDER BY approval.approval_id
            """,
            (EXPECTED_PROVIDER, EXPECTED_SOURCE_ID),
        )
        approvals = cursor.fetchall()

    scope_candidates: dict[str, list[dict[str, Any]]] = {
        competition_id: [] for competition_id in expected_ids
    }
    for approval in approvals:
        values = approval["scope_values"]
        if isinstance(values, str):
            values = json.loads(values)
        for competition_id in expected_ids.intersection(map(str, values or [])):
            scope_candidates[competition_id].append(approval)

    missing_or_ambiguous = [
        competition_id
        for competition_id, matches in scope_candidates.items()
        if len(matches) != 1
    ]
    if missing_or_ambiguous:
        raise RuntimeError(
            "APPROVED_CAPTURE_SCOPE_MISSING_OR_AMBIGUOUS:"
            + ",".join(sorted(missing_or_ambiguous))
        )

    scopes = []
    for competition_id in sorted(expected_ids):
        approval = scope_candidates[competition_id][0]
        alias_pairs = (
            BRAZIL_SERIE_B_RUN_3.identity_collision_team_alias_pairs
            if competition_id == BRAZIL_SERIE_B_RUN_3.competition_id
            else ()
        )
        scopes.append(
            CanonicalMaterializationScope(
                provider=EXPECTED_PROVIDER,
                source_id=EXPECTED_SOURCE_ID,
                competition_id=competition_id,
                rights_approval_id=approval["approval_id"],
                import_run_id=None,
                identity_collision_team_alias_pairs=alias_pairs,
            )
        )
    return scopes


def _fixture_links_for_adjudication(
    connection: psycopg.Connection[Any],
    scope: CanonicalMaterializationScope,
) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
                link.id AS link_id,
                link.provider_fixture_id,
                link.mapping_method,
                link.source_observation_id,
                link.source_sighting_id,
                link.provider_response_id,
                link.rights_approval_id,
                link.payload_sha256,
                provider_fixture.id AS provider_fixture_row_id,
                provider_fixture.provider_fixture_id AS provider_fixture_row_fixture_id,
                provider_fixture.provider_competition_id,
                provider_fixture.home_team_provider_id,
                provider_fixture.away_team_provider_id,
                provider_fixture.kickoff_at,
                provider_fixture.status,
                provider_fixture.home_goals,
                provider_fixture.away_goals,
                canonical_fixture.id AS canonical_fixture_id,
                canonical_fixture.canonical_competition_id,
                canonical_fixture.home_canonical_team_id,
                canonical_fixture.away_canonical_team_id,
                canonical_fixture.kickoff_at AS canonical_kickoff_at,
                canonical_fixture.status AS canonical_status,
                canonical_fixture.home_goals AS canonical_home_goals,
                canonical_fixture.away_goals AS canonical_away_goals,
                canonical_fixture.identity_status,
                provenance.source_fixture_provenance_status,
                home_link.effective_mapping_status AS home_mapping_status,
                away_link.effective_mapping_status AS away_mapping_status,
                competition_link.effective_mapping_status AS competition_mapping_status,
                observation.provider AS observation_provider,
                observation.source_id AS observation_source_id,
                observation.data_type,
                observation.entity_type,
                observation.provider_entity_id,
                observation.payload_sha256 AS observation_payload_sha256,
                observation.rights_approval_id AS observation_approval_id,
                sighting.payload_sha256 AS sighting_payload_sha256,
                sighting.provider_response_id AS sighting_response_id,
                sighting.retrieved_at,
                sighting.system_observed_at,
                response.provider AS response_provider,
                response.source_id AS response_source_id,
                response.http_status,
                response.rights_approval_id AS response_approval_id,
                response.fetched_at AS response_fetched_at,
                response.system_observed_at AS response_system_observed_at,
                response.response_sha256,
                approval.provider AS approval_provider,
                approval.source_id AS approval_source_id,
                approval.status AS approval_status,
                approval.valid_from AS approval_valid_from,
                approval.valid_until AS approval_valid_until,
                approval.permitted_uses,
                COALESCE(approval_event.status, approval.status) AS effective_approval_status,
                approval_event.status AS observed_approval_event_status,
                COUNT(*) OVER (PARTITION BY canonical_fixture.id) AS canonical_source_count,
                latest_review.id AS latest_review_event_id,
                latest_review.decision AS latest_review_decision
            FROM veltrix_ai_analyst.canonical_fixture_sources link
            JOIN veltrix_ai_analyst.provider_fixtures provider_fixture
              ON provider_fixture.id = link.provider_fixture_row_id
            JOIN veltrix_ai_analyst.canonical_fixtures canonical_fixture
              ON canonical_fixture.id = link.canonical_fixture_id
            LEFT JOIN veltrix_ai_analyst.canonical_fixture_source_provenance_audit provenance
              ON provenance.fixture_source_link_id = link.id
            LEFT JOIN veltrix_ai_analyst.effective_provider_team_identity_links home_link
              ON home_link.provider = provider_fixture.provider
             AND home_link.source_id = provider_fixture.source_id
             AND home_link.provider_team_id = provider_fixture.home_team_provider_id
            LEFT JOIN veltrix_ai_analyst.effective_provider_team_identity_links away_link
              ON away_link.provider = provider_fixture.provider
             AND away_link.source_id = provider_fixture.source_id
             AND away_link.provider_team_id = provider_fixture.away_team_provider_id
            LEFT JOIN veltrix_ai_analyst.effective_provider_competition_identity_links competition_link
              ON competition_link.provider = provider_fixture.provider
             AND competition_link.source_id = provider_fixture.source_id
             AND competition_link.provider_competition_id = provider_fixture.provider_competition_id
            JOIN veltrix_ai_analyst.source_observations observation
              ON observation.id = link.source_observation_id
            JOIN veltrix_ai_analyst.source_observation_sightings sighting
              ON sighting.id = link.source_sighting_id
             AND sighting.source_observation_id = observation.id
            JOIN veltrix_ai_analyst.provider_responses response
              ON response.id = link.provider_response_id
            JOIN veltrix_ai_analyst.source_approvals approval
              ON approval.approval_id = link.rights_approval_id
            LEFT JOIN LATERAL (
                SELECT event.status
                FROM veltrix_ai_analyst.source_approval_status_events event
                WHERE event.approval_id = approval.approval_id
                  AND event.effective_at <= COALESCE(sighting.system_observed_at, sighting.retrieved_at)
                ORDER BY event.effective_at DESC, event.id DESC
                LIMIT 1
            ) approval_event ON TRUE
            LEFT JOIN LATERAL (
                SELECT event.id, event.decision
                FROM veltrix_ai_analyst.canonical_identity_review_events event
                WHERE event.fixture_source_link_id = link.id
                ORDER BY event.reviewed_at DESC, event.id DESC
                LIMIT 1
            ) latest_review ON TRUE
            WHERE link.provider = %s
              AND link.source_id = %s
              AND provider_fixture.provider_competition_id = %s
            ORDER BY provider_fixture.kickoff_at, link.id
            """,
            (scope.provider, scope.source_id, scope.competition_id),
        )
        return list(cursor.fetchall())


def _provenance_is_valid(row: dict[str, Any]) -> bool:
    observed_at = row["system_observed_at"] or row["retrieved_at"]
    permitted_uses = set(row["permitted_uses"] or ())
    return bool(
        row["mapping_method"] == "EXACT_PROVIDER_FIXTURE_ID"
        and row["provider_fixture_id"] == row["provider_fixture_row_fixture_id"]
        and row["provider_fixture_id"] == row["provider_entity_id"]
        and row["source_fixture_provenance_status"] == "PROVENANCE_VERIFIED"
        and row["observation_provider"] == EXPECTED_PROVIDER
        and row["observation_source_id"] == EXPECTED_SOURCE_ID
        and row["data_type"] == "fixtures_and_results"
        and row["entity_type"] == "fixture"
        and row["observation_payload_sha256"] == row["payload_sha256"]
        and row["observation_approval_id"] == row["rights_approval_id"]
        and row["sighting_payload_sha256"] == row["payload_sha256"]
        and row["sighting_response_id"] == row["provider_response_id"]
        and row["response_provider"] == EXPECTED_PROVIDER
        and row["response_source_id"] == EXPECTED_SOURCE_ID
        and row["response_approval_id"] == row["rights_approval_id"]
        and row["response_fetched_at"] == row["retrieved_at"]
        and row["response_system_observed_at"] == row["system_observed_at"]
        and len(str(row["response_sha256"] or "").strip()) == 64
        and row["http_status"] is not None
        and 200 <= int(row["http_status"]) <= 299
        and row["approval_provider"] == EXPECTED_PROVIDER
        and row["approval_source_id"] == EXPECTED_SOURCE_ID
        and row["effective_approval_status"] == "APPROVED"
        and row["approval_valid_from"] <= observed_at
        and (
            row["approval_valid_until"] is None
            or row["approval_valid_until"] > observed_at
        )
        and REQUIRED_USES.issubset(permitted_uses)
        and int(row["canonical_source_count"]) == 1
        and row["kickoff_at"] == row["canonical_kickoff_at"]
        and row["status"] == row["canonical_status"]
        and row["home_goals"] == row["canonical_home_goals"]
        and row["away_goals"] == row["canonical_away_goals"]
    )


def _identity_mappings_are_reviewed(row: dict[str, Any]) -> bool:
    return (
        row["home_mapping_status"] in REVIEWED_MAPPING_STATUSES
        and row["away_mapping_status"] in REVIEWED_MAPPING_STATUSES
        and row["competition_mapping_status"] in REVIEWED_MAPPING_STATUSES
    )


def _adjudicate_scope(
    connection: psycopg.Connection[Any],
    scope: CanonicalMaterializationScope,
) -> dict[str, int]:
    rows = _fixture_links_for_adjudication(connection, scope)
    collisions = find_fixture_link_collisions(rows)
    reviewed = 0
    conflicts = 0
    pending = 0

    for row in rows:
        # Never replace an existing human or automated review decision.
        if row["latest_review_event_id"] is not None:
            continue
        if not _provenance_is_valid(row):
            pending += 1
            continue

        collision_ids = collisions.get(int(row["link_id"]), ())
        mappings_reviewed = _identity_mappings_are_reviewed(row)
        decision = (
            "CONFLICT"
            if row["identity_status"] == "CONFLICT"
            else "CONFLICT"
            if collision_ids and mappings_reviewed
            else "SOURCE_FIXTURE_LINK_REVIEWED"
            if mappings_reviewed
            else None
        )
        if decision is None:
            pending += 1
            continue

        evidence = {
            "policy_version": POLICY_VERSION,
            "decision": decision,
            "provider": scope.provider,
            "source_id": scope.source_id,
            "competition_id": scope.competition_id,
            "provider_fixture_row_id": int(row["provider_fixture_row_id"]),
            "provider_fixture_id": row["provider_fixture_id"],
            "provider_home_team_id": row["home_team_provider_id"],
            "provider_away_team_id": row["away_team_provider_id"],
            "source_observation_id": int(row["source_observation_id"]),
            "source_sighting_id": int(row["source_sighting_id"]),
            "provider_response_id": int(row["provider_response_id"]),
            "payload_sha256": str(row["payload_sha256"]).strip(),
            "response_sha256": str(row["response_sha256"]).strip(),
            "retrieved_at": row["retrieved_at"],
            "system_observed_at": row["system_observed_at"],
            "approval_provider": row["approval_provider"],
            "approval_source_id": row["approval_source_id"],
            "effective_approval_status": row["effective_approval_status"],
            "approval_valid_from": row["approval_valid_from"],
            "approval_valid_until": row["approval_valid_until"],
            "permitted_uses": sorted(row["permitted_uses"] or ()),
            "rights_approval_id": row["rights_approval_id"],
            "canonical_fixture_id": str(row["canonical_fixture_id"]),
            "canonical_competition_id": str(row["canonical_competition_id"]),
            "home_canonical_team_id": str(row["home_canonical_team_id"]),
            "away_canonical_team_id": str(row["away_canonical_team_id"]),
            "kickoff_at": row["kickoff_at"],
            "status": row["status"],
            "home_goals": row["home_goals"],
            "away_goals": row["away_goals"],
            "home_mapping_status": row["home_mapping_status"],
            "away_mapping_status": row["away_mapping_status"],
            "competition_mapping_status": row["competition_mapping_status"],
            "collision_link_ids": list(collision_ids),
        }
        digest = evidence_sha256(evidence)
        notes = (
            f"{POLICY_VERSION}: exact provider fixture ID, immutable source "
            "observation/sighting/response provenance, effective source rights, "
            "reviewed canonical team and competition mappings, exact copied "
            "fixture facts, one source per canonical fixture, and the 120-second "
            "canonical-team collision check. No cross-provider merge or source "
            "row mutation."
        )
        connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.canonical_identity_review_events (
                fixture_source_link_id, decision, reviewer_id, reviewed_at,
                evidence_uri, evidence_sha256, notes
            )
            VALUES (%s, %s, %s, statement_timestamp(), %s, %s, %s)
            """,
            (
                row["link_id"],
                decision,
                REVIEWER_ID,
                EVIDENCE_URI,
                digest,
                notes,
            ),
        )
        connection.execute(
            """
            UPDATE veltrix_ai_analyst.canonical_fixtures
            SET identity_status = %s
            WHERE id = %s
              AND identity_status IN ('IDENTITY_REVIEW_REQUIRED', 'CONFLICT')
            """,
            (
                "CONFLICT" if decision == "CONFLICT" else "VERIFIED",
                row["canonical_fixture_id"],
            ),
        )
        if decision == "CONFLICT":
            conflicts += 1
        else:
            reviewed += 1

    return {
        "links_seen": len(rows),
        "links_reviewed": reviewed,
        "links_conflicted": conflicts,
        "links_pending": pending,
    }


def run(connection: psycopg.Connection[Any]) -> dict[str, Any]:
    scopes = _approved_scopes(connection)
    if len(scopes) != len(PROSPECTIVE_CAPTURE_COMPETITIONS):
        raise RuntimeError("APPROVED_PROSPECTIVE_SCOPE_COUNT_MISMATCH")

    plans = [
        (scope, build_canonical_materialization_plan(connection, scope))
        for scope in scopes
    ]
    blocked = [
        {
            "competition_id": scope.competition_id,
            "blockers": list(plan.blockers),
        }
        for scope, plan in plans
        if not plan.ready
    ]
    if blocked:
        raise RuntimeError(
            "CANONICAL_SCOPE_PREFLIGHT_BLOCKED:" + json.dumps(blocked, sort_keys=True)
        )

    materialized = []
    adjudication = []
    for scope, _ in plans:
        result = materialize_canonical_entities(
            connection,
            execute=True,
            scope=scope,
        )
        materialized.append(
            {
                "competition_id": scope.competition_id,
                "fixtures_created": int(result["fixtures_created"]),
                "fixtures_reused": int(result["fixtures_reused"]),
                "teams_created": int(result["teams_created"]),
                "competition_created": bool(result["competition_created"]),
                "provider_requests_made": int(result["provider_requests_made"]),
            }
        )
        adjudication.append(
            {
                "competition_id": scope.competition_id,
                **_adjudicate_scope(connection, scope),
            }
        )

    competition_ids = [scope.competition_id for scope in scopes]
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_upcoming,
                COUNT(*) FILTER (
                    WHERE link.id IS NOT NULL
                      AND effective_link.effective_mapping_status = 'SOURCE_FIXTURE_LINK_REVIEWED'
                      AND canonical_fixture.identity_status = 'VERIFIED'
                ) AS eligible_upcoming,
                COUNT(*) FILTER (
                    WHERE link.id IS NOT NULL
                      AND effective_link.effective_mapping_status = 'CONFLICT'
                      AND canonical_fixture.identity_status = 'CONFLICT'
                ) AS conflicted_upcoming,
                COUNT(*) FILTER (
                    WHERE link.id IS NULL
                       OR effective_link.effective_mapping_status NOT IN (
                           'SOURCE_FIXTURE_LINK_REVIEWED', 'CONFLICT'
                       )
                       OR canonical_fixture.identity_status NOT IN ('VERIFIED', 'CONFLICT')
                ) AS unresolved_upcoming
            FROM veltrix_ai_analyst.provider_fixtures provider_fixture
            LEFT JOIN veltrix_ai_analyst.canonical_fixture_sources link
              ON link.provider_fixture_row_id = provider_fixture.id
            LEFT JOIN veltrix_ai_analyst.effective_canonical_fixture_sources effective_link
              ON effective_link.id = link.id
            LEFT JOIN veltrix_ai_analyst.canonical_fixtures canonical_fixture
              ON canonical_fixture.id = link.canonical_fixture_id
            WHERE provider_fixture.provider = %s
              AND provider_fixture.source_id = %s
              AND provider_fixture.provider_competition_id = ANY(%s)
              AND provider_fixture.status = 'SCHEDULED'
              AND provider_fixture.kickoff_at > statement_timestamp()
            """,
            (EXPECTED_PROVIDER, EXPECTED_SOURCE_ID, competition_ids),
        )
        coverage = cursor.fetchone()

    if int(coverage["unresolved_upcoming"]) > 0:
        raise RuntimeError(
            "UPCOMING_CANONICAL_FIXTURE_LINKS_UNRESOLVED:"
            + str(coverage["unresolved_upcoming"])
        )
    if int(coverage["total_upcoming"]) > 0 and int(coverage["eligible_upcoming"]) < 1:
        raise RuntimeError("NO_ELIGIBLE_UPCOMING_CANONICAL_FIXTURES")

    return {
        "status": "DAILY_CANONICAL_FIXTURE_LINKAGE_VERIFIED",
        "database": EXPECTED_DATABASE,
        "policy_version": POLICY_VERSION,
        "reviewer_id": REVIEWER_ID,
        "provider_requests_made": 0,
        "materialized_scopes": materialized,
        "adjudication_scopes": adjudication,
        "upcoming_fixture_coverage": {
            "total": int(coverage["total_upcoming"]),
            "eligible": int(coverage["eligible_upcoming"]),
            "conflicted_excluded": int(coverage["conflicted_upcoming"]),
            "unresolved": int(coverage["unresolved_upcoming"]),
        },
    }


def main() -> int:
    if os.environ.get("VELTRIX_DAILY_CANONICALIZATION_CONFIRMATION") != CONFIRMATION:
        raise SystemExit("DAILY_CANONICALIZATION_CONFIRMATION_REQUIRED")
    database_url = os.environ.get("DATABASE_URL", "").strip()
    expected_database = os.environ.get("EXPECTED_DATABASE_NAME", "")
    if not database_url or expected_database != EXPECTED_DATABASE:
        raise SystemExit("DAILY_CANONICALIZATION_DATABASE_CONFIGURATION_INVALID")
    if urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != EXPECTED_DATABASE:
        raise SystemExit("DAILY_CANONICALIZATION_DATABASE_URL_TARGET_MISMATCH")

    try:
        with psycopg.connect(database_url, autocommit=True) as connection:
            if connection.info.dbname != EXPECTED_DATABASE:
                raise SystemExit("DAILY_CANONICALIZATION_CONNECTED_DATABASE_MISMATCH")
            with connection.transaction():
                connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                connection.execute("SET LOCAL lock_timeout = '15s'")
                connection.execute("SET LOCAL statement_timeout = '600s'")
                report = run(connection)
            print(json.dumps(report, sort_keys=True, indent=2, default=str))
    except (psycopg.Error, OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(
            f"DAILY_CANONICAL_FIXTURE_LINKAGE_FAILED:{type(exc).__name__}:{str(exc)[:1200]}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
