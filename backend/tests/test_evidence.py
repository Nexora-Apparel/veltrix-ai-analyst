from __future__ import annotations

import pytest

from app.features.evidence import (
    EvidencePolicy,
    EvidenceSignals,
    EvidenceTier,
    assess_evidence,
)

WEIGHTS = {
    "source_reliability": 0.25,
    "freshness": 0.15,
    "team_history_coverage": 0.25,
    "competition_context_coverage": 0.15,
    "supporting_feature_coverage": 0.20,
}


def policy() -> EvidencePolicy:
    # Test-only policy values. Production boundaries must be fitted and frozen
    # from development/validation evidence before a release.
    return EvidencePolicy(
        version="test-policy-v1",
        weights=WEIGHTS,
        medium_threshold=0.45,
        strong_threshold=0.75,
    )


def test_complete_evidence_is_strong() -> None:
    signals = EvidenceSignals(1, 1, 1, 1, 1)
    result = assess_evidence(signals, policy=policy())
    assert result.tier is EvidenceTier.STRONG
    assert result.score == pytest.approx(1.0)
    assert result.policy_version == "test-policy-v1"


def test_partial_evidence_is_medium() -> None:
    signals = EvidenceSignals(0.8, 0.7, 0.6, 0.8, 0.5)
    result = assess_evidence(signals, policy=policy())
    assert result.tier is EvidenceTier.MEDIUM


def test_no_fixture_specific_evidence_is_low() -> None:
    signals = EvidenceSignals(0, 0, 0, 0, 0)
    result = assess_evidence(signals, policy=policy())
    assert result.tier is EvidenceTier.LOW
    assert result.score == 0


def test_sparse_history_is_a_signal_not_a_fixture_rejection() -> None:
    signals = EvidenceSignals(
        source_reliability=1,
        freshness=1,
        team_history_coverage=0.1,
        competition_context_coverage=0.9,
        supporting_feature_coverage=0.4,
    )
    result = assess_evidence(signals, policy=policy())
    assert result.tier in {EvidenceTier.MEDIUM, EvidenceTier.LOW}
    assert result.signal_values["team_history_coverage"] == 0.1


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_reliability", -0.01),
        ("freshness", 1.01),
        ("team_history_coverage", float("nan")),
    ],
)
def test_invalid_signal_values_are_rejected(field: str, value: float) -> None:
    values = {
        "source_reliability": 1,
        "freshness": 1,
        "team_history_coverage": 1,
        "competition_context_coverage": 1,
        "supporting_feature_coverage": 1,
    }
    values[field] = value
    with pytest.raises(ValueError):
        EvidenceSignals(**values)


def test_policy_requires_all_weights_to_sum_to_one() -> None:
    invalid = {**WEIGHTS, "freshness": 0.2}
    with pytest.raises(ValueError, match="sum to one"):
        EvidencePolicy("bad-v1", invalid, 0.4, 0.8)


def test_policy_thresholds_must_be_ordered() -> None:
    with pytest.raises(ValueError, match="thresholds"):
        EvidencePolicy("bad-v1", WEIGHTS, 0.8, 0.7)


def test_same_snapshot_and_policy_are_deterministic() -> None:
    signals = EvidenceSignals(0.9, 0.8, 0.4, 0.7, 0.6)
    assert assess_evidence(signals, policy=policy()) == assess_evidence(
        signals, policy=policy()
    )
