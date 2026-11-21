"""Calibration and probability diagnostics for the preregistered shrinkage repair."""
from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any


OUTCOMES = ("HOME", "DRAW", "AWAY")


def blend_probabilities(
    model: dict[str, float], climatology: dict[str, float], weight: float
) -> dict[str, float]:
    if not 0.0 <= weight <= 1.0:
        raise ValueError("blend weight must be in [0, 1]")
    result = {
        outcome: weight * float(model[outcome])
        + (1.0 - weight) * float(climatology[outcome])
        for outcome in OUTCOMES
    }
    total = sum(result.values())
    if total <= 0 or any(not math.isfinite(value) or value < 0 for value in result.values()):
        raise ValueError("invalid blended probability vector")
    return {key: value / total for key, value in result.items()}


def _actual(row: dict[str, Any]) -> str:
    home = int(row["label"]["home_goals"])
    away = int(row["label"]["away_goals"])
    return "HOME" if home > away else ("DRAW" if home == away else "AWAY")


def _logit(value: float) -> float:
    # Numerical guard is used only for the calibration transform, never to alter
    # the forecast probabilities or their scoring.
    epsilon = 1e-12
    adjusted = min(1.0 - epsilon, max(epsilon, value))
    return math.log(adjusted / (1.0 - adjusted))


def _calibration_fit(pairs: list[tuple[float, int]]) -> dict[str, float | int | str]:
    if len(pairs) < 3 or len({outcome for _, outcome in pairs}) < 2:
        return {
            "method": "logistic_regression_on_forecast_logit",
            "n": len(pairs),
            "intercept": float("nan"),
            "slope": float("nan"),
            "status": "INSUFFICIENT_OUTCOME_VARIATION",
        }
    xs = [_logit(probability) for probability, _ in pairs]
    ys = [float(outcome) for _, outcome in pairs]
    intercept = 0.0
    slope = 1.0
    for _ in range(100):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for x, y in zip(xs, ys):
            eta = max(-35.0, min(35.0, intercept + slope * x))
            fitted = 1.0 / (1.0 + math.exp(-eta))
            variance = max(1e-12, fitted * (1.0 - fitted))
            error = fitted - y
            g0 += error
            g1 += error * x
            h00 += variance
            h01 += variance * x
            h11 += variance * x * x
        determinant = h00 * h11 - h01 * h01
        if determinant <= 1e-14:
            return {
                "method": "logistic_regression_on_forecast_logit",
                "n": len(pairs),
                "intercept": float("nan"),
                "slope": float("nan"),
                "status": "SINGULAR_CALIBRATION_HESSIAN",
            }
        delta0 = (h11 * g0 - h01 * g1) / determinant
        delta1 = (h00 * g1 - h01 * g0) / determinant
        intercept -= delta0
        slope -= delta1
        if max(abs(delta0), abs(delta1)) < 1e-9:
            break
    return {
        "method": "logistic_regression_on_forecast_logit",
        "n": len(pairs),
        "intercept": intercept,
        "slope": slope,
        "status": "COMPUTED",
    }


def reliability_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for outcome in OUTCOMES:
        bins = []
        pairs: list[tuple[float, int]] = []
        for row in rows:
            probability = float(row["probabilities"][outcome])
            observed = int(_actual(row) == outcome)
            pairs.append((probability, observed))
        for index in range(10):
            lower = index / 10.0
            upper = (index + 1) / 10.0
            selected = [
                (probability, observed)
                for probability, observed in pairs
                if lower <= probability < upper
                or (index == 9 and probability == 1.0)
            ]
            bins.append({
                "bin": index,
                "lower_inclusive": lower,
                "upper_exclusive": upper if index < 9 else 1.0000000000000001,
                "count": len(selected),
                "mean_predicted_probability": (
                    sum(p for p, _ in selected) / len(selected) if selected else None
                ),
                "observed_frequency": (
                    sum(y for _, y in selected) / len(selected) if selected else None
                ),
            })
        report[outcome] = {
            "reliability_bins": bins,
            "calibration": _calibration_fit(pairs),
        }
    return report


def extreme_probability_report(rows: list[dict[str, Any]], threshold: float = 0.8) -> dict[str, Any]:
    selected = [
        row for row in rows
        if any(float(row["probabilities"][outcome]) > threshold for outcome in OUTCOMES)
    ]
    hits = sum(_actual(row) == max(
        OUTCOMES, key=lambda outcome: float(row["probabilities"][outcome])
    ) for row in selected)
    return {
        "threshold": threshold,
        "forecast_count_any_outcome_above_threshold": len(selected),
        "hit_count": hits,
        "hit_rate": hits / len(selected) if selected else None,
    }


def paired_date_block_bootstrap(
    differences: list[tuple[str, float]], *, replicates: int = 2000, seed: int = 20261121
) -> dict[str, float | int]:
    if not differences:
        raise ValueError("paired differences are required")
    groups: dict[str, list[float]] = defaultdict(list)
    for date, difference in differences:
        groups[date].append(float(difference))
    dates = sorted(groups)
    mean_difference = sum(value for _, value in differences) / len(differences)
    if len(dates) < 2:
        return {
            "mean": mean_difference, "ci95_low": float("nan"),
            "ci95_high": float("nan"), "date_blocks": len(dates),
        }
    rng = random.Random(seed)
    samples = []
    for _ in range(replicates):
        chosen = [rng.choice(dates) for _ in dates]
        sample = [value for date in chosen for value in groups[date]]
        samples.append(sum(sample) / len(sample))
    samples.sort()
    return {
        "mean": mean_difference,
        "ci95_low": samples[int(0.025 * replicates)],
        "ci95_high": samples[max(0, int(0.975 * replicates) - 1)],
        "date_blocks": len(dates),
    }


def competition_breakdown(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["competition_id"])].append(row)
    result = {}
    for competition, selected in sorted(groups.items()):
        loss = 0.0
        brier = 0.0
        for row in selected:
            actual = _actual(row)
            probabilities = row["probabilities"]
            loss -= math.log(max(1e-15, float(probabilities[actual])))
            brier += sum(
                (float(probabilities[outcome]) - float(outcome == actual)) ** 2
                for outcome in OUTCOMES
            )
        result[competition] = {
            "n": len(selected),
            "log_loss": loss / len(selected),
            "multiclass_brier": brier / len(selected),
            "extreme_probability": extreme_probability_report(selected),
        }
    return result


def evaluation_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("evaluation rows are required")
    loss = 0.0
    brier = 0.0
    for row in rows:
        actual = _actual(row)
        probabilities = row["probabilities"]
        loss -= math.log(max(1e-15, float(probabilities[actual])))
        brier += sum(
            (float(probabilities[outcome]) - float(outcome == actual)) ** 2
            for outcome in OUTCOMES
        )
    return {
        "n": len(rows),
        "log_loss": loss / len(rows),
        "multiclass_brier": brier / len(rows),
        "reliability": reliability_report(rows),
        "extreme_probability": extreme_probability_report(rows),
        "competition_breakdown": competition_breakdown(rows),
    }
