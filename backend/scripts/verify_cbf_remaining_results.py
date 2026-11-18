"""Read-only comparison of outstanding CBF individual match pages with provider fixtures."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import psycopg

PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"
COMPETITION_ID = "522514093"
DATABASE = "veltrix_ai_analyst"
EXPECTED_ROUNDS = {31: 10, 32: 10, 37: 7}


def load_registry() -> dict[str, object]:
    path = Path(__file__).resolve().parents[1] / "data/research/cbf_rounds31_32_37_official_results.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    fixtures = registry.get("fixtures", [])
    refs = [str(row["ref"]) for row in fixtures]
    ids = [str(row["fixture_id"]) for row in fixtures]
    rounds = [int(row["round"]) for row in fixtures]
    if len(fixtures) != 27 or len(set(refs)) != 27 or len(set(ids)) != 27:
        raise RuntimeError("OUTSTANDING_CBF_REGISTRY_MUST_HAVE_27_UNIQUE_FIXTURES")
    if {round_no: rounds.count(round_no) for round_no in set(rounds)} != EXPECTED_ROUNDS:
        raise RuntimeError("OUTSTANDING_CBF_ROUND_COUNTS_INVALID")
    for fixture in fixtures:
        url = str(fixture.get("official_source_url", ""))
        if not url.startswith("https://www.cbf.com.br/futebol-brasileiro/jogos/"):
            raise RuntimeError("OFFICIAL_CBF_MATCH_PAGE_REQUIRED")
        if len(fixture.get("score", [])) != 2:
            raise RuntimeError("OFFICIAL_SCORE_REQUIRED")
    return registry


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL_REQUIRED")
    if os.environ.get("EXPECTED_DATABASE_NAME", DATABASE) != DATABASE:
        raise SystemExit("EXPECTED_DATABASE_NAME_MISMATCH")

    registry = load_registry()
    verified = []
    mismatches = []
    missing = []
    with psycopg.connect(database_url) as connection:
        if connection.info.dbname != DATABASE:
            raise SystemExit("DATABASE_TARGET_MISMATCH")
        with connection.transaction():
            connection.execute("SET TRANSACTION READ ONLY")
            for expected in registry["fixtures"]:
                row = connection.execute(
                    """
                    SELECT provider_fixture_id, home_team_name, away_team_name,
                           home_goals, away_goals, status
                    FROM veltrix_ai_analyst.provider_fixtures
                    WHERE provider = %s AND source_id = %s
                      AND provider_competition_id = %s AND provider_fixture_id = %s
                    """,
                    (PROVIDER, SOURCE_ID, COMPETITION_ID, str(expected["fixture_id"])),
                ).fetchone()
                if row is None:
                    missing.append(expected)
                    continue
                fixture_id, home_name, away_name, home_goals, away_goals, status = row
                actual_score = (home_goals, away_goals)
                expected_score = tuple(int(value) for value in expected["score"])
                teams_match = (
                    home_name == expected["provider_home_name"]
                    and away_name == expected["provider_away_name"]
                )
                audit = {
                    **expected,
                    "provider_fixture_id": str(fixture_id),
                    "provider_home_name": home_name,
                    "provider_away_name": away_name,
                    "provider_score": list(actual_score),
                    "provider_status": status,
                    "provider_team_labels_match": teams_match,
                }
                if status == "FINISHED" and actual_score == expected_score and teams_match:
                    verified.append(audit)
                else:
                    mismatches.append(audit)

    passed = len(verified) == 27 and not mismatches and not missing
    report = {
        "audit_type": "OFFICIAL_CBF_INDIVIDUAL_MATCH_PAGES_VS_5DOLLAR_FIXTURES_READ_ONLY",
        "database": DATABASE,
        "provider": PROVIDER,
        "competition_id": COMPETITION_ID,
        "rounds": [31, 32, 37],
        "source_type": registry["source_type"],
        "schedule_source_urls": registry["schedule_source_urls"],
        "registry_sha256": hashlib.sha256(
            json.dumps(registry, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "passed": passed,
        "counts": {
            "official_results": 27,
            "verified_provider_scores": len(verified),
            "mismatches": len(mismatches),
            "missing_provider_fixtures": len(missing),
        },
        "verified": verified,
        "mismatches": mismatches,
        "missing": missing,
        "limitations": [
            "Official CBF individual match pages are used for the scorelines; the detailed schedule PDFs supply CBF match reference numbers.",
            "Provider-local fixture IDs and exact provider team labels are used; no canonical team merge is approved.",
            "No production rows are modified and this does not establish PIT availability.",
        ],
    }
    output = Path(os.environ.get(
        "CBF_REMAINING_SCORE_VERIFICATION_PATH",
        "artifacts/cbf-remaining-score-verification.json",
    ))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASSED" if passed else "FAILED", "counts": report["counts"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
