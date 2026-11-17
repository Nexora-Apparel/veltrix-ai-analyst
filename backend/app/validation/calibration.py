"""Held-out multiclass probability calibration diagnostics."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class CalibrationDiagnostics:
    classwise_ece: float
    top_label_ece: float


def _ece(confidences: list[float], outcomes: list[int], bins: int) -> float:
    count = len(confidences)
    if not count:
        raise ValueError("calibration requires at least one prediction")
    error = 0.0
    for index in range(bins):
        lower, upper = index / bins, (index + 1) / bins
        members = [
            i for i, value in enumerate(confidences)
            if lower <= value < upper or (index == bins - 1 and value == 1.0)
        ]
        if members:
            confidence = sum(confidences[i] for i in members) / len(members)
            observed = sum(outcomes[i] for i in members) / len(members)
            error += len(members) / count * abs(confidence - observed)
    return error


def multiclass_calibration_diagnostics(
    probabilities: Sequence[Sequence[float]],
    outcomes: Sequence[int],
    *,
    bins: int = 10,
) -> CalibrationDiagnostics:
    """Return macro classwise and top-label ECE; does not alter forecasts."""
    if bins < 2:
        raise ValueError("bins must be at least 2")
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

    errors = []
    for class_index in range(classes):
        errors.append(_ece(
            [row[class_index] for row in probabilities],
            [int(outcome == class_index) for outcome in outcomes],
            bins,
        ))
    top_confidence, top_correct = [], []
    for row, outcome in zip(probabilities, outcomes):
        top = max(range(classes), key=lambda index: row[index])
        top_confidence.append(row[top])
        top_correct.append(int(top == outcome))
    return CalibrationDiagnostics(
        classwise_ece=sum(errors) / classes,
        top_label_ece=_ece(top_confidence, top_correct, bins),
    )
