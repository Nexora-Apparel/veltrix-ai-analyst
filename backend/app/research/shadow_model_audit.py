"""Reproduce an archived hierarchical shadow-model fit from immutable artifacts.

This is a fit-integrity audit only. It does not evaluate predictive performance,
certify a model, query a provider, or write to a database.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from math import exp
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)


def _datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("artifact timestamps must be timezone-aware")
    return parsed


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def training_pool_sha256(training_rows: list[dict[str, Any]]) -> str:
    """Match the immutable Stage 6 training-pool fingerprint."""
    return _canonical_json_sha256(training_rows)


def training_data_sha256(training_rows: list[dict[str, Any]]) -> str:
    """Match the exact ordered training fingerprint consumed by shadow inference."""
    ordered = sorted(
        training_rows,
        key=lambda row: (row["kickoff_at"], row["fixture_id"]),
    )
    canonical_rows = [
        {
            "fixture_id": row["fixture_id"],
            "competition_id": row["competition_id"],
            "home_team_id": row["home_team_id"],
            "away_team_id": row["away_team_id"],
            "kickoff_at": row["kickoff_at"],
            "home_goals": int(row["label"]["home_goals"]),
            "away_goals": int(row["label"]["away_goals"]),
            "label_observed_at": row["label_observed_at"],
            "label_observation_id": row["label_observation_id"],
            "label_lineage": row["label_lineage"],
        }
        for row in ordered
    ]
    return _canonical_json_sha256(canonical_rows)


def _training_results(
    training_rows: list[dict[str, Any]],
    training_cutoff_at: datetime,
) -> list[HierarchicalGoalResult]:
    results = []
    for row in training_rows:
        lineage = row.get("label_lineage")
        if (
            row.get("validation_eligible") is not False
            or not isinstance(lineage, dict)
            or lineage.get("availability_basis") != "IMPORT_RUN_COMPLETED_AT_TRAINING_ONLY"
            or lineage.get("point_in_time_certifiable") is not False
        ):
            raise ValueError("TRAINING_POOL_CONTAINS_NON_TRAINING_ONLY_LABEL")
        observed_at = _datetime(row["label_observed_at"])
        kickoff_at = _datetime(row["kickoff_at"])
        if observed_at > training_cutoff_at or kickoff_at > training_cutoff_at:
            raise ValueError("TRAINING_LABEL_OR_FIXTURE_AFTER_MODEL_CUTOFF")
        label = row.get("label")
        if not isinstance(label, dict):
            raise TypeError("TRAINING_LABEL_REQUIRED")
        results.append(
            HierarchicalGoalResult(
                fixture_id=str(row["fixture_id"]),
                kickoff_at=kickoff_at,
                competition_id=str(row["competition_id"]),
                home_team_id=str(row["home_team_id"]),
                away_team_id=str(row["away_team_id"]),
                home_goals=int(label["home_goals"]),
                away_goals=int(label["away_goals"]),
            )
        )
    if not results:
        raise ValueError("EMPTY_TRAINING_POOL")
    return results



def objective_scaling_diagnostics(
    training_rows: list[dict[str, Any]],
    *,
    training_cutoff_at: datetime,
    half_life_days: float,
    team_ridge: float,
    competition_ridge: float,
) -> dict[str, float]:
    """Expose the exact scale mismatch without changing model fitting.

    The fitted objective is weighted-NLL / sum(weights) + unscaled ridge.
    Multiplying the complete objective by sum(weights) shows the equivalent
    summed-NLL penalty coefficients. This is descriptive, not a recommendation
    for a new coefficient.
    """
    if half_life_days <= 0 or team_ridge < 0 or competition_ridge < 0:
        raise ValueError("INVALID_OBJECTIVE_SCALING_INPUT")
    weights = []
    for row in training_rows:
        kickoff = _datetime(row["kickoff_at"])
        age_days = max(0.0, (training_cutoff_at - kickoff).total_seconds() / 86400)
        weights.append(exp(-0.6931471805599453 * age_days / half_life_days))
    total_weight = sum(weights)
    if not total_weight > 0:
        raise ValueError("NON_POSITIVE_TOTAL_TRAINING_WEIGHT")
    return {
        "training_row_count": float(len(training_rows)),
        "total_recency_weight": total_weight,
        "mean_recency_weight": total_weight / len(training_rows),
        "team_ridge_in_averaged_objective": team_ridge,
        "competition_ridge_in_averaged_objective": competition_ridge,
        "equivalent_team_ridge_in_summed_objective": team_ridge * total_weight,
        "equivalent_competition_ridge_in_summed_objective": competition_ridge * total_weight,
        "home_advantage_ridge": 0.0,
    }


def reproduce_shadow_fit(
    dataset: dict[str, Any],
    forecast: dict[str, Any],
    *,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Verify artifact lineage and reproduce every archived expected-goal rate."""
    if dataset.get("report_type") != "VELTRIX_PROSPECTIVE_EXPANDING_DATASET":
        raise ValueError("UNRECOGNIZED_PROSPECTIVE_DATASET")
    if forecast.get("model", {}).get("family") != "HIERARCHICAL_POISSON_DIXON_COLES":
        raise ValueError("UNRECOGNIZED_SHADOW_MODEL_FAMILY")
    if dataset.get("dataset_sha256") != forecast.get("dataset_sha256"):
        raise ValueError("DATASET_FINGERPRINT_MISMATCH")

    training_rows = dataset.get("training_only_rows")
    if not isinstance(training_rows, list):
        raise TypeError("TRAINING_ONLY_ROWS_REQUIRED")
    if len(training_rows) != int(dataset.get("training_only_label_rows", -1)):
        raise ValueError("TRAINING_POOL_COUNT_MISMATCH")

    pool_hash = training_pool_sha256(training_rows)
    if pool_hash != dataset.get("training_pool_sha256"):
        raise ValueError("TRAINING_POOL_FINGERPRINT_MISMATCH")
    training_hash = training_data_sha256(training_rows)
    if training_hash != forecast.get("training_data_sha256"):
        raise ValueError("MODEL_TRAINING_FINGERPRINT_MISMATCH")

    cutoff = _datetime(str(forecast["training_cutoff_at"]))
    results = _training_results(training_rows, cutoff)
    model_meta = forecast["model"]
    scaling = objective_scaling_diagnostics(
        training_rows,
        training_cutoff_at=cutoff,
        half_life_days=float(model_meta["half_life_days"]),
        team_ridge=float(model_meta["team_ridge"]),
        competition_ridge=float(model_meta["competition_ridge"]),
    )
    model = fit_hierarchical_poisson(
        results,
        as_of=cutoff,
        half_life_days=float(model_meta["half_life_days"]),
        team_ridge=float(model_meta["team_ridge"]),
        competition_ridge=float(model_meta["competition_ridge"]),
    )
    if not model.optimizer_converged:
        raise RuntimeError("REPRODUCED_MODEL_DID_NOT_CONVERGE")
    if model.training_fixtures != int(forecast["training_fixture_count"]):
        raise ValueError("FITTED_TRAINING_COUNT_MISMATCH")

    prospective_rows = {
        row["canonical_fixture_id"]: row
        for row in dataset.get("rows", [])
        if row.get("canonical_fixture_id")
    }
    predictions = forecast.get("predictions")
    if not isinstance(predictions, list) or not predictions:
        raise ValueError("ARCHIVED_PREDICTIONS_REQUIRED")

    home_errors = []
    away_errors = []
    one_x_two = []
    favourite_counts = {"HOME": 0, "DRAW": 0, "AWAY": 0}
    for prediction in predictions:
        row = prospective_rows.get(prediction["canonical_fixture_id"])
        if row is None:
            raise ValueError("FORECAST_FIXTURE_MISSING_FROM_DATASET")
        rates = model.predict(
            str(row["home_team_id"]),
            str(row["away_team_id"]),
            str(row["competition_id"]),
        )
        home_errors.append(abs(rates.home_lambda - float(prediction["expected_home_goals"])))
        away_errors.append(abs(rates.away_lambda - float(prediction["expected_away_goals"])))
        market = prediction["markets"]["1X2"]
        one_x_two.append(market)
        favourite_counts[max(market, key=market.get)] += 1

    max_home_error = max(home_errors)
    max_away_error = max(away_errors)
    attack = list(model.attack.values())
    defence = list(model.defence.values())
    mean_probabilities = {
        outcome: mean(float(row[outcome]) for row in one_x_two)
        for outcome in ("HOME", "DRAW", "AWAY")
    }
    probability_sd = {
        outcome: pstdev(float(row[outcome]) for row in one_x_two)
        for outcome in ("HOME", "DRAW", "AWAY")
    }

    return {
        "status": "FIT_REPRODUCTION_VERIFIED"
        if max(max_home_error, max_away_error) <= tolerance
        else "FIT_REPRODUCTION_MISMATCH",
        "evaluation_type": "FIT_REPRODUCTION_ONLY_NOT_OUT_OF_SAMPLE_EVALUATION",
        "training_fixture_count": model.training_fixtures,
        "training_team_count": len(model.attack),
        "training_competition_count": len(model.competition_effects),
        "training_pool_sha256": pool_hash,
        "training_data_sha256": training_hash,
        "training_cutoff_at": model.training_cutoff_at.isoformat(),
        "optimizer_converged": model.optimizer_converged,
        "optimizer_iterations": model.optimizer_iterations,
        "optimizer_gradient_norm": model.optimizer_gradient_norm,
        "objective_scaling": scaling,
        "global_intercept": model.global_intercept,
        "home_advantage_log_rate": model.home_advantage,
        "home_advantage_rate_multiplier": exp(model.home_advantage),
        "team_attack_effect": {
            "population_sd": pstdev(attack),
            "minimum": min(attack),
            "maximum": max(attack),
        },
        "team_defence_effect": {
            "population_sd": pstdev(defence),
            "minimum": min(defence),
            "maximum": max(defence),
        },
        "forecast_count": len(predictions),
        "max_absolute_home_goal_rate_error": max_home_error,
        "max_absolute_away_goal_rate_error": max_away_error,
        "one_x_two_mean_probabilities": mean_probabilities,
        "one_x_two_population_sd": probability_sd,
        "one_x_two_favourite_counts": favourite_counts,
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
        "performance_evaluation_performed": False,
        "point_in_time_certification_claimed": False,
    }


def audit_files(dataset_path: Path, forecast_path: Path) -> dict[str, Any]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    forecast = json.loads(forecast_path.read_text(encoding="utf-8"))
    return reproduce_shadow_fit(dataset, forecast)
