"""Read-only comparison of CBF's official Round 30 results article with provider fixtures."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os

import psycopg

PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"
COMPETITION_ID = "522514093"
DATABASE = "veltrix_ai_analyst"


def load_registry() -> dict[str, object]:
    path = Path(__file__).resolve().parents[1] / "data/research/cbf_round30_official_results.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    fixtures = registry.get("fixtures", [])
    refs = [str(row["ref"]) for row in fixtures]
    ids = [str(row["fixture_id"]) for row in fixtures]
    if len(refs) != 10 or len(set(refs)) != 10 or len(set(ids)) != 10:
        raise RuntimeError("ROUND30_REGISTRY_MUST_HAVE_10_UNIQUE_FIXTURES")
    if not str(registry.get("official_cbf_source_url", "")).startswith("https://www.cbf.com.br/"):
        raise RuntimeError("OFFICIAL_CBF_SOURCE_REQUIRED")
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

    passed = len(verified) == 10 and not mismatches and not missing
    report = {
        "audit_type": "OFFICIAL_CBF_ROUND30_ARTICLE_VS_5DOLLAR_FIXTURES_READ_ONLY",
        "database": DATABASE,
        "provider": PROVIDER,
        "competition_id": COMPETITION_ID,
        "round": 30,
        "official_cbf_source_url": registry["official_cbf_source_url"],
        "corroborating_cbf_source_url": registry["corroborating_cbf_source_url"],
        "source_type": registry["source_type"],
        "source_published_at": registry["source_published_at"],
        "registry_sha256": hashlib.sha256(
            json.dumps(registry, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "passed": passed,
        "counts": {
            "official_results": 10,
            "verified_provider_scores": len(verified),
            "mismatches": len(mismatches),
            "missing_provider_fixtures": len(missing),
        },
        "verified": verified,
        "mismatches": mismatches,
        "missing": missing,
        "limitations": [
            "The source is an official CBF round-results article, not 10 individual match pages.",
            "The two article sources together provide the full ten-result round summary.",
            "Provider-local fixture IDs are used for exact record selection; no canonical team merge is approved.",
            "No production rows are modified and this does not establish PIT availability.",
        ],
    }
    output = Path(os.environ.get(
        "CBF_ROUND30_SCORE_VERIFICATION_PATH",
        "artifacts/cbf-round30-score-verification.json",
    ))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASSED" if passed else "FAILED", "counts": report["counts"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
