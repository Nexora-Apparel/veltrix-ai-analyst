"""Validation and persistence for the isolated research-only shadow ledger."""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import psycopg
from psycopg.types.json import Jsonb

_HASH = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_STATUSES = {
    "SHADOW_FORECASTS_READY",
    "NO_FRESH_UPCOMING_SNAPSHOTS",
    "INSUFFICIENT_CUTOFF_VALID_TRAINING_LABELS",
    "NO_VALID_SHADOW_FORECASTS",
}
_MARKET_OUTCOMES = {
    "1X2": {"HOME", "DRAW", "AWAY"},
    "BTTS": {"YES", "NO"},
    "TOTALS_1_5": {"OVER", "UNDER"},
    "TOTALS_2_5": {"OVER", "UNDER"},
    "TOTALS_3_5": {"OVER", "UNDER"},
}


def canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    )


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field}_MISSING")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field}_INVALID") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_MUST_BE_TIMEZONE_AWARE")
    return parsed


def _hash(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ValueError(f"{field}_INVALID")
    return value


def validate_shadow_report(report: dict, *, code_commit: str) -> dict:
    if not isinstance(report, dict):
        raise TypeError("SHADOW_REPORT_MUST_BE_OBJECT")
    if report.get("research_only") is not True:
        raise ValueError("RESEARCH_ONLY_FLAG_REQUIRED")
    if report.get("production_promotion") != "LOCKED":
        raise ValueError("PRODUCTION_PROMOTION_MUST_REMAIN_LOCKED")
    if report.get("release_eligible") is not False:
        raise ValueError("RELEASE_MUST_REMAIN_INELIGIBLE")
    if report.get("value_betting") != "LOCKED":
        raise ValueError("VALUE_BETTING_MUST_REMAIN_LOCKED")
    status = report.get("status")
    if status not in _ALLOWED_STATUSES:
        raise ValueError("SHADOW_REPORT_STATUS_NOT_PERSISTABLE")
    if not isinstance(code_commit, str) or not _COMMIT.fullmatch(code_commit):
        raise ValueError("CODE_COMMIT_INVALID")

    generated_at = _timestamp(report.get("generated_at"), "GENERATED_AT")
    dataset_sha = _hash(report.get("dataset_sha256"), "DATASET_SHA256")
    predictions = report.get("predictions")
    abstentions = report.get("abstentions")
    if not isinstance(predictions, list) or not isinstance(abstentions, list):
        raise ValueError("SHADOW_REPORT_COLLECTIONS_INVALID")
    if len(predictions) > 25:
        raise ValueError("SHADOW_FORECAST_LIMIT_EXCEEDED")
    if report.get("forecast_count", len(predictions)) != len(predictions):
        raise ValueError("FORECAST_COUNT_MISMATCH")
    if report.get("abstention_count", len(abstentions)) != len(abstentions):
        raise ValueError("ABSTENTION_COUNT_MISMATCH")

    training_count = report.get("training_fixture_count", 0)
    if (
        isinstance(training_count, bool)
        or not isinstance(training_count, int)
        or training_count < 0
    ):
        raise ValueError("TRAINING_FIXTURE_COUNT_INVALID")
    training_cutoff = None
    training_sha = None
    model_version = None
    if status == "SHADOW_FORECASTS_READY":
        training_cutoff = _timestamp(report.get("training_cutoff_at"), "TRAINING_CUTOFF_AT")
        training_sha = _hash(report.get("training_data_sha256"), "TRAINING_DATA_SHA256")
        model = report.get("model")
        if (
            not isinstance(model, dict)
            or not isinstance(model.get("version"), str)
            or not model["version"].strip()
        ):
            raise ValueError("MODEL_VERSION_MISSING")
        model_version = model["version"]
        if training_count < 1 or not predictions:
            raise ValueError("READY_REPORT_WITHOUT_TRAINING_OR_FORECASTS")

    for prediction in predictions:
        if not isinstance(prediction, dict):
            raise ValueError("FORECAST_RECORD_INVALID")
        if prediction.get("publication_status") != "NOT_PUBLISHED":
            raise ValueError("SHADOW_FORECAST_MUST_NOT_BE_PUBLISHED")
        if prediction.get("value_betting_status") != "LOCKED":
            raise ValueError("SHADOW_FORECAST_VALUE_BETTING_MUST_REMAIN_LOCKED")
        fixture_id = prediction.get("canonical_fixture_id")
        if not isinstance(fixture_id, str) or not fixture_id.strip():
            raise ValueError("CANONICAL_FIXTURE_ID_MISSING")
        cutoff = _timestamp(
            prediction.get("prediction_cutoff_at"), "PREDICTION_CUTOFF_AT"
        )
        kickoff = _timestamp(prediction.get("kickoff_at"), "KICKOFF_AT")
        forecast_generated = _timestamp(
            prediction.get("generated_at"), "FORECAST_GENERATED_AT"
        )
        forecast_training_cutoff = _timestamp(
            prediction.get("training_cutoff_at"), "FORECAST_TRAINING_CUTOFF_AT"
        )
        if not (forecast_training_cutoff < cutoff <= forecast_generated < kickoff):
            raise ValueError("FORECAST_PREMATCH_CHRONOLOGY_INVALID")
        if forecast_generated != generated_at:
            raise ValueError("FORECAST_GENERATION_TIMESTAMP_MISMATCH")
        if training_cutoff is not None and forecast_training_cutoff != training_cutoff:
            raise ValueError("FORECAST_TRAINING_CUTOFF_MISMATCH")
        _hash(prediction.get("training_data_sha256"), "FORECAST_TRAINING_DATA_SHA256")
        markets = prediction.get("markets")
        if not isinstance(markets, dict) or set(markets) != set(_MARKET_OUTCOMES):
            raise ValueError("FORECAST_MARKET_SET_INCOMPLETE")
        for market, expected_outcomes in _MARKET_OUTCOMES.items():
            outcomes = markets[market]
            if not isinstance(outcomes, dict) or set(outcomes) != expected_outcomes:
                raise ValueError(f"FORECAST_MARKET_OUTCOMES_INVALID:{market}")
            values = list(outcomes.values())
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0 or value > 1
                for value in values
            ):
                raise ValueError(f"FORECAST_MARKET_PROBABILITY_INVALID:{market}")
            if abs(sum(values) - 1.0) > 1e-8:
                raise ValueError(f"FORECAST_MARKET_PROBABILITIES_UNBALANCED:{market}")

    report_sha = hashlib.sha256(canonical_json(report).encode("utf-8")).hexdigest()
    run_identity = {
        "generated_at": generated_at.isoformat(),
        "dataset_sha256": dataset_sha,
        "training_data_sha256": training_sha,
        "code_commit": code_commit,
    }
    run_key = hashlib.sha256(canonical_json(run_identity).encode("utf-8")).hexdigest()
    return {
        "run_key": run_key,
        "generated_at": generated_at,
        "status": status,
        "dataset_sha256": dataset_sha,
        "training_data_sha256": training_sha,
        "training_cutoff_at": training_cutoff,
        "training_fixture_count": training_count,
        "model_version": model_version,
        "code_commit": code_commit,
        "forecast_count": len(predictions),
        "abstention_count": len(abstentions),
        "report_sha256": report_sha,
        "report": report,
    }


def persist_shadow_report(
    database_url: str,
    report: dict,
    *,
    code_commit: str,
    write_enabled: bool = False,
) -> dict:
    if write_enabled is not True:
        raise RuntimeError("SHADOW_LEDGER_WRITE_EXPLICIT_OPT_IN_REQUIRED")
    database_name = urlsplit(database_url).path.lstrip("/").split("?", 1)[0]
    if database_name != "veltrix_ai_analyst":
        raise RuntimeError("DATABASE_URL_PATH_MISMATCH")
    record = validate_shadow_report(report, code_commit=code_commit)
    with psycopg.connect(database_url) as connection:
        if connection.info.dbname != "veltrix_ai_analyst":
            raise RuntimeError("DATABASE_NAME_MISMATCH")
        inserted = connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.research_shadow_forecast_runs (
                run_key, generated_at, status, dataset_sha256,
                training_data_sha256, training_cutoff_at, training_fixture_count,
                model_version, code_commit, forecast_count, abstention_count,
                report_sha256, report
            ) VALUES (
                %(run_key)s, %(generated_at)s, %(status)s, %(dataset_sha256)s,
                %(training_data_sha256)s, %(training_cutoff_at)s,
                %(training_fixture_count)s,
                %(model_version)s, %(code_commit)s, %(forecast_count)s, %(abstention_count)s,
                %(report_sha256)s, %(report)s
            )
            ON CONFLICT (run_key) DO NOTHING
            RETURNING run_key
            """,
            {**record, "report": Jsonb(record["report"])},
        ).fetchone()
        if inserted:
            return {"status": "INSERTED", "run_key": record["run_key"]}
        existing = connection.execute(
            """
            SELECT report_sha256
            FROM veltrix_ai_analyst.research_shadow_forecast_runs
            WHERE run_key = %s
            """,
            (record["run_key"],),
        ).fetchone()
        if existing is None or existing[0].strip() != record["report_sha256"]:
            raise RuntimeError("SHADOW_LEDGER_IDEMPOTENCY_CONFLICT")
        return {"status": "ALREADY_RECORDED", "run_key": record["run_key"]}
