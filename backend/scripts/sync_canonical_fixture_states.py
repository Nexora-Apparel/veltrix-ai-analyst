"""One-time, checksum-migration companion for PIT-backed canonical fixture state sync."""
from __future__ import annotations

import json
import os
import sys
from urllib.parse import urlsplit

import psycopg

from app.canonical_fixture_states import sync_canonical_fixture_states
from app.providers.prospective_capture_scope import PROSPECTIVE_CAPTURE_COMPETITIONS

EXPECTED_DATABASE = "veltrix_ai_analyst"
CONFIRMATION = "SYNC_PIT_BACKED_CANONICAL_FIXTURE_STATES_V1"


def main() -> int:
    if os.environ.get("CANONICAL_FIXTURE_STATE_SYNC_CONFIRMATION") != CONFIRMATION:
        raise SystemExit("CANONICAL_FIXTURE_STATE_SYNC_CONFIRMATION_REQUIRED")
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if (
        not database_url
        or os.environ.get("EXPECTED_DATABASE_NAME") != EXPECTED_DATABASE
        or urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != EXPECTED_DATABASE
    ):
        raise SystemExit("CANONICAL_FIXTURE_STATE_SYNC_DATABASE_TARGET_INVALID")

    competition_ids = [
        competition_id for competition_id, _ in PROSPECTIVE_CAPTURE_COMPETITIONS
    ]
    try:
        with psycopg.connect(database_url, autocommit=True) as connection:
            if connection.info.dbname != EXPECTED_DATABASE:
                raise SystemExit("CANONICAL_FIXTURE_STATE_SYNC_CONNECTED_DATABASE_MISMATCH")
            with connection.transaction():
                connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                connection.execute("SET LOCAL lock_timeout = '15s'")
                connection.execute("SET LOCAL statement_timeout = '600s'")
                report = sync_canonical_fixture_states(connection, competition_ids)
                drift = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM veltrix_ai_analyst.canonical_fixture_sources link
                    JOIN veltrix_ai_analyst.effective_canonical_fixture_sources effective_link
                      ON effective_link.id = link.id
                     AND effective_link.effective_mapping_status = 'SOURCE_FIXTURE_LINK_REVIEWED'
                    JOIN veltrix_ai_analyst.provider_fixtures fixture
                      ON fixture.id = link.provider_fixture_row_id
                    JOIN veltrix_ai_analyst.canonical_fixtures canonical
                      ON canonical.id = link.canonical_fixture_id
                     AND canonical.identity_status = 'VERIFIED'
                    WHERE fixture.provider = '5DollarFootballAPI'
                      AND fixture.source_id = '5dollarfootballapi'
                      AND fixture.provider_competition_id = ANY(%s)
                      AND (
                          canonical.status IS DISTINCT FROM fixture.status
                          OR canonical.home_goals IS DISTINCT FROM fixture.home_goals
                          OR canonical.away_goals IS DISTINCT FROM fixture.away_goals
                      )
                    """,
                    (competition_ids,),
                ).fetchone()[0]
                if int(drift) != 0:
                    raise RuntimeError(f"CANONICAL_FIXTURE_STATE_DRIFT_REMAINS:{drift}")
                report["canonical_state_drift_remaining"] = int(drift)
                report["status"] = "CANONICAL_FIXTURE_STATE_SYNC_VERIFIED"
            print(json.dumps(report, sort_keys=True, indent=2))
    except (psycopg.Error, OSError, RuntimeError, ValueError, TypeError) as exc:
        print(
            f"CANONICAL_FIXTURE_STATE_SYNC_FAILED:{type(exc).__name__}:{str(exc)[:1200]}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
