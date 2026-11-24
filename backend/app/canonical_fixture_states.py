"""Append-only PIT-backed synchronization of canonical fixture current-state projections."""
from __future__ import annotations

from typing import Any, Sequence

import psycopg

EXPECTED_PROVIDER = "5DollarFootballAPI"
EXPECTED_SOURCE_ID = "5dollarfootballapi"


def sync_canonical_fixture_states(
    connection: psycopg.Connection[Any],
    competition_ids: Sequence[str],
) -> dict[str, int]:
    """Append the latest valid PIT state event for reviewed canonical fixture links.

    Source observations remain immutable. The database trigger updates only the
    canonical fixture's current status/score projection from the appended event.
    """
    ids = sorted({str(value) for value in competition_ids})
    if not ids:
        return {"state_events_inserted": 0, "state_provenance_verified": 0}

    inserted = connection.execute(
        """
        WITH ranked AS (
            SELECT
                fixture.id AS provider_fixture_row_id,
                fixture.provider_fixture_id,
                fixture.provider_competition_id,
                fixture.home_team_provider_id,
                fixture.away_team_provider_id,
                source_link.id AS fixture_source_link_id,
                canonical.id AS canonical_fixture_id,
                observation.id AS source_observation_id,
                sighting.id AS source_sighting_id,
                sighting.provider_response_id,
                observation.rights_approval_id,
                observation.payload_sha256,
                response.response_sha256,
                sighting.system_observed_at AS observed_at,
                fixture.kickoff_at,
                fixture.status,
                fixture.home_goals,
                fixture.away_goals,
                observation.payload,
                observation.provider AS observation_provider,
                observation.source_id AS observation_source_id,
                observation.data_type,
                observation.entity_type,
                observation.provider_entity_id,
                sighting.payload_sha256 AS sighting_payload_sha256,
                sighting.retrieved_at,
                sighting.available_at,
                sighting.source_published_at,
                sighting.availability_basis,
                sighting.point_in_time_certifiable,
                response.provider AS response_provider,
                response.source_id AS response_source_id,
                response.http_status,
                response.fetched_at,
                response.system_observed_at AS response_system_observed_at,
                response.rights_approval_id AS response_approval_id,
                approval.provider AS approval_provider,
                approval.source_id AS approval_source_id,
                approval.scope_type AS approval_scope_type,
                approval.scope_values AS approval_scope_values,
                approval.valid_from,
                approval.valid_until,
                approval.permitted_uses,
                COALESCE(approval_event.status, approval.status)
                    AS effective_approval_status,
                ROW_NUMBER() OVER (
                    PARTITION BY fixture.id
                    ORDER BY
                        COALESCE(
                            sighting.system_observed_at,
                            sighting.retrieved_at,
                            observation.retrieved_at
                        ) DESC,
                        sighting.id DESC NULLS LAST,
                        observation.id DESC
                ) AS observation_rank
            FROM veltrix_ai_analyst.provider_fixtures fixture
            JOIN veltrix_ai_analyst.canonical_fixture_sources source_link
              ON source_link.provider_fixture_row_id = fixture.id
            JOIN veltrix_ai_analyst.effective_canonical_fixture_sources effective_link
              ON effective_link.id = source_link.id
             AND effective_link.effective_mapping_status = 'SOURCE_FIXTURE_LINK_REVIEWED'
             AND source_link.mapping_method = 'EXACT_PROVIDER_FIXTURE_ID'
            JOIN veltrix_ai_analyst.canonical_fixtures canonical
              ON canonical.id = source_link.canonical_fixture_id
             AND canonical.identity_status = 'VERIFIED'
            JOIN veltrix_ai_analyst.source_observations observation
              ON observation.provider = fixture.provider
             AND observation.source_id = fixture.source_id
             AND observation.data_type = 'fixtures_and_results'
             AND observation.entity_type = 'fixture'
             AND observation.provider_entity_id = fixture.provider_fixture_id
            LEFT JOIN LATERAL (
                SELECT candidate.*
                FROM veltrix_ai_analyst.source_observation_sightings candidate
                WHERE candidate.source_observation_id = observation.id
                ORDER BY
                    COALESCE(candidate.system_observed_at, candidate.retrieved_at) DESC,
                    candidate.id DESC
                LIMIT 1
            ) sighting ON TRUE
            LEFT JOIN veltrix_ai_analyst.provider_responses response
              ON response.id = sighting.provider_response_id
            LEFT JOIN veltrix_ai_analyst.source_approvals approval
              ON approval.approval_id = observation.rights_approval_id
            LEFT JOIN LATERAL (
                SELECT event.status
                FROM veltrix_ai_analyst.source_approval_status_events event
                WHERE event.approval_id = approval.approval_id
                  AND event.effective_at <= COALESCE(
                      sighting.system_observed_at,
                      sighting.retrieved_at,
                      observation.retrieved_at
                  )
                ORDER BY event.effective_at DESC, event.id DESC
                LIMIT 1
            ) approval_event ON TRUE
            WHERE fixture.provider = %s
              AND fixture.source_id = %s
              AND fixture.provider_competition_id = ANY(%s)
        ),
        latest AS (
            SELECT *
            FROM ranked
            WHERE observation_rank = 1
              AND source_sighting_id IS NOT NULL
              AND provider_response_id IS NOT NULL
              AND availability_basis = 'SYSTEM_OBSERVED_AT'
              AND point_in_time_certifiable IS TRUE
              AND observed_at IS NOT NULL
              AND available_at = observed_at
              AND observed_at >= retrieved_at
              AND source_published_at IS NULL
              AND observation_provider = %s
              AND observation_source_id = %s
        )
        INSERT INTO veltrix_ai_analyst.canonical_fixture_state_events (
            canonical_fixture_id,
            fixture_source_link_id,
            provider_fixture_row_id,
            source_observation_id,
            source_sighting_id,
            provider_response_id,
            rights_approval_id,
            payload_sha256,
            response_sha256,
            observed_at,
            kickoff_at,
            status,
            home_goals,
            away_goals
        )
        SELECT
            latest.canonical_fixture_id,
            latest.fixture_source_link_id,
            latest.provider_fixture_row_id,
            latest.source_observation_id,
            latest.source_sighting_id,
            latest.provider_response_id,
            latest.rights_approval_id,
            latest.payload_sha256,
            latest.response_sha256,
            latest.observed_at,
            latest.kickoff_at,
            latest.status,
            latest.home_goals,
            latest.away_goals
        FROM latest
        WHERE latest.data_type = 'fixtures_and_results'
          AND latest.entity_type = 'fixture'
          AND latest.provider_entity_id IS NOT NULL
          AND latest.payload_sha256 = latest.sighting_payload_sha256
          AND latest.response_provider = %s
          AND latest.response_source_id = %s
          AND latest.http_status BETWEEN 200 AND 299
          AND latest.fetched_at = latest.retrieved_at
          AND latest.response_system_observed_at = latest.observed_at
          AND latest.response_approval_id = latest.rights_approval_id
          AND length(latest.response_sha256) = 64
          AND latest.approval_provider = %s
          AND latest.approval_source_id = %s
          AND latest.approval_scope_type = 'competition_id'
          AND latest.approval_scope_values @> jsonb_build_array(latest.provider_competition_id)
          AND latest.effective_approval_status = 'APPROVED'
          AND latest.valid_from <= latest.observed_at
          AND (latest.valid_until IS NULL OR latest.valid_until > latest.observed_at)
          AND latest.permitted_uses @> '["STORAGE", "INTERNAL_ANALYSIS", "FEATURE_ENGINEERING", "MODEL_TRAINING", "MODEL_VALIDATION"]'::jsonb
          AND lower(latest.payload->>'status') = lower(latest.status)
          AND NULLIF(latest.payload->>'kickoff_at', '')::timestamptz = latest.kickoff_at
          AND latest.payload->>'competition_id' = latest.provider_competition_id
          AND latest.payload->>'home_team_id' = latest.home_team_provider_id
          AND latest.payload->>'away_team_id' = latest.away_team_provider_id
          AND latest.payload #>> '{provenance,provider_record_id}' = latest.provider_fixture_id
          AND CASE
                WHEN jsonb_typeof(latest.payload->'home_goals') = 'number'
                    THEN (latest.payload->>'home_goals')::integer
                ELSE NULL
              END IS NOT DISTINCT FROM latest.home_goals
          AND CASE
                WHEN jsonb_typeof(latest.payload->'away_goals') = 'number'
                    THEN (latest.payload->>'away_goals')::integer
                ELSE NULL
              END IS NOT DISTINCT FROM latest.away_goals
          AND NOT EXISTS (
              SELECT 1
              FROM veltrix_ai_analyst.canonical_fixture_state_events existing
              WHERE existing.canonical_fixture_id = latest.canonical_fixture_id
                AND existing.observed_at >= latest.observed_at
          )
        ON CONFLICT (
            fixture_source_link_id, source_observation_id, source_sighting_id
        ) DO NOTHING
        """,
        (
            EXPECTED_PROVIDER,
            EXPECTED_SOURCE_ID,
            ids,
            EXPECTED_PROVIDER,
            EXPECTED_SOURCE_ID,
            EXPECTED_PROVIDER,
            EXPECTED_SOURCE_ID,
            EXPECTED_PROVIDER,
            EXPECTED_SOURCE_ID,
        ),
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM veltrix_ai_analyst.canonical_fixture_state_provenance_audit audit
            JOIN veltrix_ai_analyst.provider_fixtures fixture
              ON fixture.id = audit.provider_fixture_row_id
            WHERE fixture.provider = %s
              AND fixture.source_id = %s
              AND fixture.provider_competition_id = ANY(%s)
              AND audit.state_provenance_status = 'STATE_PROVENANCE_VERIFIED'
            """,
            (EXPECTED_PROVIDER, EXPECTED_SOURCE_ID, ids),
        )
        verified = int(cursor.fetchone()[0])

    return {
        "state_events_inserted": max(0, int(inserted.rowcount)),
        "state_provenance_verified": verified,
    }
