"""Paired baseline scoring on an identical held-out fixture set."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ProbabilityForecast:
    fixture_id: str
    model_name: str
    probabilities: Mapping[str, float]
    outcome: str

    def __post_init__(self) -> None:
        if not self.fixture_id or not self.model_name:
            raise ValueError("fixture and model identifiers are required")
        if not self.probabilities or self.outcome not in self.probabilities:
            raise ValueError("observed outcome must be forecast")
        if any(not isfinite(p) or p < 0 or p > 1 for p in self.probabilities.values()):
            raise ValueError("probabilities must be finite and within [0, 1]")
        if abs(sum(self.probabilities.values()) - 1.0) > 1e-8:
            raise ValueError("probabilities must sum to one")


@dataclass(frozen=True, slots=True)
class PairedModelScore:
    model_name: str
    fixtures: int
    brier_score: float
    log_loss: float


@dataclass(frozen=True, slots=True)
class PairedBaselineComparison:
    fixture_ids: tuple[str, ...]
    scores: tuple[PairedModelScore, ...]
    protocol: str = "IDENTICAL_FIXTURE_PAIRED_MULTICLASS_V1"


def compare_paired_baselines(
    forecasts: tuple[ProbabilityForecast, ...],
) -> PairedBaselineComparison:
    """Require all compared models to score exactly the same fixtures/outcomes."""
    if not forecasts:
        raise ValueError("forecasts are required")
    by_model: dict[str, dict[str, ProbabilityForecast]] = {}
    for row in forecasts:
        model_rows = by_model.setdefault(row.model_name, {})
        if row.fixture_id in model_rows:
            raise ValueError("duplicate model/fixture forecast")
        model_rows[row.fixture_id] = row
    if len(by_model) < 2:
        raise ValueError("at least two models are required")
    fixture_sets = [set(rows) for rows in by_model.values()]
    common = set.intersection(*fixture_sets)
    if not common or any(fixtures != common for fixtures in fixture_sets):
        raise ValueError("models must cover identical fixture IDs")
    ordered_ids = tuple(sorted(common))
    reference = next(iter(by_model.values()))
    classes_by_fixture = {
        fixture_id: tuple(reference[fixture_id].probabilities)
        for fixture_id in ordered_ids
    }
    for model_rows in by_model.values():
        for fixture_id in ordered_ids:
            row = model_rows[fixture_id]
            if row.outcome != reference[fixture_id].outcome:
                raise ValueError("models must use identical observed outcomes")
            if tuple(row.probabilities) != classes_by_fixture[fixture_id]:
                raise ValueError("models must forecast identical outcome classes")

    scores = []
    for model_name, model_rows in sorted(by_model.items()):
        brier = 0.0
        loss = 0.0
        for fixture_id in ordered_ids:
            row = model_rows[fixture_id]
            brier += sum(
                (probability - (1.0 if label == row.outcome else 0.0)) ** 2
                for label, probability in row.probabilities.items()
            )
            loss -= log(max(row.probabilities[row.outcome], 1e-15))
        scores.append(PairedModelScore(
            model_name=model_name,
            fixtures=len(ordered_ids),
            brier_score=brier / len(ordered_ids),
            log_loss=loss / len(ordered_ids),
        ))
    return PairedBaselineComparison(ordered_ids, tuple(scores))
