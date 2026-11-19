"""Persist an audited prospective dataset as immutable PIT feature snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from psycopg.types.json import Jsonb


FEATURE_SCHEMA_VERSION = "veltrix-pit-features-v1"


def canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def snapshot_digest(row: dict) -> str:
    return hashlib.sha256(canonical_json(row).encode("utf-8")).hexdigest()


def validate_report(report: dict) -> list[dict]:
    if report.get("report_type") != "VELTRIX_PROSPECTIVE_EXPANDING_DATASET":
        raise ValueError("UNRECOGNIZED_DATASET_REPORT")
    if report.get("status") not in ("READY_FOR_RESEARCH", "NO_PROSPECTIVE_DATA_YET"):
        raise ValueError("DATASET_REPORT_NOT_READY")
    dataset_sha = report.get("dataset_sha256")
    if not isinstance(dataset_sha, str) or len(dataset_sha) != 64:
        raise ValueError("DATASET_HASH_MISSING")
    rows = report.get("rows")
    if not isinstance(rows, list):
        raise ValueError("DATASET_ROWS_MISSING")
    for row in rows:
        if not all(row.get(key) for key in (
            "canonical_fixture_id", "canonical_competition_id",
            "home_team_id", "away_team_id", "kickoff_at",
            "prediction_cutoff_at", "provider_fixture_id",
        )):
            raise ValueError("CANONICAL_SNAPSHOT_IDENTITY_MISSING")
        if row["prediction_cutoff_at"] >= row["kickoff_at"]:
            raise ValueError("PIT_CUTOFF_NOT_BEFORE_KICKOFF")
        if not row.get("feature_lineage"):
            raise ValueError("FEATURE_LINEAGE_MISSING")
        required_uses = {
            "FEATURE_ENGINEERING", "MODEL_TRAINING", "MODEL_VALIDATION"
        }
        for item in row["feature_lineage"]:
            if (
                item.get("availability_basis") != "SYSTEM_OBSERVED_AT"
                or item.get("point_in_time_certifiable") is not True
                or item.get("rights_status") != "APPROVED"
                or not item.get("rights_approval_id")
                or not required_uses.issubset(set(item.get("rights_permitted_uses", [])))
            ):
                raise ValueError("FEATURE_LINEAGE_RIGHTS_OR_PIT_GATE_FAILED")
            if (
                item["system_observed_at"] >= row["kickoff_at"]
                or item["system_observed_at"] > row["prediction_cutoff_at"]
                or item["retrieved_at"] > item["system_observed_at"]
            ):
                raise ValueError("FEATURE_LINEAGE_NOT_STRICTLY_PRE_KICKOFF")
            for digest_key in ("payload_sha256", "raw_response_sha256"):
                digest = item.get(digest_key, "")
                if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                    raise ValueError("FEATURE_LINEAGE_HASH_INVALID")
            for id_key in ("source_observation_id", "source_sighting_id", "provider_response_id"):
                if not isinstance(item.get(id_key), int) or item[id_key] < 1:
                    raise ValueError("FEATURE_LINEAGE_ID_INVALID")
        if row.get("label") is not None:
            label_lineage = row.get("label_lineage") or {}
            if (
                row.get("label_observed_at") is None
                or row["label_observed_at"] <= row["kickoff_at"]
                or label_lineage.get("availability_basis") != "SYSTEM_OBSERVED_AT"
                or label_lineage.get("point_in_time_certifiable") is not True
                or label_lineage.get("rights_status") != "APPROVED"
            ):
                raise ValueError("LABEL_LINEAGE_GATE_FAILED")
    return rows


def persist_report(database_url: str, report: dict) -> dict:
    rows = validate_report(report)
    expected_database = "veltrix_ai_analyst"
    if urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != expected_database:
        raise RuntimeError("DATABASE_URL_PATH_MISMATCH")

    inserted = 0
    unchanged = 0
    with psycopg.connect(database_url) as connection:
        if connection.info.dbname != expected_database:
            raise RuntimeError("DATABASE_NAME_MISMATCH")
        with connection.cursor() as cursor:
            for row in rows:
                provider_competition, provider_fixture = row["fixture_id"].split(":", 1)
                digest = snapshot_digest(row)
                values = (
                    row["canonical_fixture_id"],
                    row["canonical_competition_id"],
                    row["home_team_id"],
                    row["away_team_id"],
                    row["provider"],
                    row["source_id"],
                    provider_fixture,
                    provider_competition,
                    row["kickoff_at"],
                    row["prediction_cutoff_at"],
                    FEATURE_SCHEMA_VERSION,
                    Jsonb(row["features"]),
                    Jsonb(row["feature_lineage"]),
                    Jsonb(row["label"]) if row.get("label") is not None else None,
                    row.get("label_observed_at"),
                    row.get("label_observation_id"),
                    Jsonb(row["label_lineage"]) if row.get("label_lineage") is not None else None,
                    digest,
                    report["dataset_sha256"],
                )
                cursor.execute(
                    """
                    INSERT INTO veltrix_ai_analyst.prospective_feature_snapshots (
                        canonical_fixture_id, canonical_competition_id,
                        home_canonical_team_id, away_canonical_team_id,
                        provider, source_id, provider_fixture_id, provider_competition_id,
                        kickoff_at, prediction_cutoff_at, feature_schema_version,
                        features, feature_lineage, label, label_observed_at,
                        label_observation_id, label_lineage, snapshot_sha256, dataset_sha256
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (
                        canonical_fixture_id, prediction_cutoff_at, feature_schema_version
                    ) DO NOTHING
                    RETURNING id
                    """,
                    values,
                )
                inserted_id = cursor.fetchone()
                if inserted_id:
                    inserted += 1
                    continue
                cursor.execute(
                    """
                    SELECT snapshot_sha256, dataset_sha256
                    FROM veltrix_ai_analyst.prospective_feature_snapshots
                    WHERE canonical_fixture_id = %s
                      AND prediction_cutoff_at = %s
                      AND feature_schema_version = %s
                    """,
                    (
                        row["canonical_fixture_id"],
                        row["prediction_cutoff_at"],
                        FEATURE_SCHEMA_VERSION,
                    ),
                )
                existing = cursor.fetchone()
                if existing is None or existing[0].strip() != digest:
                    raise RuntimeError("IMMUTABLE_SNAPSHOT_IDEMPOTENCY_CONFLICT")
                unchanged += 1
        connection.commit()

    return {
        "status": "PERSISTED",
        "inserted": inserted,
        "unchanged": unchanged,
        "rows": len(rows),
        "dataset_sha256": report["dataset_sha256"],
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--confirm-persist",
        action="store_true",
        help="Required to perform database writes; default behavior is validation only.",
    )
    args = parser.parse_args()
    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows = validate_report(report)
    if not args.confirm_persist:
        print(json.dumps({
            "status": "VALIDATED_READ_ONLY",
            "rows": len(rows),
            "dataset_sha256": report["dataset_sha256"],
        }, sort_keys=True))
        return 0
    database_url = os.getenv("VELTRIX_AI_ANALYST_DATABASE_URL", "").strip()
    if not database_url:
        parser.error("VELTRIX_AI_ANALYST_DATABASE_URL is required for persistence")
    print(json.dumps(persist_report(database_url, report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
