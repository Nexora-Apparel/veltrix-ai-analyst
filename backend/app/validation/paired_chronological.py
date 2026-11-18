# ruff: noqa: I001  # Keep this module's standard-library imports explicit; Ruff's isort check misclassifies this block.
"""Paired chronological diagnostics for retrospective prequential 1X2 reports.

This module consumes predictions already generated in chronological order. It never
uses bookmaker prices and does not claim point-in-time (PIT) certification.
"""
from __future__ import annotations

import collections
import datetime
import math
import random
import typing


MODEL_NAMES = ("elo", "poisson", "ensemble")
OUTCOMES = ("home", "draw", "away")
COLD_START_PHASES = (
    ("cold_start_0", 0, 0),
    ("early_1_4", 1, 4),
    ("developing_5_19", 5, 19),
    ("warm_20_49", 20, 49),
    ("mature_50_plus", 50, None),
)


def _probability_vector(row: dict[str, typing.Any], model: str) -> tuple[float, float, float]:
    if model in ("elo", "poisson"):
        raw = row[f"{model}_1x2"]
        return tuple(float(value) for value in raw)  # type: ignore[return-value]
    elo = row["elo_1x2"]
    poisson = row["poisson_1x2"]
    weight = float(row["ensemble_elo_weight"])
    if not 0.0 <= weight <= 1.0:
        raise ValueError("invalid model probability: ensemble weight outside [0, 1]")
    values = tuple(weight * float(elo[i]) + (1.0 - weight) * float(poisson[i]) for i in range(3))
    total = sum(values)
    return tuple(value / total for value in values)  # type: ignore[return-value]


def _actual(row: dict[str, typing.Any]) -> int:
    home, away = int(row["actual_home_goals"]), int(row["actual_away_goals"])
    return 0 if home > away else 1 if home == away else 2


def _metrics(rows: collections.abc.Sequence[dict[str, typing.Any]], model: str) -> dict[str, float | int]:
    if not rows:
        return {"matches": 0, "brier": 0.0, "log_loss": 0.0}
    brier = 0.0
    log_loss = 0.0
    for row in rows:
        actual = _actual(row)
        probs = _probability_vector(row, model)
        brier += sum((probs[i] - float(i == actual)) ** 2 for i in range(3))
        log_loss -= math.log(max(1e-15, probs[actual]))
    return {"matches": len(rows), "brier": brier / len(rows), "log_loss": log_loss / len(rows)}


def _percentile(values: collections.abc.Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _paired_block_bootstrap(
    rows: collections.abc.Sequence[dict[str, typing.Any]], *, resamples: int, block_size: int, seed: int
) -> dict[str, typing.Any]:
    if len(rows) < 2:
        raise ValueError("at least two paired predictions are required")
    if resamples < 100:
        raise ValueError("resamples must be at least 100")
    if block_size < 1:
        raise ValueError("block_size must be positive")
    rng = random.Random(seed)
    n = len(rows)
    kickoff_groups = _kickoff_batches(rows)
    blocks: list[list[dict[str, typing.Any]]] = []
    for start in range(len(kickoff_groups)):
        block: list[dict[str, typing.Any]] = []
        for group in kickoff_groups[start:]:
            block.extend(group)
            if len(block) >= block_size:
                break
        if block:
            blocks.append(block)
    comparisons: dict[str, typing.Any] = {}
    sample_sizes: list[int] = []
    for left_index, left in enumerate(MODEL_NAMES):
        for right in MODEL_NAMES[left_index + 1:]:
            samples_brier: list[float] = []
            samples_log: list[float] = []
            for _ in range(resamples):
                selected: list[dict[str, typing.Any]] = []
                while len(selected) < n:
                    selected.extend(rng.choice(blocks))
                sample = selected
                sample_sizes.append(len(sample))
                left_metrics = _metrics(sample, left)
                right_metrics = _metrics(sample, right)
                samples_brier.append(float(left_metrics["brier"]) - float(right_metrics["brier"]))
                samples_log.append(float(left_metrics["log_loss"]) - float(right_metrics["log_loss"]))
            original_left = _metrics(rows, left)
            original_right = _metrics(rows, right)
            comparisons[f"{left}_minus_{right}"] = {
                "brier": {
                    "mean_difference": float(original_left["brier"]) - float(original_right["brier"]),
                    "ci_95": [_percentile(samples_brier, 0.025), _percentile(samples_brier, 0.975)],
                },
                "log_loss": {
                    "mean_difference": float(original_left["log_loss"]) - float(original_right["log_loss"]),
                    "ci_95": [_percentile(samples_log, 0.025), _percentile(samples_log, 0.975)],
                },
            }
    return {
        "method": "PAIRED_MOVING_CHRONOLOGICAL_BLOCK_BOOTSTRAP",
        "resamples": resamples,
        "block_size_fixtures": block_size,
        "seed": seed,
        "resample_size_min": min(sample_sizes),
        "resample_size_max": max(sample_sizes),
        "resample_size_policy": "WHOLE_KICKOFF_BATCHES_RETAINED; SAMPLE MAY EXCEED TARGET_FIXTURE_COUNT",
        "comparisons": comparisons,
        "interpretation": "Negative differences favour the left-hand model; intervals are paired and descriptive, not PIT certification.",
    }


def _kickoff_batches(rows: collections.abc.Sequence[dict[str, typing.Any]]) -> list[list[dict[str, typing.Any]]]:
    batches: list[list[dict[str, typing.Any]]] = []
    for row in rows:
        kickoff = datetime.datetime.fromisoformat(row["kickoff_at"])
        if not batches or datetime.datetime.fromisoformat(batches[-1][0]["kickoff_at"]) != kickoff:
            batches.append([])
        batches[-1].append(row)
    return batches


def _periods(rows: collections.abc.Sequence[dict[str, typing.Any]], period_count: int) -> list[dict[str, typing.Any]]:
    batches = _kickoff_batches(rows)
    if not batches:
        return []
    count = min(period_count, len(batches))
    periods = []
    for period_index in range(count):
        start = round(period_index * len(batches) / count)
        end = round((period_index + 1) * len(batches) / count)
        group = [row for batch in batches[start:end] for row in batch]
        if group:
            periods.append({
                "period": period_index + 1,
                "kickoff_start": group[0]["kickoff_at"],
                "kickoff_end": group[-1]["kickoff_at"],
                "matches": len(group),
                "models": {model: _metrics(group, model) for model in MODEL_NAMES},
            })
    return periods


def _cold_start(rows: collections.abc.Sequence[dict[str, typing.Any]]) -> list[dict[str, typing.Any]]:
    batches = _kickoff_batches(rows)
    history_count = 0
    phase_rows: dict[str, list[dict[str, typing.Any]]] = collections.defaultdict(list)
    for batch in batches:
        if history_count == 0:
            phase = "cold_start_0"
        elif history_count <= 4:
            phase = "early_1_4"
        elif history_count <= 19:
            phase = "developing_5_19"
        elif history_count <= 49:
            phase = "warm_20_49"
        else:
            phase = "mature_50_plus"
        phase_rows[phase].extend(batch)
        history_count += len(batch)
    output = []
    for name, low, high in COLD_START_PHASES:
        group = phase_rows.get(name, [])
        output.append({
            "phase": name,
            "prior_finished_fixtures_min": low,
            "prior_finished_fixtures_max": high,
            "matches": len(group),
            "models": {model: _metrics(group, model) for model in MODEL_NAMES} if group else {},
        })
    return output


def _calibration(rows: collections.abc.Sequence[dict[str, typing.Any]], *, bins: int = 10) -> dict[str, typing.Any]:
    if bins < 2:
        raise ValueError("at least two calibration bins are required")
    output: dict[str, typing.Any] = {}
    for class_index, class_name in enumerate(OUTCOMES):
        model_data: dict[str, typing.Any] = {}
        for model in MODEL_NAMES:
            bucket_rows: list[list[tuple[float, float]]] = [[] for _ in range(bins)]
            for row in rows:
                probability = _probability_vector(row, model)[class_index]
                observed = float(_actual(row) == class_index)
                bucket = min(bins - 1, int(probability * bins))
                bucket_rows[bucket].append((probability, observed))
            reliability = []
            total_error = 0.0
            for bucket_index, values in enumerate(bucket_rows):
                if not values:
                    continue
                mean_probability = sum(value[0] for value in values) / len(values)
                observed_frequency = sum(value[1] for value in values) / len(values)
                total_error += len(values) / max(1, len(rows)) * abs(mean_probability - observed_frequency)
                reliability.append({
                    "band": f"{bucket_index / bins:.1f}-{(bucket_index + 1) / bins:.1f}",
                    "matches": len(values),
                    "mean_predicted_probability": mean_probability,
                    "observed_frequency": observed_frequency,
                })
            model_data[model] = {"classwise_ece": total_error, "reliability_bands": reliability}
        output[class_name] = model_data
    return {"bin_count": bins, "binning": "FIXED_WIDTH_ONE_VS_REST_PROBABILITY_BANDS", "classes": output}


def evaluate_paired_chronological_report(
    report: dict[str, typing.Any], *, resamples: int = 2000, block_size: int = 20,
    seed: int = 20261118, period_count: int = 4, calibration_bins: int = 10,
) -> dict[str, typing.Any]:
    if report.get("dataset_type") != "RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED":
        raise ValueError("input must be a non-PIT retrospective prequential report")
    source = report.get("source")
    if not isinstance(source, dict):
        raise ValueError("input must include source chronology adjudication metadata")
    if source.get("chronology_basis") != (
        "PROVIDER_KICKOFF_WITH_EVIDENCE_BACKED_OFFICIAL_CBF_ADJUDICATIONS"
    ):
        raise ValueError("input chronology has not passed official kickoff adjudication")
    applied = source.get("kickoff_adjudications_applied")
    applied_count = source.get("kickoff_adjudication_count")
    if (
        not isinstance(applied, list)
        or type(applied_count) is not int
        or applied_count < 0
        or len(applied) != applied_count
    ):
        raise ValueError("input kickoff adjudication audit is incomplete")
    predictions = report.get("predictions")
    if not isinstance(predictions, list) or len(predictions) < 2:
        raise ValueError("at least two predictions are required")
    rows = sorted(predictions, key=lambda row: (datetime.datetime.fromisoformat(row["kickoff_at"]), row["fixture_id"]))
    for row in rows:
        for model in MODEL_NAMES:
            vector = _probability_vector(row, model)
            if len(vector) != 3 or any(not 0.0 <= value <= 1.0 for value in vector):
                raise ValueError("invalid model probability vector")
            if abs(sum(vector) - 1.0) > 1e-9:
                raise ValueError("model probability vector must sum to one")
    return {
        "evaluation_type": "RETROSPECTIVE_PREQUENTIAL_PAIRED_DIAGNOSTICS_NOT_PIT_CERTIFIED",
        "source_report_sha256": report.get("report_sha256"),
        "fixture_count": len(rows),
        "date_start": rows[0]["kickoff_at"],
        "date_end": rows[-1]["kickoff_at"],
        "protocol_boundary": {
            "this_report": "Full-corpus prequential predictions from the retrospective lagged-results run.",
            "not_comparable_as_same_sample": "The separate nested chronological walk-forward report has a different held-out fixture set and protocol.",
            "prohibited_inference": "Do not pool, rank or claim superiority across these two protocols from aggregate scores.",
            "pit_status": "NOT_PIT_CERTIFIED",
            "bookmaker_odds_used": False,
        },
        "overall": {model: _metrics(rows, model) for model in MODEL_NAMES},
        "chronological_periods": _periods(rows, period_count),
        "cold_start_warmup": _cold_start(rows),
        "paired_block_bootstrap": _paired_block_bootstrap(
            rows, resamples=resamples, block_size=block_size, seed=seed
        ),
        "calibration_reliability": _calibration(rows, bins=calibration_bins),
    }
