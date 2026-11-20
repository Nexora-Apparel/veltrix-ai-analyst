"""Research-only shadow forecasts from cutoff-valid historical outcomes.

This module writes no database rows and never approves or publishes a model.
It deliberately keeps the current probability model separate from snapshot
features: features are audited and reported, but not used as learned inputs
until prospective labels support feature-model validation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.models.hierarchical_poisson import fit_hierarchical_poisson
from app.validation.prospective_dataset import ProspectiveDatasetRow
from app.validation.prospective_model_evaluation import (
    _estimate_inner_rho,
    _goal_result,
    _label_evidence_valid,
    _lineage_rights_valid,
    _model_distribution,
)

HALF_LIFE_DAYS = 365.0
TEAM_RIDGE = 0.5
COMPETITION_RIDGE = 0.5


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def select_training_rows(
    training_only_rows: list[ProspectiveDatasetRow] | tuple[ProspectiveDatasetRow, ...],
    prospective_rows: list[ProspectiveDatasetRow] | tuple[ProspectiveDatasetRow, ...],
    *,
    prediction_cutoff_at: datetime,
) -> tuple[ProspectiveDatasetRow, ...]:
    """Select labels known and rights-valid before one forecast cutoff."""
    _require_aware(prediction_cutoff_at, "prediction_cutoff_at")
    candidates = [*training_only_rows, *prospective_rows]
    eligible = [
        row for row in candidates
        if row.kickoff_at < prediction_cutoff_at
        and row.label_observed_at is not None
        and row.label_observed_at < prediction_cutoff_at
        and (
            not row.validation_eligible
            or (
                row.prediction_cutoff_at is not None
                and row.prediction_cutoff_at < row.kickoff_at
            )
        )
        and row.canonical_fixture_id is not None
        and row.canonical_competition_id is not None
        and _label_evidence_valid(row)
        and _lineage_rights_valid(
            row.label_lineage, prediction_cutoff_at, ("MODEL_TRAINING",)
        )
    ]
    if len({row.fixture_id for row in eligible}) != len(eligible):
        raise ValueError("DUPLICATE_TRAINING_FIXTURE_IDS")

    # Recheck rights at the actual model training cutoff. A later revocation
    # must not be hidden by an earlier valid import-run completion timestamp.
    while eligible:
        training_cutoff = max(
            row.label_observed_at
            for row in eligible
            if row.label_observed_at is not None
        )
        rights_valid = [
            row for row in eligible
            if _lineage_rights_valid(
                row.label_lineage, training_cutoff, ("MODEL_TRAINING",)
            )
        ]
        if len(rights_valid) == len(eligible):
            return tuple(sorted(
                eligible,
                key=lambda row: (row.kickoff_at, row.fixture_id),
            ))
        eligible = rights_valid
    return ()


def _training_data_sha256(rows: tuple[ProspectiveDatasetRow, ...]) -> str:
    payload = [
        {
            "fixture_id": row.fixture_id,
            "competition_id": row.competition_id,
            "home_team_id": row.home_team_id,
            "away_team_id": row.away_team_id,
            "kickoff_at": row.kickoff_at.isoformat(),
            "home_goals": int(row.label["home_goals"]),
            "away_goals": int(row.label["away_goals"]),
            "label_observed_at": row.label_observed_at.isoformat(),
            "label_observation_id": row.label_observation_id,
            "label_lineage": row.label_lineage,
        }
        for row in rows
    ]
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_shadow_predictions(
    dataset: dict[str, Any],
    *,
    generated_at: datetime | None = None,
    max_fixtures: int = 25,
    max_snapshot_age_hours: float = 6.0,
    minimum_training_fixtures: int = 30,
) -> dict[str, Any]:
    """Build up to 25 fresh, pre-match shadow forecasts without persistence."""
    generated = generated_at or datetime.now(UTC)
    _require_aware(generated, "generated_at")
    if max_fixtures < 1 or minimum_training_fixtures < 1:
        raise ValueError("fixture and training limits must be positive")
    if max_snapshot_age_hours <= 0:
        raise ValueError("max_snapshot_age_hours must be positive")

    raw_rows = dataset.get("rows")
    raw_training = dataset.get("training_only_rows")
    if not isinstance(raw_rows, list) or not isinstance(raw_training, list):
        raise TypeError("PROSPECTIVE_DATASET_ROWS_MISSING")

    rows = tuple(raw_rows)
    training_only_rows = tuple(raw_training)
    fresh_targets = [
        row for row in rows
        if isinstance(row, ProspectiveDatasetRow)
        and row.validation_eligible
        and row.prediction_cutoff_at is not None
        and row.canonical_fixture_id is not None
        and row.canonical_competition_id is not None
        and row.prediction_cutoff_at <= generated
        and row.prediction_cutoff_at < row.kickoff_at
        and row.kickoff_at > generated
        and generated - row.prediction_cutoff_at
            <= timedelta(hours=max_snapshot_age_hours)
    ]
    fresh_targets = sorted(
        fresh_targets,
        key=lambda row: (row.kickoff_at, row.fixture_id),
    )[:max_fixtures]

    base_report: dict[str, Any] = {
        "generated_at": generated.isoformat(),
        "status": "SHADOW_ONLY_NOT_FOR_PUBLICATION",
        "research_only": True,
        "dataset_sha256": dataset.get("dataset_sha256"),
        "feature_schema_version": dataset.get("feature_schema_version"),
        "requested_fixture_limit": max_fixtures,
        "max_snapshot_age_hours": max_snapshot_age_hours,
        "candidate_snapshot_rows": len(rows),
        "fresh_upcoming_fixture_count": len(fresh_targets),
        "training_only_label_rows_available": len(training_only_rows),
        "provider_calls": 0,
        "database_writes": 0,
        "odds_used": False,
        "production_promotion": "LOCKED",
        "release_eligible": False,
        "value_betting": "LOCKED",
        "predictions": [],
        "abstentions": [],
    }
    if not fresh_targets:
        base_report["status"] = "NO_FRESH_UPCOMING_SNAPSHOTS"
        return base_report

    common_cutoff = min(
        row.prediction_cutoff_at
        for row in fresh_targets
        if row.prediction_cutoff_at is not None
    )
    training_rows = select_training_rows(
        training_only_rows,
        rows,
        prediction_cutoff_at=common_cutoff,
    )
    if len(training_rows) < minimum_training_fixtures:
        base_report["status"] = "INSUFFICIENT_CUTOFF_VALID_TRAINING_LABELS"
        base_report["training_fixture_count"] = len(training_rows)
        base_report["required_training_fixtures"] = minimum_training_fixtures
        return base_report

    training_cutoff = max(
        row.label_observed_at
        for row in training_rows
        if row.label_observed_at is not None
    )
    if training_cutoff >= common_cutoff:
        raise ValueError("TRAINING_CUTOFF_NOT_BEFORE_EARLIEST_PREDICTION_CUTOFF")

    model = fit_hierarchical_poisson(
        [_goal_result(row) for row in training_rows],
        as_of=training_cutoff,
        half_life_days=HALF_LIFE_DAYS,
        team_ridge=TEAM_RIDGE,
        competition_ridge=COMPETITION_RIDGE,
    )
    rho, rho_oof_fixtures, rho_status = _estimate_inner_rho(training_rows)
    training_sha256 = _training_data_sha256(training_rows)

    base_report.update({
        "status": "SHADOW_FORECASTS_READY",
        "training_fixture_count": len(training_rows),
        "training_team_count": len(model.attack),
        "training_competition_count": len(model.competition_effects),
        "training_cutoff_at": training_cutoff.isoformat(),
        "earliest_target_prediction_cutoff_at": common_cutoff.isoformat(),
        "training_data_sha256": training_sha256,
        "model": {
            "family": "HIERARCHICAL_POISSON_DIXON_COLES",
            "version": "hierarchical-poisson-shadow-v1",
            "half_life_days": HALF_LIFE_DAYS,
            "team_ridge": TEAM_RIDGE,
            "competition_ridge": COMPETITION_RIDGE,
            "optimizer_converged": model.optimizer_converged,
            "optimizer_iterations": model.optimizer_iterations,
            "optimizer_gradient_norm": model.optimizer_gradient_norm,
            "rho": rho,
            "rho_oof_fixtures": rho_oof_fixtures,
            "rho_status": rho_status,
        },
        "probability_model_inputs": "HISTORICAL_GOAL_OUTCOMES_ONLY",
        "snapshot_feature_usage": (
            "AUDITED_BUT_NOT_USED_IN_PROBABILITIES_PENDING_PROSPECTIVE_FEATURE_VALIDATION"
        ),
    })

    predictions: list[dict[str, Any]] = []
    abstentions: list[dict[str, str]] = []
    for row in fresh_targets:
        cutoff = row.prediction_cutoff_at
        if cutoff is None or training_cutoff >= cutoff:
            abstentions.append({
                "fixture_id": row.fixture_id,
                "reason": "TRAINING_CUTOFF_NOT_BEFORE_FIXTURE_PREDICTION_CUTOFF",
            })
            continue
        try:
            rates = model.predict(
                row.home_team_id, row.away_team_id, row.competition_id
            )
            forecast, applied_rho, max_goals = _model_distribution(model, row, rho)
            feature_values = row.features
            feature_non_null = sum(
                value is not None for value in feature_values.values()
            )
            snapshot_payload = json.dumps(
                {
                    "features": feature_values,
                    "feature_lineage": row.feature_lineage,
                },
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
            predictions.append({
                "canonical_fixture_id": row.canonical_fixture_id,
                "canonical_competition_id": row.canonical_competition_id,
                "kickoff_at": row.kickoff_at.isoformat(),
                "prediction_cutoff_at": cutoff.isoformat(),
                "generated_at": generated.isoformat(),
                "training_cutoff_at": training_cutoff.isoformat(),
                "training_fixture_count": model.training_fixtures,
                "training_data_sha256": training_sha256,
                "expected_home_goals": rates.home_lambda,
                "expected_away_goals": rates.away_lambda,
                "markets": forecast.markets,
                "team_history": {
                    "home_matches": rates.home_team_history,
                    "away_matches": rates.away_team_history,
                    "competition_seen": rates.competition_seen,
                    "calculation_mode": rates.calculation_mode,
                },
                "snapshot_feature_audit": {
                    "field_count": len(feature_values),
                    "non_null_field_count": feature_non_null,
                    "lineage_record_count": len(row.feature_lineage),
                    "sha256": hashlib.sha256(snapshot_payload).hexdigest(),
                },
                "scoreline": {
                    "rho_requested": rho,
                    "rho_applied": applied_rho,
                    "rho_status": rho_status,
                    "max_goals": max_goals,
                    "probability_mass_before_normalization": (
                        forecast.scoreline.normalization_mass_before
                    ),
                },
                "publication_status": "NOT_PUBLISHED",
                "value_betting_status": "LOCKED",
            })
        except (ArithmeticError, ValueError, OverflowError) as exc:
            abstentions.append({
                "fixture_id": row.fixture_id,
                "reason": f"MODEL_CALCULATION_FAILED:{type(exc).__name__}",
            })

    base_report["predictions"] = predictions
    base_report["abstentions"] = abstentions
    base_report["forecast_count"] = len(predictions)
    base_report["abstention_count"] = len(abstentions)
    if not predictions:
        base_report["status"] = "NO_VALID_SHADOW_FORECASTS"
    return base_report
