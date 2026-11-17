"""Fold-contained multiclass temperature scaling utilities.

Fit only on earlier inner out-of-fold predictions, never on outer test labels.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import exp, isfinite, log


@dataclass(frozen=True, slots=True)
class TemperatureFit:
    temperature: float
    sample_count: int
    log_loss_before: float
    log_loss_after: float


def _validate(
    probabilities: Sequence[Sequence[float]], outcomes: Sequence[int]
) -> int:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("probabilities and outcomes must have equal nonzero length")
    classes = len(probabilities[0])
    if classes < 2:
        raise ValueError("at least two classes are required")
    for row, outcome in zip(probabilities, outcomes):
        if len(row) != classes or outcome < 0 or outcome >= classes:
            raise ValueError("inconsistent class count or invalid outcome")
        if any(not isfinite(value) or value < 0 or value > 1 for value in row):
            raise ValueError("probabilities must be finite and in [0, 1]")
        if abs(sum(row) - 1.0) > 1e-6:
            raise ValueError("each probability row must sum to one")
    return classes


def apply_temperature(
    probabilities: Sequence[Sequence[float]], temperature: float
) -> list[tuple[float, ...]]:
    """Scale multiclass logits and return normalized probabilities."""
    if not isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be finite and positive")
    output: list[tuple[float, ...]] = []
    for row in probabilities:
        if not row or any(not isfinite(value) or value < 0 or value > 1 for value in row):
            raise ValueError("probabilities must be finite and in [0, 1]")
        logits = [log(max(value, 1e-15)) / temperature for value in row]
        maximum = max(logits)
        values = [exp(value - maximum) for value in logits]
        total = sum(values)
        output.append(tuple(value / total for value in values))
    return output


def _log_loss(probabilities: Sequence[Sequence[float]], outcomes: Sequence[int]) -> float:
    return sum(-log(max(1e-15, row[outcome])) for row, outcome in zip(probabilities, outcomes)) / len(outcomes)


def fit_temperature(
    probabilities: Sequence[Sequence[float]],
    outcomes: Sequence[int],
    *,
    min_samples: int = 30,
    min_temperature: float = 0.25,
    max_temperature: float = 4.0,
    iterations: int = 80,
) -> TemperatureFit:
    """Fit one scalar temperature by inner-OOF multiclass log loss."""
    _validate(probabilities, outcomes)
    if len(probabilities) < min_samples:
        raise ValueError(f"at least {min_samples} inner OOF samples are required")
    if min_temperature <= 0 or max_temperature <= min_temperature or iterations < 20:
        raise ValueError("invalid temperature search bounds or iterations")
    before = _log_loss(probabilities, outcomes)

    # Golden-section search in log-temperature space guarantees T > 0.
    left, right = log(min_temperature), log(max_temperature)
    ratio = (5**0.5 - 1.0) / 2.0

    def objective(log_temperature: float) -> float:
        scaled = apply_temperature(probabilities, exp(log_temperature))
        return _log_loss(scaled, outcomes)

    x1 = right - ratio * (right - left)
    x2 = left + ratio * (right - left)
    f1, f2 = objective(x1), objective(x2)
    for _ in range(iterations):
        if f1 <= f2:
            right, x2, f2 = x2, x1, f1
            x1 = right - ratio * (right - left)
            f1 = objective(x1)
        else:
            left, x1, f1 = x1, x2, f2
            x2 = left + ratio * (right - left)
            f2 = objective(x2)
    candidates = [(1.0, before), (exp(x1), f1), (exp(x2), f2)]
    temperature, after = min(candidates, key=lambda item: (item[1], abs(item[0] - 1.0)))
    return TemperatureFit(
        temperature=temperature,
        sample_count=len(probabilities),
        log_loss_before=before,
        log_loss_after=after,
    )
