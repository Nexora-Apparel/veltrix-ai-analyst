"""Versioned evidence-quality classification for fixture presentation.

The classifier measures evidence coverage; it does not estimate outcome likelihood.
Weights and boundaries must be fitted/selected on development data, frozen per
release, and never tuned against a final evaluation period.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class EvidenceTier(StrEnum):
    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


_SIGNAL_NAMES = (
    "source_reliability",
    "freshness",
    "team_history_coverage",
    "competition_context_coverage",
    "supporting_feature_coverage",
)


@dataclass(frozen=True, slots=True)
class EvidenceSignals:
    """Observed coverage/quality signals, each normalized to [0, 1].

    History coverage is a measured coverage ratio, not a minimum match-count
    rule. Optional supporting features may be absent without excluding a fixture.
    """

    source_reliability: float
    freshness: float
    team_history_coverage: float
    competition_context_coverage: float
    supporting_feature_coverage: float

    def __post_init__(self) -> None:
        for name in _SIGNAL_NAMES:
            value = getattr(self, name)
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and between zero and one")


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    """Frozen, versioned scoring policy calibrated outside the final test set."""

    version: str
    weights: Mapping[str, float]
    medium_threshold: float
    strong_threshold: float

    def __post_init__(self) -> None:
        if not self.version.strip():
            raise ValueError("evidence policy version is required")
        if set(self.weights) != set(_SIGNAL_NAMES):
            raise ValueError("weights must define every evidence signal exactly once")
        values = tuple(self.weights.values())
        if any(not isfinite(value) or value < 0.0 for value in values):
            raise ValueError("evidence weights must be finite and nonnegative")
        if abs(sum(values) - 1.0) > 1e-9:
            raise ValueError("evidence weights must sum to one")
        if not (
            isfinite(self.medium_threshold)
            and isfinite(self.strong_threshold)
            and 0.0 <= self.medium_threshold < self.strong_threshold <= 1.0
        ):
            raise ValueError("tier thresholds must satisfy 0 <= medium < strong <= 1")


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    tier: EvidenceTier
    score: float
    policy_version: str
    signal_values: Mapping[str, float]


def assess_evidence(
    signals: EvidenceSignals, *, policy: EvidencePolicy
) -> EvidenceAssessment:
    """Return a deterministic evidence tier from measured signals and frozen policy."""
    values = {name: float(getattr(signals, name)) for name in _SIGNAL_NAMES}
    score = sum(policy.weights[name] * values[name] for name in _SIGNAL_NAMES)
    if score >= policy.strong_threshold:
        tier = EvidenceTier.STRONG
    elif score >= policy.medium_threshold:
        tier = EvidenceTier.MEDIUM
    else:
        tier = EvidenceTier.LOW
    return EvidenceAssessment(
        tier=tier,
        score=score,
        policy_version=policy.version,
        signal_values=values,
    )
