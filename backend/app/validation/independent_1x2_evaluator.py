"""Independent scoring-only 1X2 evaluator.

This module deliberately does not import model fitters, feature builders, or
prediction-generation code. A trusted orchestration layer must reserve/log a
one-use holdout before it passes records to this evaluator.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from statistics import NormalDist, mean, stdev
from typing import Literal, Sequence

Outcome = Literal["HOME", "DRAW", "AWAY"]
BASELINE_CLIMATOLOGY = "LEAGUE_CLIMATOLOGY_HOME_ADVANTAGE"
BASELINE_TEAM_AWARE = "TUNED_TEAM_AWARE_POISSON_OR_ELO"
_REQUIRED_RIGHTS_USE = "MODEL_VALIDATION"


@dataclass(frozen=True, slots=True)
class EvaluationRow:
    fixture_id: str
    kickoff_at: datetime
    prediction_cutoff_at: datetime
    forecast_generated_at: datetime
    training_cutoff_at: datetime
    label_observed_at: datetime
    outcome: Outcome
    candidate_probabilities: tuple[float, float, float]
    climatology_probabilities: tuple[float, float, float]
    team_baseline_probabilities: tuple[float, float, float]
    label_availability_basis: str
    point_in_time_certifiable: bool
    rights_status: str
    rights_valid_from: datetime
    rights_valid_until: datetime | None
    rights_permitted_uses: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PreRegistration:
    protocol_version: str
    smallest_worthwhile_improvement: float
    alpha: float
    target_power: float
    planned_distinct_dates: int
    minimum_fixtures: int
    bootstrap_replicates: int
    bootstrap_seed: int
    climatology_baseline_version: str
    team_baseline_version: str
    approval_status: Literal["DRAFT", "APPROVED"]
    approval_reference: str
    threshold_sha256: str


@dataclass(frozen=True, slots=True)
class PowerAssessment:
    status: Literal["POWER_SUFFICIENT", "INSUFFICIENT_POWER"]
    mde_by_baseline: dict[str, float | None]
    development_date_count_by_baseline: dict[str, int]
    planned_distinct_dates: int
    smallest_worthwhile_improvement: float
    alpha: float
    target_power: float


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field}_MUST_BE_TIMEZONE_AWARE")


def _protocol_payload(protocol: PreRegistration) -> dict:
    payload = asdict(protocol)
    payload.pop("threshold_sha256")
    return payload


def preregistration_sha256(protocol: PreRegistration) -> str:
    canonical = json.dumps(
        _protocol_payload(protocol),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_preregistration(protocol: PreRegistration) -> None:
    if protocol.approval_status != "APPROVED" or not protocol.approval_reference.strip():
        raise ValueError("PREREGISTRATION_NOT_EXPLICITLY_APPROVED")
    if (
        not math.isfinite(protocol.smallest_worthwhile_improvement)
        or protocol.smallest_worthwhile_improvement <= 0
        or not 0 < protocol.alpha < 1
        or not 0 < protocol.target_power < 1
        or protocol.planned_distinct_dates < 2
        or protocol.minimum_fixtures < 1
        or protocol.bootstrap_replicates < 200
        or not protocol.protocol_version.strip()
        or not protocol.climatology_baseline_version.strip()
        or not protocol.team_baseline_version.strip()
    ):
        raise ValueError("INVALID_PREREGISTERED_THRESHOLD_CONFIGURATION")
    if protocol.threshold_sha256 != preregistration_sha256(protocol):
        raise ValueError("PREREGISTRATION_HASH_MISMATCH")


def assess_power(
    development_daily_improvements: dict[str, dict[str, Sequence[float]]],
    *,
    planned_distinct_dates: int,
    smallest_worthwhile_improvement: float,
    alpha: float,
    target_power: float,
) -> PowerAssessment:
    """Compute MDE from development-period date blocks before holdout access.

    Each inner mapping is date -> per-fixture paired improvement (baseline
    log loss minus candidate log loss). Dates, not individual fixtures, are
    the independent units for the normal-approximation power calculation.
    """
    if planned_distinct_dates < 2 or smallest_worthwhile_improvement <= 0:
        raise ValueError("INVALID_POWER_PLAN")
    if not 0 < alpha < 1 or not 0 < target_power < 1:
        raise ValueError("INVALID_POWER_LEVELS")
    z_alpha = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    z_power = NormalDist().inv_cdf(target_power)
    mde_by_baseline: dict[str, float | None] = {}
    date_counts: dict[str, int] = {}
    for baseline_name in (BASELINE_CLIMATOLOGY, BASELINE_TEAM_AWARE):
        date_values = development_daily_improvements.get(baseline_name)
        if not isinstance(date_values, dict):
            raise ValueError(f"MISSING_DEVELOPMENT_BASELINE:{baseline_name}")
        daily_means = [
            mean(values) for _, values in sorted(date_values.items()) if values
        ]
        date_counts[baseline_name] = len(daily_means)
        if len(daily_means) < 2:
            mde_by_baseline[baseline_name] = None
            continue
        standard_error = stdev(daily_means) / math.sqrt(planned_distinct_dates)
        mde_by_baseline[baseline_name] = (z_alpha + z_power) * standard_error
    sufficient = all(
        date_counts[name] >= 2 and mde_by_baseline[name] <= smallest_worthwhile_improvement
        for name in (BASELINE_CLIMATOLOGY, BASELINE_TEAM_AWARE)
    )
    return PowerAssessment(
        status="POWER_SUFFICIENT" if sufficient else "INSUFFICIENT_POWER",
        mde_by_baseline=mde_by_baseline,
        development_date_count_by_baseline=date_counts,
        planned_distinct_dates=planned_distinct_dates,
        smallest_worthwhile_improvement=smallest_worthwhile_improvement,
        alpha=alpha,
        target_power=target_power,
    )


def _probability_triplet(values: tuple[float, float, float], field: str) -> None:
    if len(values) != 3 or any(
        isinstance(value, bool) or not math.isfinite(value) or value <= 0 or value > 1
        for value in values
    ):
        raise ValueError(f"INVALID_{field.upper()}_PROBABILITIES")
    if not math.isclose(sum(values), 1.0, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError(f"NON_NORMALIZED_{field.upper()}_PROBABILITIES")


def _validate_row(row: EvaluationRow, evaluation_as_of: datetime) -> None:
    for field in (
        "kickoff_at",
        "prediction_cutoff_at",
        "forecast_generated_at",
        "training_cutoff_at",
        "label_observed_at",
        "rights_valid_from",
    ):
        _aware(getattr(row, field), field)
    if row.rights_valid_until is not None:
        _aware(row.rights_valid_until, "rights_valid_until")
    if not row.fixture_id.strip():
        raise ValueError("FIXTURE_ID_REQUIRED")
    if not (
        row.training_cutoff_at <= row.forecast_generated_at
        <= row.prediction_cutoff_at < row.kickoff_at < row.label_observed_at
        <= evaluation_as_of
    ):
        raise ValueError("FIXTURE_CHRONOLOGY_INVALID")
    if (
        row.label_availability_basis != "SYSTEM_OBSERVED_AT"
        or row.point_in_time_certifiable is not True
    ):
        raise ValueError("VALIDATION_LABEL_NOT_POINT_IN_TIME_CERTIFIABLE")
    if (
        row.rights_status != "APPROVED"
        or row.rights_valid_from > evaluation_as_of
        or (row.rights_valid_until is not None and row.rights_valid_until <= evaluation_as_of)
        or _REQUIRED_RIGHTS_USE not in row.rights_permitted_uses
    ):
        raise ValueError("VALIDATION_LABEL_RIGHTS_INVALID")
    if row.outcome not in ("HOME", "DRAW", "AWAY"):
        raise ValueError("INVALID_1X2_OUTCOME")
    _probability_triplet(row.candidate_probabilities, "candidate")
    _probability_triplet(row.climatology_probabilities, "climatology")
    _probability_triplet(row.team_baseline_probabilities, "team_baseline")


def _log_loss(probabilities: tuple[float, float, float], outcome: Outcome) -> float:
    index = {"HOME": 0, "DRAW": 1, "AWAY": 2}[outcome]
    return -math.log(probabilities[index])


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("BOOTSTRAP_SAMPLE_EMPTY")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _date_block_bootstrap(
    improvements_by_date: dict[str, list[float]],
    *,
    replicates: int,
    seed: int,
    alpha: float,
) -> tuple[float, float]:
    dates = sorted(improvements_by_date)
    if len(dates) < 2:
        raise ValueError("BOOTSTRAP_REQUIRES_AT_LEAST_TWO_DATE_BLOCKS")
    rng = random.Random(seed)
    samples = []
    for _ in range(replicates):
        sampled_dates = [rng.choice(dates) for _ in dates]
        values = [
            value
            for date_key in sampled_dates
            for value in improvements_by_date[date_key]
        ]
        samples.append(mean(values))
    return (
        _percentile(samples, alpha / 2.0),
        _percentile(samples, 1.0 - alpha / 2.0),
    )


def evaluate_primary_1x2(
    rows: Sequence[EvaluationRow],
    *,
    evaluation_as_of: datetime,
    protocol: PreRegistration,
    power: PowerAssessment,
) -> dict:
    """Score candidate against both baselines using paired date-block bootstrap.

    This is the primary 1X2 endpoint only. Secondary markets are intentionally
    absent. The caller must reserve and log any final holdout before invoking
    this pure evaluator; one-use enforcement belongs to the database runner.
    """
    _aware(evaluation_as_of, "evaluation_as_of")
    validate_preregistration(protocol)
    if (
        power.planned_distinct_dates != protocol.planned_distinct_dates
        or power.smallest_worthwhile_improvement != protocol.smallest_worthwhile_improvement
        or power.alpha != protocol.alpha
        or power.target_power != protocol.target_power
    ):
        raise ValueError("POWER_ASSESSMENT_PROTOCOL_MISMATCH")
    if power.status == "POWER_SUFFICIENT" and (
        any(
            power.mde_by_baseline.get(name) is None
            or power.mde_by_baseline[name] > protocol.smallest_worthwhile_improvement
            for name in (BASELINE_CLIMATOLOGY, BASELINE_TEAM_AWARE)
        )
        or any(
            power.development_date_count_by_baseline.get(name, 0) < 2
            for name in (BASELINE_CLIMATOLOGY, BASELINE_TEAM_AWARE)
        )
    ):
        raise ValueError("POWER_ASSESSMENT_FALSE_SUFFICIENCY")
    if power.status != "POWER_SUFFICIENT":
        return {
            "status": "INSUFFICIENT_POWER",
            "primary_metric": "1X2_LOG_LOSS",
            "scored_fixtures": 0,
            "mde_by_baseline": power.mde_by_baseline,
            "production_promotion": "LOCKED",
            "value_betting": "LOCKED",
            "secondary_markets": "NOT_EVALUATED",
        }
    if len(rows) < protocol.minimum_fixtures:
        return {
            "status": "INSUFFICIENT_FIXTURES",
            "primary_metric": "1X2_LOG_LOSS",
            "scored_fixtures": 0,
            "production_promotion": "LOCKED",
            "value_betting": "LOCKED",
            "secondary_markets": "NOT_EVALUATED",
        }
    fixture_ids = [row.fixture_id for row in rows]
    if len(set(fixture_ids)) != len(fixture_ids):
        raise ValueError("DUPLICATE_FIXTURE_IDS")
    for row in rows:
        _validate_row(row, evaluation_as_of)
    distinct_dates = {row.kickoff_at.astimezone(timezone.utc).date().isoformat() for row in rows}
    if len(distinct_dates) < protocol.planned_distinct_dates:
        return {
            "status": "INSUFFICIENT_DISTINCT_DATES",
            "primary_metric": "1X2_LOG_LOSS",
            "scored_fixtures": 0,
            "distinct_dates": len(distinct_dates),
            "production_promotion": "LOCKED",
            "value_betting": "LOCKED",
            "secondary_markets": "NOT_EVALUATED",
        }

    groups: dict[str, dict[str, list[float]]] = {
        BASELINE_CLIMATOLOGY: defaultdict(list),
        BASELINE_TEAM_AWARE: defaultdict(list),
    }
    candidate_losses = []
    climatology_losses = []
    team_losses = []
    for row in rows:
        date_key = row.kickoff_at.astimezone(timezone.utc).date().isoformat()
        candidate_loss = _log_loss(row.candidate_probabilities, row.outcome)
        climatology_loss = _log_loss(row.climatology_probabilities, row.outcome)
        team_loss = _log_loss(row.team_baseline_probabilities, row.outcome)
        candidate_losses.append(candidate_loss)
        climatology_losses.append(climatology_loss)
        team_losses.append(team_loss)
        groups[BASELINE_CLIMATOLOGY][date_key].append(climatology_loss - candidate_loss)
        groups[BASELINE_TEAM_AWARE][date_key].append(team_loss - candidate_loss)

    results = {}
    for offset, baseline_name in enumerate((BASELINE_CLIMATOLOGY, BASELINE_TEAM_AWARE)):
        baseline_losses = (
            climatology_losses if baseline_name == BASELINE_CLIMATOLOGY else team_losses
        )
        improvements = [
            baseline - candidate for baseline, candidate in zip(baseline_losses, candidate_losses)
        ]
        lower, upper = _date_block_bootstrap(
            groups[baseline_name],
            replicates=protocol.bootstrap_replicates,
            seed=protocol.bootstrap_seed + offset,
            alpha=protocol.alpha,
        )
        average_improvement = mean(improvements)
        results[baseline_name] = {
            "candidate_log_loss": mean(candidate_losses),
            "baseline_log_loss": mean(baseline_losses),
            "mean_improvement": average_improvement,
            "paired_date_block_ci_lower": lower,
            "paired_date_block_ci_upper": upper,
            "beats_baseline": lower > 0.0,
            "meets_practical_effect": (
                average_improvement >= protocol.smallest_worthwhile_improvement
            ),
            "mde": power.mde_by_baseline[baseline_name],
        }

    passed = all(
        item["beats_baseline"] and item["meets_practical_effect"]
        for item in results.values()
    )
    return {
        "status": "PRIMARY_1X2_PASS" if passed else "PRIMARY_1X2_FAIL",
        "primary_metric": "1X2_LOG_LOSS",
        "scored_fixtures": len(rows),
        "distinct_dates": len(distinct_dates),
        "protocol_sha256": protocol.threshold_sha256,
        "power_status": power.status,
        "mde_by_baseline": power.mde_by_baseline,
        "baselines": results,
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
        "secondary_markets": "NOT_EVALUATED",
    }
