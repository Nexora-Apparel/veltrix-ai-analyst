"""Build a separately materialized, non-PIT retrospective research dataset.

This command is read-only against Neon. It uses provider-local historical results,
reconstructs strictly earlier same-competition features, and writes a local,
content-addressed JSON artifact. It never writes prospective snapshots or labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.validation.retrospective_features import (
    HistoricalFixture,
    build_retrospective_lagged_features,
)

DATABASE_NAME = "veltrix_ai_analyst"
PROVIDER = "5DollarFootballAPI"
SOURCE_ID = "5dollarfootballapi"
DATASET_TYPE = "RETROSPECTIVE_RESEARCH_TRAINING_ONLY"
PROVENANCE_MODE = "RETROSPECTIVE_EVENT_TIME_RECONSTRUCTION"


def load_historical_rows(dsn: str) -> list[dict[str, Any]]:
    """Load the approved provider-local finished corpus in a read-only txn."""
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        connection.execute("SET TRANSACTION READ ONLY")
        database = connection.execute("SELECT current_database() AS name").fetchone()["name"]
        if database != DATABASE_NAME:
            raise RuntimeError(f"refusing database {database!r}; expected {DATABASE_NAME!r}")
        rows = connection.execute(
            """
            SELECT
                fixture.id::text AS fixture_id,
                fixture.provider_competition_id AS competition_id,
                fixture.kickoff_at,
                fixture.home_team_provider_id AS home_team_id,
                fixture.away_team_provider_id AS away_team_id,
                fixture.home_goals,
                fixture.away_goals,
                fixture.home_corners,
                fixture.away_corners,
                fixture.home_yellow_cards,
                fixture.away_yellow_cards,
                fixture.home_red_cards,
                fixture.away_red_cards,
                fixture.source_observation_id,
                observation.retrieved_at,
                observation.availability_basis,
                observation.point_in_time_certifiable,
                observation.payload_sha256,
                observation.payload->'statistics' AS statistics,
                observation.provider_response_id,
                observation.rights_approval_id,
                approval.status AS rights_status,
                approval.permitted_uses,
                approval.valid_from AS rights_valid_from,
                approval.valid_until AS rights_valid_until
            FROM veltrix_ai_analyst.provider_fixtures AS fixture
            JOIN veltrix_ai_analyst.source_observations AS observation
              ON observation.id = fixture.source_observation_id
            JOIN veltrix_ai_analyst.source_approvals AS approval
              ON approval.approval_id = observation.rights_approval_id
            WHERE fixture.provider = %s
              AND fixture.source_id = %s
              AND fixture.status = 'FINISHED'
              AND fixture.home_goals IS NOT NULL
              AND fixture.away_goals IS NOT NULL
            ORDER BY fixture.kickoff_at, fixture.id
            """,
            (PROVIDER, SOURCE_ID),
        ).fetchall()
    if not rows:
        raise RuntimeError("no completed fixtures found for the configured provider/source")
    return [dict(row) for row in rows]


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def build_dataset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Join feature vectors to labels while preserving source and rights lineage."""
    required_uses = {"FEATURE_ENGINEERING", "MODEL_TRAINING"}
    for source in rows:
        permitted = set(source.get("permitted_uses") or ())
        retrieved_at = source.get("retrieved_at")
        if (
            source.get("rights_status") != "APPROVED"
            or not required_uses.issubset(permitted)
            or retrieved_at is None
            or source.get("rights_valid_from") is None
            or source["rights_valid_from"] > retrieved_at
            or (
                source.get("rights_valid_until") is not None
                and source["rights_valid_until"] <= retrieved_at
            )
        ):
            raise RuntimeError("RETROSPECTIVE_TRAINING_RIGHTS_NOT_VERIFIED")

    fixtures = [
        HistoricalFixture(
            fixture_id=row["fixture_id"],
            competition_id=row["competition_id"],
            kickoff_at=row["kickoff_at"],
            home_team_id=row["home_team_id"],
            away_team_id=row["away_team_id"],
            home_goals=int(row["home_goals"]),
            away_goals=int(row["away_goals"]),
            home_corners=row["home_corners"],
            away_corners=row["away_corners"],
            home_yellow_cards=row["home_yellow_cards"],
            away_yellow_cards=row["away_yellow_cards"],
            home_red_cards=row["home_red_cards"],
            away_red_cards=row["away_red_cards"],
            home_statistics=row.get("statistics"),
            away_statistics=row.get("statistics"),
        )
        for row in rows
    ]
    feature_rows = build_retrospective_lagged_features(fixtures)
    by_id = {row["fixture_id"]: row for row in feature_rows}
    output_rows = []
    for source in rows:
        feature = by_id[source["fixture_id"]]
        output_rows.append({
            "fixture_id": source["fixture_id"],
            "competition_id": source["competition_id"],
            "kickoff_at": source["kickoff_at"].astimezone(UTC).isoformat(),
            "home_team_id": source["home_team_id"],
            "away_team_id": source["away_team_id"],
            "label": {
                "home_goals": int(source["home_goals"]),
                "away_goals": int(source["away_goals"]),
            },
            "features": feature["features"],
            "feature_provenance": {
                **feature["feature_provenance"],
                "source_observation_id": int(source["source_observation_id"]),
                "provider_response_id": (
                    int(source["provider_response_id"])
                    if source["provider_response_id"] is not None else None
                ),
                "retrieved_at": source["retrieved_at"].astimezone(UTC).isoformat(),
                "availability_basis": source["availability_basis"],
                "point_in_time_certifiable": bool(source["point_in_time_certifiable"]),
                "payload_sha256": str(source["payload_sha256"]).strip(),
                "rights_approval_id": source["rights_approval_id"],
                "rights_status_at_current_read": source["rights_status"],
                "rights_permitted_uses": _json_value(source["permitted_uses"]),
                "rights_valid_from": _json_value(source["rights_valid_from"]),
                "rights_valid_until": _json_value(source["rights_valid_until"]),
            },
            "validation_eligible": False,
            "certification_eligible": False,
        })
    if any(row["validation_eligible"] or row["certification_eligible"] for row in output_rows):
        raise RuntimeError("RETROSPECTIVE_DATASET_ELIGIBILITY_INVARIANT_FAILED")
    return {
        "dataset_type": DATASET_TYPE,
        "provider": PROVIDER,
        "source_id": SOURCE_ID,
        "provenance_mode": PROVENANCE_MODE,
        "created_at": datetime.now(UTC).isoformat(),
        "row_count": len(output_rows),
        "competition_count": len({row["competition_id"] for row in output_rows}),
        "validation_eligible": False,
        "point_in_time_certifiable": False,
        "prospective_dataset_join": False,
        "rows": output_rows,
    }


def write_content_addressed(dataset: dict[str, Any], output_dir: Path) -> tuple[Path, str]:
    canonical = json.dumps(dataset, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    envelope = {**dataset, "dataset_sha256": digest}
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"retrospective-training-{digest}.json"
    path.write_text(
        json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path, digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/retrospective-research"),
    )
    args = parser.parse_args()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is required")
    dataset = build_dataset(load_historical_rows(dsn))
    path, digest = write_content_addressed(dataset, args.output_dir)
    print(json.dumps({
        "dataset_type": dataset["dataset_type"],
        "rows": dataset["row_count"],
        "competitions": dataset["competition_count"],
        "sha256": digest,
        "artifact": str(path),
        "validation_eligible": False,
        "point_in_time_certifiable": False,
        "database_writes": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
