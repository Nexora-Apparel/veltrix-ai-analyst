"""Gated hierarchical prediction orchestration with per-market audit records.

This module is deliberately inert until a validated release manifest is supplied.
It performs no provider calls and writes no production predictions itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from app.features.evidence import (
    EvidenceAssessment,
    EvidencePolicy,
    EvidenceSignals,
    assess_evidence,
)
from app.models.hierarchical_poisson import HierarchicalPoissonModel
from app.models.hierarchical_scoreline import forecast_hierarchical_fixture


@dataclass(frozen=True, slots=True)
class ValidatedModelRelease:
    model_version: str
    release_id: str
    rho: float
    rho_development_protocol: str
    hyperparameter_protocol: str
    validation_report_id: str
    approved: bool = False

    def __post_init__(self) -> None:
        if not all((
            self.model_version.strip(),
            self.release_id.strip(),
            self.rho_development_protocol.strip(),
            self.hyperparameter_protocol.strip(),
            self.validation_report_id.strip(),
        )):
            raise ValueError("release provenance fields are required")


@dataclass(frozen=True, slots=True)
class MarketAvailability:
    available: bool
    probabilities: Mapping[str, float] | None
    reason_code: str | None


@dataclass(frozen=True, slots=True)
class PredictionAuditRecord:
    fixture_id: str
    generated_at: datetime
    model_version: str
    release_id: str
    validation_report_id: str
    training_cutoff_at: datetime
    evidence: EvidenceAssessment
    rho: float
    rho_development_protocol: str
    hyperparameter_protocol: str
    optimizer_iterations: int
    optimizer_gradient_norm: float
    market_availability: Mapping[str, MarketAvailability]


@dataclass(frozen=True, slots=True)
class OrchestratedPrediction:
    fixture_id: str
    evidence: EvidenceAssessment
    markets: Mapping[str, MarketAvailability]
    audit: PredictionAuditRecord


def generate_hierarchical_prediction(
    *,
    fixture_id: str,
    home_team_id: str,
    away_team_id: str,
    competition_id: str,
    model: HierarchicalPoissonModel,
    release: ValidatedModelRelease,
    evidence_signals: EvidenceSignals,
    evidence_policy: EvidencePolicy,
    generated_at: datetime,
) -> OrchestratedPrediction:
    """Generate audited market forecasts only from an approved frozen release."""
    if not release.approved:
        raise RuntimeError("MODEL_RELEASE_NOT_VALIDATED")
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    if not model.optimizer_converged:
        raise RuntimeError("MODEL_OPTIMIZER_NOT_CONVERGED")
    evidence = assess_evidence(evidence_signals, policy=evidence_policy)
    markets: dict[str, MarketAvailability] = {}
    try:
        forecast = forecast_hierarchical_fixture(
            model,
            home_team_id,
            away_team_id,
            competition_id,
            rho=release.rho,
        )
        for market, outcomes in forecast.markets.items():
            valid = (
                bool(outcomes)
                and all(0.0 <= probability <= 1.0 for probability in outcomes.values())
                and abs(sum(outcomes.values()) - 1.0) <= 1e-8
            )
            markets[market] = MarketAvailability(
                available=valid,
                probabilities=dict(outcomes) if valid else None,
                reason_code=None if valid else "INVALID_MARKET_DISTRIBUTION",
            )
    except (ArithmeticError, ValueError, OverflowError):
        for market in ("1X2", "BTTS", "TOTALS_1_5", "TOTALS_2_5", "TOTALS_3_5"):
            markets[market] = MarketAvailability(
                available=False,
                probabilities=None,
                reason_code="MODEL_MARKET_CALCULATION_FAILED",
            )

    audit = PredictionAuditRecord(
        fixture_id=fixture_id,
        generated_at=generated_at,
        model_version=release.model_version,
        release_id=release.release_id,
        validation_report_id=release.validation_report_id,
        training_cutoff_at=model.training_cutoff_at,
        evidence=evidence,
        rho=release.rho,
        rho_development_protocol=release.rho_development_protocol,
        hyperparameter_protocol=release.hyperparameter_protocol,
        optimizer_iterations=model.optimizer_iterations,
        optimizer_gradient_norm=model.optimizer_gradient_norm,
        market_availability=markets,
    )
    return OrchestratedPrediction(
        fixture_id=fixture_id,
        evidence=evidence,
        markets=markets,
        audit=audit,
    )
