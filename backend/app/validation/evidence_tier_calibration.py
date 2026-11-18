"""Evidence-tier calibration diagnostics for held-out market forecasts."""
from __future__ import annotations

from collections.abc import Mapping
from collections import defaultdict
from dataclasses import dataclass
from math import isfinite, log


TIERS = ("STRONG", "MEDIUM", "LOW")


@dataclass(frozen=True, slots=True)
class MarketForecastObservation:
    fixture_id: str
    evidence_tier: str
    market: str
    probabilities: Mapping[str, float]
    outcome: str

    def __post_init__(self) -> None:
        if not self.fixture_id or not self.market:
            raise ValueError("fixture ID and market are required")
        if self.evidence_tier not in TIERS:
            raise ValueError("evidence tier must be STRONG, MEDIUM or LOW")
        if not self.probabilities or self.outcome not in self.probabilities:
            raise ValueError("outcome must be one of the forecast probability keys")
        values = tuple(self.probabilities.values())
        if any(not isfinite(value) or value < 0 or value > 1 for value in values):
            raise ValueError("probabilities must be finite and within [0, 1]")
        if abs(sum(values) - 1.0) > 1e-8:
            raise ValueError("market probabilities must sum to one")


@dataclass(frozen=True, slots=True)
class TierMarketMetrics:
    evidence_tier: str
    market: str
    observations: int
    brier_score: float
    log_loss: float
    mean_entropy: float
    mean_max_probability: float
    expected_calibration_error: float


def evaluate_evidence_tier_calibration(
    observations: tuple[MarketForecastObservation, ...],
    *,
    bins: int = 10,
) -> tuple[TierMarketMetrics, ...]:
    """Score held-out forecasts independently by market and evidence tier.

    Brier is the multiclass sum-of-squared-error score. ECE is the weighted
    one-vs-rest reliability gap over every class and fixed-width probability bin.
    """
    if bins < 2:
        raise ValueError("at least two calibration bins are required")
    if len({(row.fixture_id, row.market) for row in observations}) != len(observations):
        raise ValueError("duplicate fixture/market observations are not allowed")

    grouped: dict[tuple[str, str], list[MarketForecastObservation]] = defaultdict(list)
    for row in observations:
        grouped[(row.evidence_tier, row.market)].append(row)

    output = []
    for (tier, market), rows in sorted(grouped.items()):
        classes = tuple(rows[0].probabilities)
        if any(tuple(row.probabilities) != classes for row in rows):
            raise ValueError("class keys must be consistent within a market")
        brier_total = 0.0
        logloss_total = 0.0
        entropy_total = 0.0
        max_probability_total = 0.0
        bin_counts = [[0] * bins for _ in classes]
        bin_confidence = [[0.0] * bins for _ in classes]
        bin_frequency = [[0.0] * bins for _ in classes]
        for row in rows:
            probs = row.probabilities
            brier_total += sum(
                (probs[label] - (1.0 if label == row.outcome else 0.0)) ** 2
                for label in classes
            )
            logloss_total -= log(max(probs[row.outcome], 1e-15))
            entropy_total -= sum(p * log(max(p, 1e-15)) for p in probs.values())
            max_probability_total += max(probs.values())
            for class_index, label in enumerate(classes):
                probability = probs[label]
                bin_index = min(bins - 1, int(probability * bins))
                bin_counts[class_index][bin_index] += 1
                bin_confidence[class_index][bin_index] += probability
                bin_frequency[class_index][bin_index] += float(row.outcome == label)

        ece = 0.0
        n = len(rows)
        for class_index in range(len(classes)):
            for bin_index in range(bins):
                count = bin_counts[class_index][bin_index]
                if count:
                    confidence = bin_confidence[class_index][bin_index] / count
                    frequency = bin_frequency[class_index][bin_index] / count
                    ece += (count / (n * len(classes))) * abs(confidence - frequency)
        output.append(TierMarketMetrics(
            evidence_tier=tier,
            market=market,
            observations=n,
            brier_score=brier_total / n,
            log_loss=logloss_total / n,
            mean_entropy=entropy_total / n,
            mean_max_probability=max_probability_total / n,
            expected_calibration_error=ece,
        ))
    return tuple(output)
