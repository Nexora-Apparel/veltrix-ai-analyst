"""Fail-closed validation for retrospective research report artifacts."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from typing import Any


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _aware_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise TypeError("PREDICTION_TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("PREDICTION_TIMESTAMP_INVALID") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("PREDICTION_TIMESTAMP_NOT_AWARE")
    return parsed


def validate_retrospective_report(report: dict[str, Any]) -> None:
    """Validate report integrity, source accounting, chronology and scorecard shape."""
    if not isinstance(report, dict):
        raise TypeError("REPORT_ROOT_MUST_BE_OBJECT")
    supplied_hash = report.get("report_sha256")
    if not isinstance(supplied_hash, str) or len(supplied_hash) != 64:
        raise ValueError("REPORT_SHA256_MISSING_OR_INVALID")
    unsigned = {key: value for key, value in report.items() if key != "report_sha256"}
    try:
        canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError("REPORT_NOT_JSON_SAFE") from None
    actual_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if actual_hash != supplied_hash.casefold():
        raise ValueError("REPORT_SHA256_MISMATCH")

    if report.get("dataset_type") != "RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED":
        raise ValueError("REPORT_DATASET_TYPE_INVALID")
    fixture_count = report.get("fixture_count")
    team_count = report.get("team_count")
    if type(fixture_count) is not int or fixture_count < 1:
        raise ValueError("REPORT_FIXTURE_COUNT_INVALID")
    if type(team_count) is not int or team_count < 2:
        raise ValueError("REPORT_TEAM_COUNT_INVALID")

    source = report.get("source")
    if not isinstance(source, dict):
        raise TypeError("REPORT_SOURCE_ACCOUNTING_MISSING")
    source_rows = source.get("source_rows")
    finished = source.get("finished_labeled_rows")
    unknown = source.get("unknown_unlabeled_rows_excluded")
    invalid = source.get("invalid_rows")
    if any(type(value) is not int or value < 0 for value in (source_rows, finished, unknown, invalid)):
        raise ValueError("REPORT_SOURCE_ACCOUNTING_INVALID")
    if finished != fixture_count or source_rows != finished + unknown + invalid:
        raise ValueError("REPORT_SOURCE_ACCOUNTING_MISMATCH")
    if invalid != 0:
        raise ValueError("REPORT_INVALID_SOURCE_ROWS_PRESENT")
    if source.get("identity_namespace") != "PROVIDER_LOCAL_TEAM_IDS":
        raise ValueError("REPORT_IDENTITY_NAMESPACE_INVALID")
    if source.get("feature_semantics") != "RETROSPECTIVE_LAGGED_RESULTS_NOT_HISTORICAL_PIT_REPLAY":
        raise ValueError("REPORT_FEATURE_SEMANTICS_INVALID")

    predictions = report.get("predictions")
    if not isinstance(predictions, list) or len(predictions) != fixture_count:
        raise ValueError("REPORT_PREDICTION_COUNT_MISMATCH")
    fixture_ids: set[str] = set()
    previous_key: tuple[datetime, str] | None = None
    for prediction in predictions:
        if not isinstance(prediction, dict):
            raise TypeError("REPORT_PREDICTION_INVALID")
        fixture_id = prediction.get("fixture_id")
        if not isinstance(fixture_id, str) or not fixture_id or fixture_id in fixture_ids:
            raise ValueError("REPORT_DUPLICATE_OR_INVALID_FIXTURE_ID")
        fixture_ids.add(fixture_id)
        kickoff = _aware_timestamp(prediction.get("kickoff_at"))
        key = (kickoff, fixture_id)
        if previous_key is not None and key < previous_key:
            raise ValueError("REPORT_PREDICTIONS_NOT_CHRONOLOGICAL")
        previous_key = key
        for score_key in ("actual_home_goals", "actual_away_goals"):
            score = prediction.get(score_key)
            if type(score) is not int or score < 0:
                raise ValueError("REPORT_ACTUAL_SCORE_INVALID")
        for probability_key in ("elo_1x2", "poisson_1x2"):
            probabilities = prediction.get(probability_key)
            if not isinstance(probabilities, list) or len(probabilities) != 3:
                raise ValueError("REPORT_PROBABILITY_VECTOR_INVALID")
            if any(not _finite_number(value) or not 0.0 <= value <= 1.0 for value in probabilities):
                raise ValueError("REPORT_PROBABILITY_INVALID")
            if not math.isclose(sum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-9):
                raise ValueError("REPORT_PROBABILITIES_NOT_NORMALIZED")
        rates = prediction.get("goal_rates")
        if not isinstance(rates, list) or len(rates) != 2:
            raise ValueError("REPORT_GOAL_RATES_INVALID")
        if any(not _finite_number(value) or value <= 0 for value in rates):
            raise ValueError("REPORT_GOAL_RATES_INVALID")
        if not _finite_number(prediction.get("rho")):
            raise ValueError("REPORT_RHO_INVALID")
        weight = prediction.get("ensemble_elo_weight")
        if not _finite_number(weight) or not 0.0 <= weight <= 1.0:
            raise ValueError("REPORT_ENSEMBLE_WEIGHT_INVALID")

    for model_name in ("elo", "poisson", "ensemble"):
        scorecard = report.get(model_name)
        if not isinstance(scorecard, dict):
            raise TypeError("REPORT_SCORECARD_MISSING:" + model_name)
        if scorecard.get("matches") != float(fixture_count):
            raise TypeError("REPORT_SCORECARD_MATCH_COUNT_MISMATCH:" + model_name)
        brier = scorecard.get("brier")
        log_loss = scorecard.get("log_loss")
        if not _finite_number(brier) or not 0.0 <= brier <= 2.0:
            raise ValueError("REPORT_SCORECARD_BRIER_INVALID:" + model_name)
        if not _finite_number(log_loss) or log_loss < 0.0:
            raise ValueError("REPORT_SCORECARD_LOG_LOSS_INVALID:" + model_name)

    baseline = report.get("ensemble_elo_weight_baseline")
    mean = report.get("ensemble_elo_weight_mean")
    minimum = report.get("ensemble_elo_weight_min")
    maximum = report.get("ensemble_elo_weight_max")
    if any(not _finite_number(value) or not 0.0 <= value <= 1.0 for value in (baseline, mean, minimum, maximum)):
        raise ValueError("REPORT_ENSEMBLE_WEIGHT_SUMMARY_INVALID")
    if not minimum <= mean <= maximum:
        raise ValueError("REPORT_ENSEMBLE_WEIGHT_SUMMARY_ORDER_INVALID")
    if not _finite_number(report.get("dixon_coles_rho_full_corpus_diagnostic_only")):
        raise ValueError("REPORT_RHO_DIAGNOSTIC_INVALID")
