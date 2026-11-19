"""Persist an audited prospective dataset as immutable PIT feature snapshots."""
# ruff: noqa: I001
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
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
    label_keys = {
        "label", "label_observed_at", "label_observation_id", "label_lineage"
    }
    immutable_features = dict(row)
    for key in label_keys:
        immutable_features[key] = None
    return hashlib.sha256(canonical_json(immutable_features).encode("utf-8")).hexdigest()


def label_digest(row: dict) -> str:
    label_payload = {
        "label": row["label"],
        "label_observed_at": row["label_observed_at"],
        "label_observation_id": row["label_observation_id"],
        "label_lineage": row["label_lineage"],
    }
    return hashlib.sha256(canonical_json(label_payload).encode("utf-8")).hexdigest()


def parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise TypeError("PIT_TIMESTAMP_MISSING")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("PIT_TIMESTAMP_INVALID") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("PIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    return parsed


def validate_rights_lineage(
    lineage: dict,
    effective_at: datetime,
    required_uses: set[str],
    error_code: str,
) -> None:
    if (
        lineage.get("rights_status") != "APPROVED"
        or not lineage.get("rights_approval_id")
        or not required_uses.issubset(set(lineage.get("rights_permitted_uses", [])))
    ):
        raise ValueError(error_code)
    valid_from = parse_timestamp(lineage.get("rights_valid_from"))
    valid_until_value = lineage.get("rights_valid_until")
    valid_until = (
        parse_timestamp(valid_until_value) if valid_until_value is not None else None
    )
    if valid_from > effective_at or (
        valid_until is not None and valid_until <= effective_at
    ):
        raise ValueError(error_code)
    events = lineage.get("rights_status_events", [])
    if not isinstance(events, list):
        raise TypeError(error_code)
    effective_events = []
    for event in events:
        if not isinstance(event, dict):
            raise TypeError(error_code)
        event_at = parse_timestamp(event.get("effective_at"))
        if event_at <= effective_at:
            event_id = event.get("id")
            if isinstance(event_id, bool) or not isinstance(event_id, int):
                raise ValueError(error_code)
            effective_events.append((event_at, event_id, event.get("status")))
    latest_event = (
        max(effective_events, key=lambda item: (item[0], item[1]))
        if effective_events else None
    )
    if latest_event is not None and latest_event[2] != "APPROVED":
        raise ValueError(error_code)


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
        raise TypeError("DATASET_ROWS_MISSING")
    for row in rows:
        if not all(row.get(key) for key in (
            "canonical_fixture_id", "canonical_competition_id",
            "home_team_id", "away_team_id", "kickoff_at",
            "prediction_cutoff_at", "provider_fixture_id",
        )):
            raise ValueError("CANONICAL_SNAPSHOT_IDENTITY_MISSING")
        kickoff_at = parse_timestamp(row["kickoff_at"])
        cutoff_at = parse_timestamp(row["prediction_cutoff_at"])
        if cutoff_at >= kickoff_at:
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
            ):
                raise ValueError("FEATURE_LINEAGE_RIGHTS_OR_PIT_GATE_FAILED")
            observed_at = parse_timestamp(item["system_observed_at"])
            validate_rights_lineage(
                item, observed_at, required_uses,
                "FEATURE_LINEAGE_RIGHTS_OR_PIT_GATE_FAILED",
            )
            retrieved_at = parse_timestamp(item["retrieved_at"])
            if (
                observed_at >= kickoff_at
                or observed_at > cutoff_at
                or retrieved_at > observed_at
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
            label_observed_at = parse_timestamp(row["label_observed_at"])
            required_label_uses = {"MODEL_TRAINING", "MODEL_VALIDATION"}
            if (
                label_observed_at <= kickoff_at
                or isinstance(row.get("label_observation_id"), bool)
                or not isinstance(row.get("label_observation_id"), int)
                or row["label_observation_id"] < 1
                or not isinstance(row.get("label"), dict)
                or label_lineage.get("availability_basis") != "SYSTEM_OBSERVED_AT"
                or label_lineage.get("point_in_time_certifiable") is not True
                or parse_timestamp(label_lineage.get("system_observed_at")) != label_observed_at
                or parse_timestamp(label_lineage.get("retrieved_at")) > label_observed_at
                or label_lineage.get("source_observation_id") != row.get("label_observation_id")
            ):
                raise ValueError("LABEL_LINEAGE_GATE_FAILED")
            validate_rights_lineage(
                label_lineage, label_observed_at, required_label_uses,
                "LABEL_LINEAGE_GATE_FAILED",
            )
            for digest_key in ("payload_sha256", "raw_response_sha256"):
                digest = label_lineage.get(digest_key, "")
                if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                    raise ValueError("LABEL_LINEAGE_HASH_INVALID")
            for id_key in ("source_observation_id", "source_sighting_id", "provider_response_id"):
                if not isinstance(label_lineage.get(id_key), int) or label_lineage[id_key] < 1:
                    raise ValueError("LABEL_LINEAGE_ID_INVALID")
    return rows


def persist_report(database_url: str, report: dict) -> dict:
    rows = validate_report(report)
    expected_database = "veltrix_ai_analyst"
    if urlsplit(database_url).path.lstrip("/").split("?", 1)[0] != expected_database:
        raise RuntimeError("DATABASE_URL_PATH_MISMATCH")

    inserted = 0
    unchanged = 0
    labels_inserted = 0
    labels_unchanged = 0
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
                        features, feature_lineage, snapshot_sha256, dataset_sha256
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
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
                    snapshot_id = inserted_id[0]
                    inserted += 1
                else:
                    cursor.execute(
                        """
                        SELECT id, snapshot_sha256
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
                    if existing is None or existing[1].strip() != digest:
                        raise RuntimeError("IMMUTABLE_SNAPSHOT_IDEMPOTENCY_CONFLICT")
                    snapshot_id = existing[0]
                    unchanged += 1

                if row.get("label") is None:
                    continue
                lineage = row["label_lineage"]
                digest = label_digest(row)
                cursor.execute(
                    """
                    INSERT INTO veltrix_ai_analyst.prospective_feature_snapshot_labels (
                        snapshot_id, source_observation_id, source_sighting_id,
                        provider_response_id, label, label_observed_at,
                        label_lineage, label_sha256
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_id, source_observation_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        snapshot_id,
                        lineage["source_observation_id"],
                        lineage["source_sighting_id"],
                        lineage["provider_response_id"],
                        Jsonb(row["label"]),
                        row["label_observed_at"],
                        Jsonb(lineage),
                        digest,
                    ),
                )
                label_inserted_id = cursor.fetchone()
                if label_inserted_id:
                    labels_inserted += 1
                else:
                    cursor.execute(
                        """
                        SELECT label_sha256
                        FROM veltrix_ai_analyst.prospective_feature_snapshot_labels
                        WHERE snapshot_id = %s AND source_observation_id = %s
                        """,
                        (snapshot_id, lineage["source_observation_id"]),
                    )
                    existing_label = cursor.fetchone()
                    if existing_label is None or existing_label[0].strip() != digest:
                        raise RuntimeError("IMMUTABLE_LABEL_IDEMPOTENCY_CONFLICT")
                    labels_unchanged += 1
        connection.commit()

    return {
        "status": "PERSISTED",
        "inserted": inserted,
        "unchanged": unchanged,
        "rows": len(rows),
        "labels_inserted": labels_inserted,
        "labels_unchanged": labels_unchanged,
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
