"""Safely materialize the 10 Round 38 fixtures into the existing canonical layer.

This is an incremental, full-scope reconciliation: the original 374 source mappings
must be reused byte-for-byte, and exactly 10 run-5 fixtures may be added. No
identity review is resolved and no PIT feature is promoted.
"""
from __future__ import annotations

import json
import os
import sys

import psycopg

from app.canonicalization import (
    BRAZIL_SERIE_B_RUN_3,
    CanonicalMaterializationScope,
    build_brazil_serie_b_materialization_plan,
    materialize_brazil_serie_b_canonical_entities,
)

CONFIRMATION = "MATERIALIZE_BRAZIL_SERIE_B_RUN_5_INCREMENTAL"
EXPECTED_BEFORE = {
    "canonical_teams": 21,
    "canonical_competitions": 1,
    "canonical_fixtures": 374,
    "provider_team_identity_links": 21,
    "provider_competition_identity_links": 1,
    "canonical_fixture_sources": 374,
    "canonical_identity_review_events": 0,
}
EXPECTED_AFTER = {**EXPECTED_BEFORE, "canonical_fixtures": 384, "canonical_fixture_sources": 384}
EXPECTED_CONFLICT_IDS = {
    "2341822348", "3116209225", "2336910968", "1587564237",
    "933498248", "236839304", "1988139832", "553958702",
}
SCOPE = CanonicalMaterializationScope(
    provider=BRAZIL_SERIE_B_RUN_3.provider,
    source_id=BRAZIL_SERIE_B_RUN_3.source_id,
    competition_id=BRAZIL_SERIE_B_RUN_3.competition_id,
    rights_approval_id=BRAZIL_SERIE_B_RUN_3.rights_approval_id,
    import_run_id=None,
    expected_fixture_count=384,
    expected_team_count=21,
)
COUNT_SQL = """
SELECT
 (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_teams),
 (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_competitions),
 (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_fixtures),
 (SELECT COUNT(*) FROM veltrix_ai_analyst.provider_team_identity_links),
 (SELECT COUNT(*) FROM veltrix_ai_analyst.provider_competition_identity_links),
 (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_fixture_sources),
 (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_identity_review_events)
"""
REVIEW_SQL = """
SELECT
 (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_identity_review_cases),
 (SELECT COUNT(*) FROM veltrix_ai_analyst.canonical_identity_review_case_events)
"""
NEW_FIXTURES_SQL = """
SELECT COUNT(*)
FROM veltrix_ai_analyst.provider_fixtures fixture
JOIN veltrix_ai_analyst.source_observation_sightings sighting
  ON sighting.source_observation_id = fixture.source_observation_id
JOIN veltrix_ai_analyst.import_request_reservations reservation
  ON reservation.provider_response_id = sighting.provider_response_id
WHERE fixture.provider = %s AND fixture.source_id = %s
  AND fixture.provider_competition_id = %s
  AND reservation.import_run_id = 5
  AND NOT EXISTS (
      SELECT 1 FROM veltrix_ai_analyst.canonical_fixture_sources source
      WHERE source.provider_fixture_row_id = fixture.id
  )
"""
UNLINKED_FIXTURES_SQL = """
SELECT COUNT(*)
FROM veltrix_ai_analyst.provider_fixtures fixture
LEFT JOIN veltrix_ai_analyst.canonical_fixture_sources source
  ON source.provider_fixture_row_id = fixture.id
WHERE fixture.provider = %s AND fixture.source_id = %s
  AND fixture.provider_competition_id = %s
  AND source.id IS NULL
"""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SystemExit(code)


def _counts(connection: psycopg.Connection) -> dict[str, int]:
    row = connection.execute(COUNT_SQL).fetchone()
    keys = tuple(EXPECTED_BEFORE)
    return dict(zip(keys, map(int, row), strict=True))


def main() -> int:
    _require(
        os.environ.get("CANONICAL_INCREMENTAL_CONFIRMATION") == CONFIRMATION,
        "CANONICAL_INCREMENTAL_CONFIRMATION_REQUIRED",
    )
    database_url = os.environ.get("DATABASE_URL", "")
    expected_database = os.environ.get("EXPECTED_DATABASE_NAME", "")
    _require(bool(database_url), "CANONICAL_INCREMENTAL_DATABASE_URL_MISSING")
    _require(
        expected_database == "veltrix_ai_analyst",
        "CANONICAL_INCREMENTAL_EXPECTED_DATABASE_INVALID",
    )

    with psycopg.connect(database_url, autocommit=True) as connection:
        _require(
            connection.info.dbname == expected_database,
            "CANONICAL_INCREMENTAL_DATABASE_TARGET_MISMATCH",
        )
        with connection.transaction():
            connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            connection.execute("SET LOCAL lock_timeout = '15s'")
            connection.execute("SET LOCAL statement_timeout = '180s'")
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                ("veltrix-canonical:5DollarFootballAPI:5dollarfootballapi:522514093:incremental",),
            )

            before = _counts(connection)
            _require(before == EXPECTED_BEFORE, "CANONICAL_INCREMENTAL_BEFORE_COUNTS_MISMATCH")
            review_before = tuple(map(int, connection.execute(REVIEW_SQL).fetchone()))
            unlinked = int(connection.execute(
                UNLINKED_FIXTURES_SQL,
                (SCOPE.provider, SCOPE.source_id, SCOPE.competition_id),
            ).fetchone()[0])
            run5_unlinked = int(connection.execute(
                NEW_FIXTURES_SQL,
                (SCOPE.provider, SCOPE.source_id, SCOPE.competition_id),
            ).fetchone()[0])
            _require(unlinked == 10, "CANONICAL_INCREMENTAL_UNLINKED_SCOPE_MISMATCH")
            _require(run5_unlinked == 10, "CANONICAL_INCREMENTAL_RUN5_SCOPE_MISMATCH")

            plan = build_brazil_serie_b_materialization_plan(connection, SCOPE)
            _require(plan.ready, "CANONICAL_INCREMENTAL_PLAN_BLOCKED")
            _require(
                plan.team_count == 21
                and plan.competition_count == 1
                and plan.fixture_count == 384
                and plan.finished_fixture_count == 380
                and plan.unknown_fixture_count == 4
                and plan.provenance_complete_team_count == 21
                and plan.provenance_complete_competition_count == 1
                and plan.provenance_complete_fixture_count == 384
                and plan.non_pit_observation_count == 406
                and set(plan.conflict_fixture_ids) == EXPECTED_CONFLICT_IDS,
                "CANONICAL_INCREMENTAL_PLAN_SCOPE_OR_PROVENANCE_MISMATCH",
            )

            result = materialize_brazil_serie_b_canonical_entities(
                connection, execute=True, scope=SCOPE
            )
            after = _counts(connection)
            review_after = tuple(map(int, connection.execute(REVIEW_SQL).fetchone()))
            _require(after == EXPECTED_AFTER, "CANONICAL_INCREMENTAL_AFTER_COUNTS_MISMATCH")
            _require(review_after == review_before, "CANONICAL_INCREMENTAL_REVIEW_QUEUE_CHANGED")
            _require(
                result["mode"] == "APPLIED"
                and result["competition_created"] is False
                and result["teams_created"] == 0
                and result["fixtures_created"] == 10
                and result["fixtures_reused"] == 374
                and result["identity_reviews_created"] == 0
                and result["pit_observations_promoted"] == 0
                and result["provider_requests_made"] == 0,
                "CANONICAL_INCREMENTAL_RESULT_MISMATCH",
            )
            remaining = int(connection.execute(
                UNLINKED_FIXTURES_SQL,
                (SCOPE.provider, SCOPE.source_id, SCOPE.competition_id),
            ).fetchone()[0])
            _require(remaining == 0, "CANONICAL_INCREMENTAL_UNLINKED_REMAINS")

        print(json.dumps({
            "status": "CANONICAL_INCREMENTAL_COMMITTED",
            "database": expected_database,
            "before_counts": before,
            "after_counts": after,
            "review_queue_before": review_before,
            "review_queue_after": review_after,
            "run5_unlinked_before": run5_unlinked,
            "unlinked_after": remaining,
            "scope": plan.as_dict(),
            "result": result,
        }, sort_keys=True, default=str))
        print("CANONICAL_INCREMENTAL_COMMITTED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"CANONICAL_INCREMENTAL_FAILED:{type(exc).__name__}", file=sys.stderr)
        raise
