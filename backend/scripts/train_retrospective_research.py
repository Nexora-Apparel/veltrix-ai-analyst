"""Build and score the personal-use retrospective research corpus from Neon."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

import psycopg

from app.models.retrospective import ResearchFixture, chronological_research_run

QUERY = """
SELECT provider_fixture_id, kickoff_at, home_team_provider_id,
       away_team_provider_id, home_goals, away_goals, status
FROM veltrix_ai_analyst.provider_fixtures
WHERE provider = %s AND source_id = %s
  AND provider_competition_id = %s
ORDER BY kickoff_at, provider_fixture_id
"""
PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"
COMPETITION_ID = "522514093"


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    expected_database = os.environ.get("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")
    if not database_url:
        raise SystemExit("DATABASE_URL_REQUIRED")
    if expected_database != "veltrix_ai_analyst":
        raise SystemExit("EXPECTED_DATABASE_NAME_MISMATCH")

    with psycopg.connect(database_url, autocommit=True) as connection:
        if connection.info.dbname != expected_database:
            raise SystemExit("DATABASE_TARGET_MISMATCH")
        rows = connection.execute(QUERY, (PROVIDER, SOURCE_ID, COMPETITION_ID)).fetchall()

    finished = []
    unknown = []
    invalid = []
    for fixture_id, kickoff, home_id, away_id, home_goals, away_goals, status in rows:
        if status == "FINISHED" and home_goals is not None and away_goals is not None:
            finished.append(ResearchFixture(
                fixture_id=str(fixture_id), kickoff_at=kickoff,
                home_team_id=str(home_id), away_team_id=str(away_id),
                home_goals=int(home_goals), away_goals=int(away_goals),
            ))
        elif status == "UNKNOWN" and home_goals is None and away_goals is None:
            unknown.append(str(fixture_id))
        else:
            invalid.append(str(fixture_id))
    if invalid:
        raise SystemExit(f"UNEXPECTED_STATUS_OR_SCORE_ROWS:{len(invalid)}")
    if not finished:
        raise SystemExit("NO_FINISHED_FIXTURES")

    report = chronological_research_run(finished)
    report["source"] = {
        "provider": PROVIDER,
        "source_id": SOURCE_ID,
        "competition_id": COMPETITION_ID,
        "training_permission": "PROJECT_OWNER_CONFIRMED_PERSONAL_USE",
        "identity_namespace": "PROVIDER_LOCAL_TEAM_IDS",
        "feature_semantics": "RETROSPECTIVE_LAGGED_RESULTS_NOT_HISTORICAL_PIT_REPLAY",
        "source_rows": len(rows),
        "finished_labeled_rows": len(finished),
        "unknown_unlabeled_rows_excluded": len(unknown),
        "unknown_fixture_ids": sorted(unknown),
        "invalid_rows": 0,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    output = Path(os.environ.get("TRAINING_REPORT_PATH", "artifacts/retrospective-training-report.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "RETROSPECTIVE_RESEARCH_TRAINING_COMPLETE",
        "database": expected_database,
        "finished": len(finished),
        "unknown_excluded": len(unknown),
        "report_path": str(output),
        "metrics": {
            "elo": report["elo"],
            "poisson": report["poisson"],
            "ensemble": report["ensemble"],
        },
        "rho_diagnostic": report["dixon_coles_rho_full_corpus_diagnostic_only"],
        "report_sha256": report["report_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"RETROSPECTIVE_TRAINING_FAILED:{type(exc).__name__}", file=sys.stderr)
        raise
