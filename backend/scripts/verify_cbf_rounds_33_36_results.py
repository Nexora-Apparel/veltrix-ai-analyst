"""Read-only comparison of official CBF results articles for rounds 33–36."""
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
EXPECTED_PER_ROUND = 10
PREVIOUSLY_VERIFIED_OVERLAPS = {"325", "360"}


def load_registry() -> dict[str, object]:
    path = Path(__file__).resolve().parents[1] / "data/research/cbf_round33_36_official_results.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    fixtures = registry.get("fixtures", [])
    refs = [str(row["ref"]) for row in fixtures]
    ids = [str(row["fixture_id"]) for row in fixtures]
    rounds = [int(row["round"]) for row in fixtures]
    if len(fixtures) != 40 or len(set(refs)) != 40 or len(set(ids)) != 40:
        raise RuntimeError("ROUNDS_33_36_REGISTRY_MUST_HAVE_40_UNIQUE_FIXTURES")
    if {round_no: rounds.count(round_no) for round_no in set(rounds)} != {
        33: 10, 34: 10, 35: 10, 36: 10
    }:
        raise RuntimeError("ROUNDS_33_36_REGISTRY_FIXTURE_COUNTS_INVALID")
    for fixture in fixtures:
        urls = fixture.get("source_urls", [])
        if not urls or any(not url.startswith("https://www.cbf.com.br/") for url in urls):
            raise RuntimeError("OFFICIAL_CBF_FIXTURE_SOURCE_REQUIRED")
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

    overlap_refs = sorted(
        PREVIOUSLY_VERIFIED_OVERLAPS.intersection(str(row["ref"]) for row in verified)
    )
    unique_new = len(verified) - len(overlap_refs)
    passed = len(verified) == 40 and not mismatches and not missing and len(overlap_refs) == 2
    report = {
        "audit_type": "OFFICIAL_CBF_ROUNDS_33_36_ARTICLES_VS_5DOLLAR_FIXTURES_READ_ONLY",
        "database": DATABASE,
        "provider": PROVIDER,
        "competition_id": COMPETITION_ID,
        "rounds": [33, 34, 35, 36],
        "sources": registry["sources"],
        "source_type": registry["source_type"],
        "registry_sha256": hashlib.sha256(
            json.dumps(registry, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "passed": passed,
        "counts": {
            "official_results": 40,
            "verified_provider_scores": len(verified),
            "mismatches": len(mismatches),
            "missing_provider_fixtures": len(missing),
            "previously_verified_overlap_refs": overlap_refs,
            "new_unique_verified_scores": unique_new,
        },
        "verified": verified,
        "mismatches": mismatches,
        "missing": missing,
        "limitations": [
            "The sources are official CBF round-results articles, not 40 individual match pages.",
            "Refs 325 and 360 overlap two previously verified official match-page score checks and are not double-counted.",
            "Provider-local fixture IDs and exact provider team labels are used; no canonical team merge is approved.",
            "No production rows are modified and this does not establish PIT availability.",
        ],
    }
    output = Path(os.environ.get(
        "CBF_ROUNDS_33_36_SCORE_VERIFICATION_PATH",
        "artifacts/cbf-rounds-33-36-score-verification.json",
    ))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASSED" if passed else "FAILED", "counts": report["counts"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
