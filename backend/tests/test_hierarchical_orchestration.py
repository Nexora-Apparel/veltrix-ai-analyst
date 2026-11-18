from datetime import UTC, datetime, timedelta

import pytest

from app.features.evidence import EvidencePolicy, EvidenceSignals
from app.models.hierarchical_poisson import HierarchicalGoalResult, fit_hierarchical_poisson
from app.orchestration.hierarchical_predictions import (
    ValidatedModelRelease,
    generate_hierarchical_prediction,
)


def _model():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    teams = ("A", "B", "C", "D", "E", "F")
    rows = [
        HierarchicalGoalResult(
            fixture_id=str(day),
            kickoff_at=start + timedelta(days=day),
            competition_id="league",
            home_team_id=teams[day % 6],
            away_team_id=teams[(day + 1) % 6],
            home_goals=(day * 3) % 4,
            away_goals=(day * 5) % 3,
        )
        for day in range(1, 41)
    ]
    return fit_hierarchical_poisson(rows)


def _release(approved):
    return ValidatedModelRelease(
        model_version="hier-poisson-test",
        release_id="test-release",
        rho=0.0,
        rho_development_protocol="OOF_DIXON_COLES_PROFILE_NLL_V1",
        hyperparameter_protocol="EXPANDING_WINDOW_PAIRED_POISSON_NLL_V1",
        validation_report_id="test-report",
        approved=approved,
    )


def _policy():
    return EvidencePolicy(
        version="test-policy",
        weights={
            "source_reliability": 0.2,
            "freshness": 0.2,
            "team_history_coverage": 0.2,
            "competition_context_coverage": 0.2,
            "supporting_feature_coverage": 0.2,
        },
        medium_threshold=0.4,
        strong_threshold=0.75,
    )


def test_orchestration_blocks_unvalidated_release():
    with pytest.raises(RuntimeError, match="MODEL_RELEASE_NOT_VALIDATED"):
        generate_hierarchical_prediction(
            fixture_id="fixture-1",
            home_team_id="A",
            away_team_id="B",
            competition_id="league",
            model=_model(),
            release=_release(False),
            evidence_signals=EvidenceSignals(1, 1, 1, 1, 1),
            evidence_policy=_policy(),
            generated_at=datetime(2026, 3, 1, tzinfo=UTC),
        )


def test_orchestration_emits_market_results_and_audit_for_approved_release():
    result = generate_hierarchical_prediction(
        fixture_id="fixture-2",
        home_team_id="A",
        away_team_id="B",
        competition_id="league",
        model=_model(),
        release=_release(True),
        evidence_signals=EvidenceSignals(1, 1, 1, 1, 1),
        evidence_policy=_policy(),
        generated_at=datetime(2026, 3, 1, tzinfo=UTC),
    )
    assert result.evidence.tier.value == "STRONG"
    assert result.audit.release_id == "test-release"
    assert result.audit.training_cutoff_at == result.audit.training_cutoff_at
    assert result.markets["1X2"].available
    assert result.markets["BTTS"].available
    assert sum(result.markets["1X2"].probabilities.values()) == pytest.approx(1.0)
