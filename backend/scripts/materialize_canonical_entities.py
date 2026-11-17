"""Execute the first guarded production canonical materialization.

This command is intentionally first-run-only. It requires a workflow confirmation,
a fresh exact-scope plan, and all canonical target tables to be empty. The entire
write and post-write reconciliation run in one PostgreSQL transaction.
"""
from __future__ import annotations

import json
import os
import sys

import psycopg

from app.canonicalization import (
    BRAZIL_SERIE_B_RUN_3,
    build_brazil_serie_b_materialization_plan,
    materialize_brazil_serie_b_canonical_entities,
)

EXPECTED_COUNTS = {
    "canonical_teams": 21,
    "canonical_competitions": 1,
    "canonical_fixtures": 374,
    "provider_team_identity_links": 21,
    "provider_competition_identity_links": 1,
    "canonical_fixture_sources": 374,
    "canonical_identity_review_events": 0,
}

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


def _counts(connection: psycopg.Connection) -> dict[str, int]:
    row = connection.execute(COUNT_SQL).fetchone()
    return dict(zip(EXPECTED_COUNTS, map(int, row), strict=True))


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise SystemExit(code)


def main() -> int:
    _require(
        os.environ.get("CANONICAL_MATERIALIZATION_CONFIRMATION")
        == "MATERIALIZE_BRAZIL_SERIE_B_RUN_3",
        "CANONICAL_MATERIALIZATION_CONFIRMATION_REQUIRED",
    )
    database_url = os.environ.get("DATABASE_URL", "")
    expected_database = os.environ.get("EXPECTED_DATABASE_NAME", "")
    _require(bool(database_url), "CANONICAL_MATERIALIZATION_DATABASE_URL_MISSING")
    _require(
        expected_database == "veltrix_ai_analyst",
        "CANONICAL_MATERIALIZATION_EXPECTED_DATABASE_INVALID",
    )

    # Autocommit allows the explicit outer transaction below to own the complete
    # write, including the materializer's nested transaction/savepoint.
    with psycopg.connect(database_url, autocommit=True) as connection:
        _require(
            connection.info.dbname == expected_database,
            "CANONICAL_MATERIALIZATION_DATABASE_TARGET_MISMATCH",
        )

        plan = build_brazil_serie_b_materialization_plan(connection)
        report = plan.as_dict()
        _require(plan.ready, "CANONICAL_MATERIALIZATION_PLAN_BLOCKED")
        _require(
            (
                plan.provider == BRAZIL_SERIE_B_RUN_3.provider
                and plan.source_id == BRAZIL_SERIE_B_RUN_3.source_id
                and plan.competition_id == BRAZIL_SERIE_B_RUN_3.competition_id
                and plan.import_run_id == BRAZIL_SERIE_B_RUN_3.import_run_id
                and plan.team_count == 21
                and plan.competition_count == 1
                and plan.fixture_count == 374
                and plan.finished_fixture_count == 370
                and plan.unknown_fixture_count == 4
                and plan.provenance_complete_team_count == 21
                and plan.provenance_complete_competition_count == 1
                and plan.provenance_complete_fixture_count == 374
                and plan.non_pit_observation_count == 396
                and set(plan.conflict_fixture_ids) == {"2341822348", "3116209225"}
            ),
            "CANONICAL_MATERIALIZATION_PLAN_SCOPE_OR_COUNTS_CHANGED",
        )

        before = _counts(connection)
        _require(
            all(value == 0 for value in before.values()),
            "CANONICAL_MATERIALIZATION_TARGET_NOT_EMPTY",
        )

        with connection.transaction():
            result = materialize_brazil_serie_b_canonical_entities(
                connection,
                execute=True,
                scope=BRAZIL_SERIE_B_RUN_3,
            )
            after = _counts(connection)
            _require(
                after == EXPECTED_COUNTS,
                "CANONICAL_MATERIALIZATION_POST_WRITE_COUNTS_MISMATCH",
            )
            _require(
                result["mode"] == "APPLIED"
                and result["competition_created"] is True
                and result["teams_created"] == 21
                and result["fixtures_created"] == 374
                and result["fixtures_reused"] == 0
                and result["identity_reviews_created"] == 0
                and result["pit_observations_promoted"] == 0
                and result["provider_requests_made"] == 0,
                "CANONICAL_MATERIALIZATION_RESULT_MISMATCH",
            )

        print(
            json.dumps(
                {
                    "status": "MATERIALIZATION_COMMITTED",
                    "database": expected_database,
                    "scope": report,
                    "before_counts": before,
                    "after_counts": after,
                    "result": result,
                },
                sort_keys=True,
                default=str,
            )
        )
        print("CANONICAL_MATERIALIZATION_COMMITTED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # Fail closed; workflow logs retain the exception type.
        print(
            f"CANONICAL_MATERIALIZATION_FAILED:{type(exc).__name__}",
            file=sys.stderr,
        )
        raise
