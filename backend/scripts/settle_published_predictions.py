"""Settle published predictions only from exact, PIT-qualified source results.

Dry-run is the default. --execute writes append-only settlement events; the
database trigger independently revalidates publication, canonical identity,
source response, observation timing, payload hashes and rights.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

DATABASE_NAME = "veltrix_ai_analyst"

CANDIDATE_QUERY = """
    SELECT DISTINCT ON (prediction.prediction_id)
        prediction.prediction_id,
        observation.id AS source_observation_id,
        sighting.id AS source_sighting_id,
        response.id AS provider_response_id,
        approval.approval_id AS rights_approval_id,
        (observation.payload->>'home_goals')::smallint AS home_goals,
        (observation.payload->>'away_goals')::smallint AS away_goals,
        sighting.system_observed_at AS settled_at,
        observation.payload_sha256 AS source_payload_sha256,
        response.response_sha256 AS provider_response_sha256
    FROM veltrix_ai_analyst.predictions prediction
    JOIN veltrix_ai_analyst.canonical_fixtures fixture
      ON fixture.id = prediction.canonical_fixture_id
     AND fixture.identity_status = 'VERIFIED'
     AND fixture.completeness_status = 'RECONCILED'
    JOIN LATERAL (
        SELECT event.decision
        FROM veltrix_ai_analyst.prediction_publication_events event
        WHERE event.prediction_id = prediction.prediction_id
        ORDER BY event.effective_at DESC, event.id DESC
        LIMIT 1
    ) publication ON publication.decision = 'PUBLISHED'
    JOIN veltrix_ai_analyst.canonical_fixture_sources fixture_source
      ON fixture_source.canonical_fixture_id = fixture.id
     AND fixture_source.mapping_status = 'REVIEW_REQUIRED'
    JOIN LATERAL (
        SELECT event.decision
        FROM veltrix_ai_analyst.canonical_identity_review_events event
        WHERE event.fixture_source_link_id = fixture_source.id
        ORDER BY event.reviewed_at DESC, event.id DESC
        LIMIT 1
    ) source_review ON source_review.decision = 'SOURCE_FIXTURE_LINK_REVIEWED'
    JOIN veltrix_ai_analyst.provider_fixtures provider_fixture
      ON provider_fixture.id = fixture_source.provider_fixture_row_id
     AND provider_fixture.provider = '5DollarFootballAPI'
     AND provider_fixture.source_id = '5dollarfootballapi'
     AND provider_fixture.provider_fixture_id = fixture_source.provider_fixture_id
     AND provider_fixture.status = 'FINISHED'
     AND provider_fixture.home_goals IS NOT NULL
     AND provider_fixture.away_goals IS NOT NULL
     AND provider_fixture.kickoff_at = fixture.kickoff_at
    JOIN veltrix_ai_analyst.source_observations observation
      ON observation.provider = provider_fixture.provider
     AND observation.source_id = provider_fixture.source_id
     AND observation.data_type = 'fixtures_and_results'
     AND observation.entity_type = 'fixture'
     AND observation.provider_entity_id = provider_fixture.provider_fixture_id
     AND observation.availability_basis = 'SYSTEM_OBSERVED_AT'
     AND observation.point_in_time_certifiable IS TRUE
     AND observation.system_observed_at IS NOT NULL
     AND observation.available_at = observation.system_observed_at
     AND lower(observation.payload->>'status') = 'finished'
     AND jsonb_typeof(observation.payload->'home_goals') = 'number'
     AND jsonb_typeof(observation.payload->'away_goals') = 'number'
     AND (observation.payload->>'home_goals')::smallint = provider_fixture.home_goals
     AND (observation.payload->>'away_goals')::smallint = provider_fixture.away_goals
     AND observation.payload->>'competition_id' = provider_fixture.provider_competition_id
     AND observation.payload->>'home_team_id' = provider_fixture.home_team_provider_id
     AND observation.payload->>'away_team_id' = provider_fixture.away_team_provider_id
     AND (observation.payload->>'kickoff_at')::timestamptz = fixture.kickoff_at
     AND observation.payload #>> '{provenance,provider_record_id}'
         = provider_fixture.provider_fixture_id
    JOIN veltrix_ai_analyst.source_observation_sightings sighting
      ON sighting.source_observation_id = observation.id
     AND sighting.provider_response_id IS NOT NULL
     AND sighting.payload_sha256 = observation.payload_sha256
     AND sighting.availability_basis = 'SYSTEM_OBSERVED_AT'
     AND sighting.point_in_time_certifiable IS TRUE
     AND sighting.system_observed_at IS NOT NULL
     AND sighting.available_at = sighting.system_observed_at
     AND sighting.system_observed_at >= sighting.retrieved_at
     AND observation.system_observed_at <= sighting.system_observed_at
     AND observation.retrieved_at <= sighting.system_observed_at
     AND sighting.system_observed_at > fixture.kickoff_at
    JOIN veltrix_ai_analyst.provider_responses response
      ON response.id = sighting.provider_response_id
     AND response.provider = observation.provider
     AND response.source_id = observation.source_id
     AND response.http_status BETWEEN 200 AND 299
     AND response.fetched_at = sighting.retrieved_at
     AND response.system_observed_at >= response.fetched_at
     AND response.system_observed_at <= sighting.system_observed_at
     AND length(response.response_sha256) = 64
    JOIN veltrix_ai_analyst.source_approvals approval
      ON approval.approval_id = observation.rights_approval_id
     AND approval.approval_id = response.rights_approval_id
     AND approval.provider = observation.provider
     AND approval.source_id = observation.source_id
     AND approval.status = 'APPROVED'
     AND approval.valid_from <= sighting.system_observed_at
     AND (approval.valid_until IS NULL OR approval.valid_until > sighting.system_observed_at)
     AND approval.scope_values @> jsonb_build_array(provider_fixture.provider_competition_id)
     AND approval.data_types @> '["fixtures_and_results"]'::jsonb
     AND approval.permitted_uses @> '["MODEL_TRAINING","MODEL_VALIDATION"]'::jsonb
    LEFT JOIN LATERAL (
        SELECT event.status
        FROM veltrix_ai_analyst.source_approval_status_events event
        WHERE event.approval_id = approval.approval_id
          AND event.effective_at <= sighting.system_observed_at
        ORDER BY event.effective_at DESC, event.id DESC
        LIMIT 1
    ) approval_event ON TRUE
    LEFT JOIN veltrix_ai_analyst.latest_prediction_settlements previous
      ON previous.prediction_id = prediction.prediction_id
    WHERE sighting.system_observed_at > COALESCE(
        previous.settled_at, fixture.kickoff_at
    )
      AND COALESCE(approval_event.status, approval.status) = 'APPROVED'
      AND (observation.payload->>'home_goals')::smallint = provider_fixture.home_goals
      AND (observation.payload->>'away_goals')::smallint = provider_fixture.away_goals
    ORDER BY prediction.prediction_id, sighting.system_observed_at DESC,
             observation.id DESC, sighting.id DESC
    LIMIT %s
"""


INSERT_SETTLEMENT = """
    INSERT INTO veltrix_ai_analyst.prediction_settlement_events (
        prediction_id, source_observation_id, source_sighting_id,
        provider_response_id, rights_approval_id, home_goals, away_goals,
        settled_at, source_payload_sha256, provider_response_sha256
    ) VALUES (
        %(prediction_id)s, %(source_observation_id)s, %(source_sighting_id)s,
        %(provider_response_id)s, %(rights_approval_id)s, %(home_goals)s,
        %(away_goals)s, %(settled_at)s, %(source_payload_sha256)s,
        %(provider_response_sha256)s
    )
    ON CONFLICT (prediction_id, source_observation_id) DO NOTHING
    RETURNING id
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="insert verified append-only settlement events; default is read-only dry-run",
    )
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > 5000:
        parser.error("--limit must be between 1 and 5000")
    return args


def settle_published_predictions(
    database_url: str,
    *,
    expected_database: str,
    execute: bool = False,
    limit: int = 250,
) -> dict[str, Any]:
    if expected_database != DATABASE_NAME:
        raise ValueError("EXPECTED_DATABASE_NAME_MISMATCH")
    if not database_url.strip():
        raise ValueError("DATABASE_URL_REQUIRED")
    if limit < 1 or limit > 5000:
        raise ValueError("SETTLEMENT_LIMIT_OUT_OF_RANGE")

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        if connection.info.dbname != DATABASE_NAME:
            raise ValueError("DATABASE_TARGET_NAME_MISMATCH")
        connection.execute(
            "SET TRANSACTION READ WRITE" if execute else "SET TRANSACTION READ ONLY"
        )
        candidates = connection.execute(CANDIDATE_QUERY, (limit,)).fetchall()
        inserted = 0
        if execute:
            for candidate in candidates:
                result = connection.execute(INSERT_SETTLEMENT, candidate).fetchone()
                inserted += int(result is not None)

    return {
        "status": (
            "SETTLEMENTS_INSERTED" if inserted else
            "DRY_RUN_CANDIDATES_READY" if candidates else
            "NO_ELIGIBLE_PUBLISHED_RESULTS"
        ),
        "candidate_count": len(candidates),
        "inserted_count": inserted,
        "mode": "EXECUTE" if execute else "READ_ONLY_DRY_RUN",
        "limit": limit,
        "provider_calls": 0,
        "odds_api_calls": 0,
        "telegram_messages": 0,
        "source_of_truth": "5DollarFootballAPI_SYSTEM_OBSERVED_AT",
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    database_url = (
        os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL")
        or os.getenv("DATABASE_URL", "")
    ).strip()
    expected_database = os.getenv("EXPECTED_DATABASE_NAME", "")
    report = settle_published_predictions(
        database_url,
        expected_database=expected_database,
        execute=args.execute,
        limit=args.limit,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
