"""Strict V1 inference from an independently promoted model artifact.

This module deliberately refuses retrospective/research artifacts. It is a
pure inference boundary; persistence and publication are handled elsewhere.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil, isfinite, sqrt
from typing import Any
from uuid import UUID

from app.contracts.prediction import FixturePredictionRequest, ModelPredictionOutput
from app.models.attack_defence import AttackDefenceModel
from app.models.scoreline import build_scoreline_distribution


class ModelArtifactNotPromoted(ValueError):
    """Raised when an artifact is not eligible for production inference."""


@dataclass(frozen=True, slots=True)
class VerifiedTeamMapping:
    canonical_team_id: UUID
    model_team_id: str
    identity_status: str


def _aware_datetime(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ModelArtifactNotPromoted(f"{field}_MISSING")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ModelArtifactNotPromoted(f"{field}_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ModelArtifactNotPromoted(f"{field}_MUST_BE_TIMEZONE_AWARE")
    return parsed


def _required_text(artifact: dict[str, Any], field: str) -> str:
    value = artifact.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ModelArtifactNotPromoted(f"{field.upper()}_MISSING")
    return value


def _load_promoted_model(artifact: dict[str, Any]) -> tuple[AttackDefenceModel, float, datetime]:
    if artifact.get("deployment_status") != "PRODUCTION_APPROVED":
        raise ModelArtifactNotPromoted("MODEL_NOT_PRODUCTION_APPROVED")
    if artifact.get("point_in_time_certified") is not True:
        raise ModelArtifactNotPromoted("MODEL_TRAINING_DATA_NOT_PIT_CERTIFIED")

    training_cutoff = _aware_datetime(artifact.get("training_cutoff_at"), "training_cutoff_at")
    primary = artifact.get("primary_model")
    if not isinstance(primary, dict):
        raise ModelArtifactNotPromoted("PRIMARY_MODEL_MISSING")

    try:
        attack = {str(k): float(v) for k, v in primary["attack"].items()}
        defence = {str(k): float(v) for k, v in primary["defence"].items()}
        intercept = float(primary["intercept"])
        home_advantage = float(primary["home_advantage_log_rate"])
        half_life_days = float(primary["half_life_days"])
        ridge = float(primary["ridge"])
        training_fixtures = int(primary["training_fixtures"])
        rho = float(artifact["dixon_coles"]["rho"])
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ModelArtifactNotPromoted("MODEL_PARAMETERS_INVALID") from exc

    values = [*attack.values(), *defence.values(), intercept, home_advantage, rho]
    if not all(isfinite(value) for value in values):
        raise ModelArtifactNotPromoted("MODEL_PARAMETERS_NON_FINITE")
    if (
        not attack
        or set(attack) != set(defence)
        or training_fixtures < 1
        or not isfinite(half_life_days)
        or half_life_days <= 0
        or not isfinite(ridge)
        or ridge < 0
    ):
        raise ModelArtifactNotPromoted("MODEL_TEAM_PARAMETERS_INCOMPLETE")

    model = AttackDefenceModel(
        intercept=intercept,
        home_advantage=home_advantage,
        attack=attack,
        defence=defence,
        teams=tuple(sorted(attack)),
        training_fixtures=training_fixtures,
        half_life_days=half_life_days,
        ridge=ridge,
    )
    return model, rho, training_cutoff


def predict_fixture(
    artifact: dict[str, Any],
    request: FixturePredictionRequest,
    *,
    home_team_mapping: VerifiedTeamMapping,
    away_team_mapping: VerifiedTeamMapping,
    generated_at: datetime | None = None,
) -> ModelPredictionOutput:
    """Calculate every V1 market from one scoreline probability matrix."""
    model, rho, training_cutoff = _load_promoted_model(artifact)
    if (
        home_team_mapping.canonical_team_id != request.home_team_id
        or away_team_mapping.canonical_team_id != request.away_team_id
        or home_team_mapping.identity_status != "VERIFIED"
        or away_team_mapping.identity_status != "VERIFIED"
    ):
        raise ValueError("CANONICAL_TEAM_IDENTITY_NOT_VERIFIED")
    if (
        not home_team_mapping.model_team_id
        or not away_team_mapping.model_team_id
        or home_team_mapping.model_team_id == away_team_mapping.model_team_id
    ):
        raise ValueError("RESOLVED_MODEL_TEAM_IDS_REQUIRED_AND_DISTINCT")
    if training_cutoff >= request.prediction_cutoff_at:
        raise ModelArtifactNotPromoted("MODEL_TRAINING_CUTOFF_NOT_BEFORE_PREDICTION")

    # Canonical UUIDs are never assumed to equal provider-local model IDs.
    # The caller must resolve and verify both identities before inference.
    rates = model.predict(
        home_team_mapping.model_team_id, away_team_mapping.model_team_id
    )
    # Choose a fixture-specific grid large enough to avoid material tail loss.
    # The fitted rate parameter is bounded, so this remains computationally small.
    max_rate = max(rates.home_lambda, rates.away_lambda)
    max_goals = min(250, max(15, ceil(max_rate + 12.0 * sqrt(max_rate) + 20.0)))
    distribution = build_scoreline_distribution(
        rates.home_lambda, rates.away_lambda, rho=rho, max_goals=max_goals
    )
    probabilities = distribution.market_probabilities()

    # The API's team IDs may not be provider-local IDs used in the artifact.
    # Unknown IDs intentionally receive neutral team effects through model.predict.
    required_markets = {
        "1X2", "BTTS", "TOTALS_1_5", "TOTALS_2_5", "TOTALS_3_5"
    }
    if not required_markets.issubset(set(request.requested_markets)):
        raise ValueError("REQUEST_MUST_INCLUDE_ALL_V1_MARKETS")

    generated = generated_at or datetime.now(UTC)
    if generated.tzinfo is None or generated.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    if generated < request.prediction_cutoff_at or generated >= request.kickoff_at:
        raise ValueError("GENERATION_TIME_OUTSIDE_PREMATCH_WINDOW")

    primary = artifact["primary_model"]
    model_id = _required_text(artifact, "model_id")
    model_version = _required_text(artifact, "model_version")
    code_commit = _required_text(artifact, "code_commit")
    manifest_id = _required_text(artifact, "training_dataset_manifest_id")
    config = {
        "primary_model": primary,
        "dixon_coles": artifact["dixon_coles"],
    }
    config_sha256 = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    return ModelPredictionOutput(
        prediction_id=f"{request.request_id}:{model_version}",
        request_id=request.request_id,
        model_id=model_id,
        model_version=model_version,
        algorithm="RECENCY_WEIGHTED_ATTACK_DEFENCE_POISSON_DIXON_COLES",
        config_sha256=config_sha256,
        code_commit=code_commit,
        training_dataset_manifest_id=manifest_id,
        training_cutoff_at=training_cutoff,
        feature_snapshot_id=request.feature_snapshot_id,
        feature_schema_version=request.feature_schema_version,
        generated_at=generated,
        prediction_cutoff_at=request.prediction_cutoff_at,
        market_probabilities=probabilities,
        expected_home_goals=rates.home_lambda,
        expected_away_goals=rates.away_lambda,
        uncertainty={
            "status": "NOT_YET_CALIBRATED",
            "scoreline_probability_mass_before_renormalization": distribution.normalization_mass_before,
        },
        coverage={},
        eligibility_status="ELIGIBLE",
        publication_status="NOT_PUBLISHED",
    )
