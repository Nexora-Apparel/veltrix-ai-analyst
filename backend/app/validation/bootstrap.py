"""Paired fold-block bootstrap uncertainty for retrospective model comparisons."""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Sequence


@dataclass(frozen=True, slots=True)
class PairedMetricInterval:
    mean_difference: float
    lower_95: float
    upper_95: float


@dataclass(frozen=True, slots=True)
class PairedFoldBootstrap:
    resamples: int
    seed: int
    brier_difference: PairedMetricInterval
    log_loss_difference: PairedMetricInterval


def paired_fold_block_bootstrap(
    fold_metrics: Sequence[object],
    *,
    resamples: int = 5000,
    seed: int = 20261117,
) -> PairedFoldBootstrap:
    """Resample chronological folds; negative model-minus-baseline favours model."""
    if len(fold_metrics) < 2:
        raise ValueError("at least two chronological folds are required")
    if resamples < 100:
        raise ValueError("at least 100 bootstrap resamples are required")
    rows = []
    for row in fold_metrics:
        count = int(row.fixture_count)
        if count < 1:
            raise ValueError("fold fixture_count must be positive")
        rows.append((
            count,
            float(row.brier_1x2 - row.baseline_brier_1x2),
            float(row.log_loss_1x2 - row.baseline_log_loss_1x2),
        ))
    rng = Random(seed)
    brier_draws, log_draws = [], []
    for _ in range(resamples):
        sampled = [rows[rng.randrange(len(rows))] for _ in rows]
        weight = sum(row[0] for row in sampled)
        brier_draws.append(sum(row[0] * row[1] for row in sampled) / weight)
        log_draws.append(sum(row[0] * row[2] for row in sampled) / weight)
    def interval(draws: list[float], point: float) -> PairedMetricInterval:
        return PairedMetricInterval(
            mean_difference=point,
            lower_95=_percentile(draws, 0.025),
            upper_95=_percentile(draws, 0.975),
        )
    total = sum(row[0] for row in rows)
    point_brier = sum(row[0] * row[1] for row in rows) / total
    point_log = sum(row[0] * row[2] for row in rows) / total
    return PairedFoldBootstrap(
        resamples=resamples,
        seed=seed,
        brier_difference=interval(brier_draws, point_brier),
        log_loss_difference=interval(log_draws, point_log),
    )


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction
