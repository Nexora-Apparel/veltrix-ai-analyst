"""Independent binary-market metrics and stratified paired bootstrap intervals."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import log
import random


_EPSILON = 1e-15


@dataclass(frozen=True, slots=True)
class BinaryForecast:
    fixture_id: str
    competition_id: str
    actual: bool
    probability: float

    def __post_init__(self) -> None:
        if not self.fixture_id.strip() or not self.competition_id.strip():
            raise ValueError("fixture_id and competition_id are required")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("probability must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class BinaryMarketEvaluation:
    fixtures: int
    brier_score: float
    log_loss: float


def binary_metrics(
    rows: tuple[BinaryForecast, ...] | list[BinaryForecast],
) -> BinaryMarketEvaluation:
    if not rows:
        raise ValueError("binary market evaluation requires at least one row")
    brier = 0.0
    loss = 0.0
    for row in rows:
        p = min(1.0 - _EPSILON, max(_EPSILON, row.probability))
        y = 1.0 if row.actual else 0.0
        brier += (row.probability - y) ** 2
        loss -= y * log(p) + (1.0 - y) * log(1.0 - p)
    n = len(rows)
    return BinaryMarketEvaluation(n, brier / n, loss / n)


def _interval(values: list[float]) -> dict[str, float]:
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


def evaluate_paired_binary_market(
    model_rows: tuple[BinaryForecast, ...] | list[BinaryForecast],
    baseline_rows: tuple[BinaryForecast, ...] | list[BinaryForecast],
    *,
    bootstrap_replicates: int = 2000,
    seed: int = 20261118,
) -> dict:
    """Evaluate identical labels with a paired bootstrap stratified by competition.

    Delta is model minus baseline, so a negative interval favours the model.
    This is a descriptive interval, not a release test.
    """
    if bootstrap_replicates < 200:
        raise ValueError("at least 200 bootstrap replicates are required")
    model = {row.fixture_id: row for row in model_rows}
    baseline = {row.fixture_id: row for row in baseline_rows}
    if not model or model.keys() != baseline.keys():
        raise ValueError("model and baseline must cover identical non-empty fixtures")
    for fixture_id, row in model.items():
        other = baseline[fixture_id]
        if row.actual != other.actual or row.competition_id != other.competition_id:
            raise ValueError("paired forecasts must share labels and competition IDs")

    model_ordered = list(model.values())
    baseline_ordered = [baseline[row.fixture_id] for row in model_ordered]
    overall_model = binary_metrics(model_ordered)
    overall_baseline = binary_metrics(baseline_ordered)
    by_comp: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(model_ordered):
        by_comp[row.competition_id].append(index)

    per_competition = {}
    for competition_id, indices in sorted(by_comp.items()):
        model_score = binary_metrics([model_ordered[i] for i in indices])
        baseline_score = binary_metrics([baseline_ordered[i] for i in indices])
        per_competition[competition_id] = {
            "model": {
                "fixtures": model_score.fixtures,
                "brier_score": model_score.brier_score,
                "log_loss": model_score.log_loss,
            },
            "baseline": {
                "fixtures": baseline_score.fixtures,
                "brier_score": baseline_score.brier_score,
                "log_loss": baseline_score.log_loss,
            },
        }

    rng = random.Random(seed)
    deltas_brier: list[float] = []
    deltas_log: list[float] = []
    model_brier: list[float] = []
    model_log: list[float] = []
    baseline_brier: list[float] = []
    baseline_log: list[float] = []
    for _ in range(bootstrap_replicates):
        sampled_indices: list[int] = []
        for competition_id in sorted(by_comp):
            indices = by_comp[competition_id]
            sampled_indices.extend(rng.choice(indices) for _ in range(len(indices)))
        sampled_model = [model_ordered[i] for i in sampled_indices]
        sampled_baseline = [baseline_ordered[i] for i in sampled_indices]
        mm = binary_metrics(sampled_model)
        bm = binary_metrics(sampled_baseline)
        model_brier.append(mm.brier_score)
        model_log.append(mm.log_loss)
        baseline_brier.append(bm.brier_score)
        baseline_log.append(bm.log_loss)
        deltas_brier.append(mm.brier_score - bm.brier_score)
        deltas_log.append(mm.log_loss - bm.log_loss)

    return {
        "fixtures": len(model_ordered),
        "model": {
            "brier_score": overall_model.brier_score,
            "brier_ci_95": _interval(model_brier),
            "log_loss": overall_model.log_loss,
            "log_loss_ci_95": _interval(model_log),
        },
        "baseline": {
            "brier_score": overall_baseline.brier_score,
            "brier_ci_95": _interval(baseline_brier),
            "log_loss": overall_baseline.log_loss,
            "log_loss_ci_95": _interval(baseline_log),
        },
        "paired_delta_model_minus_baseline": {
            "brier_score_ci_95": _interval(deltas_brier),
            "log_loss_ci_95": _interval(deltas_log),
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
