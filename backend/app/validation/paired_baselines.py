"""Paired baseline scoring on an identical held-out fixture set."""
from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite, log


@dataclass(frozen=True, slots=True)
class ProbabilityForecast:
    fixture_id: str
    model_name: str
    probabilities: Mapping[str, float]
    outcome: str
    competition_id: str = "UNSPECIFIED"

    def __post_init__(self) -> None:
        if not self.fixture_id or not self.model_name or not self.competition_id:
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



def _multiclass_scores(rows: list[ProbabilityForecast]) -> tuple[float, float]:
    if not rows:
        raise ValueError("multiclass evaluation rows are required")
    brier = 0.0
    loss = 0.0
    for row in rows:
        brier += sum(
            (probability - (1.0 if label == row.outcome else 0.0)) ** 2
            for label, probability in row.probabilities.items()
        )
        loss -= log(max(row.probabilities[row.outcome], 1e-15))
    return brier / len(rows), loss / len(rows)


def _percentile_interval(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("bootstrap produced no replicates")

    def percentile(q: float) -> float:
        index = (len(ordered) - 1) * q
        lower = int(index)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = index - lower
        return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction

    return {"lower_95": percentile(0.025), "upper_95": percentile(0.975)}


def evaluate_paired_multiclass(
    forecasts: tuple[ProbabilityForecast, ...] | list[ProbabilityForecast],
    *,
    model_name: str,
    baseline_name: str,
    bootstrap_replicates: int = 2000,
    seed: int = 20261118,
) -> dict:
    """Return per-competition metrics and paired stratified bootstrap intervals.

    Deltas are model minus baseline; negative values favour the model. The
    intervals are descriptive and are not a release-certification test.
    """
    if bootstrap_replicates < 200:
        raise ValueError("at least 200 bootstrap replicates are required")
    if model_name == baseline_name:
        raise ValueError("model and baseline names must differ")
    compare_paired_baselines(tuple(forecasts))
    by_model: dict[str, dict[str, ProbabilityForecast]] = defaultdict(dict)
    for row in forecasts:
        by_model[row.model_name][row.fixture_id] = row
    if set(by_model) != {model_name, baseline_name}:
        raise ValueError("requested model and baseline must be the only compared models")
    model_rows = by_model[model_name]
    baseline_rows = by_model[baseline_name]
    fixture_ids = sorted(model_rows)
    for fixture_id in fixture_ids:
        if model_rows[fixture_id].competition_id != baseline_rows[fixture_id].competition_id:
            raise ValueError("paired forecasts must share competition IDs")

    model_ordered = [model_rows[fixture_id] for fixture_id in fixture_ids]
    baseline_ordered = [baseline_rows[fixture_id] for fixture_id in fixture_ids]
    model_brier, model_log = _multiclass_scores(model_ordered)
    baseline_brier, baseline_log = _multiclass_scores(baseline_ordered)
    by_competition: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(model_ordered):
        by_competition[row.competition_id].append(index)

    per_competition = {}
    for competition_id, indices in sorted(by_competition.items()):
        comp_model = [model_ordered[index] for index in indices]
        comp_baseline = [baseline_ordered[index] for index in indices]
        model_comp_brier, model_comp_log = _multiclass_scores(comp_model)
        base_comp_brier, base_comp_log = _multiclass_scores(comp_baseline)
        per_competition[competition_id] = {
            "fixtures": len(indices),
            "model": {"brier_score": model_comp_brier, "log_loss": model_comp_log},
            "baseline": {"brier_score": base_comp_brier, "log_loss": base_comp_log},
            "paired_delta_model_minus_baseline": {
                "brier_score": model_comp_brier - base_comp_brier,
                "log_loss": model_comp_log - base_comp_log,
            },
        }

    rng = random.Random(seed)
    model_brier_samples: list[float] = []
    model_log_samples: list[float] = []
    baseline_brier_samples: list[float] = []
    baseline_log_samples: list[float] = []
    delta_brier_samples: list[float] = []
    delta_log_samples: list[float] = []
    for _ in range(bootstrap_replicates):
        sample_indices: list[int] = []
        for competition_id in sorted(by_competition):
            indices = by_competition[competition_id]
            sample_indices.extend(rng.choice(indices) for _ in range(len(indices)))
        sample_model = [model_ordered[index] for index in sample_indices]
        sample_baseline = [baseline_ordered[index] for index in sample_indices]
        mb, ml = _multiclass_scores(sample_model)
        bb, bl = _multiclass_scores(sample_baseline)
        model_brier_samples.append(mb)
        model_log_samples.append(ml)
        baseline_brier_samples.append(bb)
        baseline_log_samples.append(bl)
        delta_brier_samples.append(mb - bb)
        delta_log_samples.append(ml - bl)

    return {
        "fixtures": len(fixture_ids),
        "model": {
            "brier_score": model_brier,
            "brier_ci_95": _percentile_interval(model_brier_samples),
            "log_loss": model_log,
            "log_loss_ci_95": _percentile_interval(model_log_samples),
        },
        "baseline": {
            "brier_score": baseline_brier,
            "brier_ci_95": _percentile_interval(baseline_brier_samples),
            "log_loss": baseline_log,
            "log_loss_ci_95": _percentile_interval(baseline_log_samples),
        },
        "paired_delta_model_minus_baseline": {
            "brier_score_ci_95": _percentile_interval(delta_brier_samples),
            "log_loss_ci_95": _percentile_interval(delta_log_samples),
            "interpretation": "negative favours model",
        },
        "per_competition": per_competition,
        "bootstrap": {
            "method": "PAIRED_STRATIFIED_BY_COMPETITION",
            "replicates": bootstrap_replicates,
            "seed": seed,
            "release_test": False,
        },
    }
