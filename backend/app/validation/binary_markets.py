"""Proper scoring metrics for every binary V1 market.

These metrics are odds-independent. They evaluate probability quality, not
profitability or value-bet performance.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite, log


@dataclass(frozen=True, slots=True)
class BinaryMarketEvaluation:
    market: str
    samples: int
    brier_score: float
    log_loss: float
    accuracy_at_half: float
    expected_calibration_error: float


_MARKETS = {
    "BTTS": ("YES", lambda home, away: home > 0 and away > 0),
    "TOTALS_1_5": ("OVER", lambda home, away: home + away >= 2),
    "TOTALS_2_5": ("OVER", lambda home, away: home + away >= 3),
    "TOTALS_3_5": ("OVER", lambda home, away: home + away >= 4),
}


def evaluate_binary_markets(
    rows: Sequence[tuple[Mapping[str, Mapping[str, float]], int, int]],
    *,
    bins: int = 10,
) -> dict[str, BinaryMarketEvaluation]:
    """Score BTTS and O/U 1.5, 2.5, 3.5 from pre-match probabilities."""
    if not rows:
        raise ValueError("at least one settled prediction is required")
    if bins < 2:
        raise ValueError("bins must be at least 2")

    evaluations: dict[str, BinaryMarketEvaluation] = {}
    for market, (outcome_key, actual_fn) in _MARKETS.items():
        probabilities: list[float] = []
        outcomes: list[int] = []
        for markets, home_goals, away_goals in rows:
            if home_goals < 0 or away_goals < 0:
                raise ValueError("settled goals cannot be negative")
            try:
                probability = float(markets[market][outcome_key])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"missing probability for {market}.{outcome_key}") from exc
            if not isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError(f"invalid probability for {market}.{outcome_key}")
            probabilities.append(probability)
            outcomes.append(int(actual_fn(home_goals, away_goals)))

        count = len(rows)
        brier = sum((p - y) ** 2 for p, y in zip(probabilities, outcomes)) / count
        log_loss = -sum(
            log(max(1e-15, p if y else 1.0 - p))
            for p, y in zip(probabilities, outcomes)
        ) / count
        accuracy = sum(
            int((p >= 0.5) == bool(y))
            for p, y in zip(probabilities, outcomes)
        ) / count
        ece = 0.0
        for index in range(bins):
            lower, upper = index / bins, (index + 1) / bins
            members = [
                i for i, p in enumerate(probabilities)
                if lower <= p < upper or (index == bins - 1 and p == 1.0)
            ]
            if members:
                mean_probability = sum(probabilities[i] for i in members) / len(members)
                observed_rate = sum(outcomes[i] for i in members) / len(members)
                ece += len(members) / count * abs(mean_probability - observed_rate)

        evaluations[market] = BinaryMarketEvaluation(
            market=market,
            samples=count,
            brier_score=brier,
            log_loss=log_loss,
            accuracy_at_half=accuracy,
            expected_calibration_error=ece,
        )
    return evaluations
