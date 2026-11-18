"""Development-only Dixon-Coles rho estimation from out-of-fold goal rates."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite, lgamma, log


@dataclass(frozen=True, slots=True)
class DixonColesObservation:
    home_goals: int
    away_goals: int
    home_lambda: float
    away_lambda: float

    def __post_init__(self) -> None:
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("observed goals cannot be negative")
        if (
            not isfinite(self.home_lambda) or not isfinite(self.away_lambda)
            or self.home_lambda <= 0 or self.away_lambda <= 0
        ):
            raise ValueError("out-of-fold goal rates must be positive and finite")


@dataclass(frozen=True, slots=True)
class DixonColesRhoEstimate:
    rho: float
    negative_log_likelihood: float
    observations: int
    lower_bound: float
    upper_bound: float
    protocol: str = "OOF_DIXON_COLES_PROFILE_NLL_V1"


def estimate_dixon_coles_rho(
    observations: Iterable[DixonColesObservation],
    *,
    max_iterations: int = 160,
    tolerance: float = 1e-9,
) -> DixonColesRhoEstimate:
    """Fit one shared rho using development-only out-of-fold forecasts.

    The feasible interval is intersected across all forecast pairs so none of
    the four low-score correction factors becomes negative.
    """
    rows = tuple(observations)
    if len(rows) < 20:
        raise ValueError("at least 20 out-of-fold observations are required")
    if max_iterations < 1 or not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("invalid optimization settings")

    lower = max(
        max(-1.0 / row.home_lambda, -1.0 / row.away_lambda, -1.0)
        for row in rows
    )
    upper = min(1.0 / (row.home_lambda * row.away_lambda) for row in rows)
    if not lower < upper:
        raise ValueError("no common feasible rho interval for supplied rates")

    def objective(rho: float) -> float:
        total = 0.0
        for row in rows:
            h, a = row.home_goals, row.away_goals
            lh, la = row.home_lambda, row.away_lambda
            tau = 1.0
            if (h, a) == (0, 0):
                tau = 1.0 - lh * la * rho
            elif (h, a) == (0, 1):
                tau = 1.0 + lh * rho
            elif (h, a) == (1, 0):
                tau = 1.0 + la * rho
            elif (h, a) == (1, 1):
                tau = 1.0 - rho
            if tau <= 0 or not isfinite(tau):
                return float("inf")
            total -= (
                -lh + h * log(lh) - lgamma(h + 1)
                -la + a * log(la) - lgamma(a + 1)
                + log(tau)
            )
        return total

    # Golden-section minimization on the common mathematically feasible range.
    left, right = lower + tolerance, upper - tolerance
    if left >= right:
        raise ValueError("feasible rho interval is too narrow")
    ratio = (5**0.5 - 1.0) / 2.0
    x1 = right - ratio * (right - left)
    x2 = left + ratio * (right - left)
    f1, f2 = objective(x1), objective(x2)
    for _ in range(max_iterations):
        if right - left <= tolerance:
            break
        if f1 <= f2:
            right, x2, f2 = x2, x1, f1
            x1 = right - ratio * (right - left)
            f1 = objective(x1)
        else:
            left, x1, f1 = x1, x2, f2
            x2 = left + ratio * (right - left)
            f2 = objective(x2)
    rho = (left + right) / 2.0
    return DixonColesRhoEstimate(
        rho=rho,
        negative_log_likelihood=objective(rho),
        observations=len(rows),
        lower_bound=lower,
        upper_bound=upper,
    )


def estimate_rho_from_development_folds(
    results,
    folds,
    candidate,
    *,
    min_training_fixtures: int = 30,
) -> DixonColesRhoEstimate:
    """Build strictly out-of-fold rates, then estimate rho on development data."""
    from itertools import pairwise

    from app.models.hierarchical_poisson import fit_hierarchical_poisson

    rows = tuple(results)
    ordered_folds = tuple(sorted(folds, key=lambda fold: fold.train_cutoff))
    if not ordered_folds:
        raise ValueError("at least one chronological fold is required")
    if min_training_fixtures < 1:
        raise ValueError("min_training_fixtures must be positive")
    if len({row.fixture_id for row in rows}) != len(rows):
        raise ValueError("duplicate fixture IDs are not allowed")
    for previous, current in pairwise(ordered_folds):
        if current.train_cutoff < previous.validation_end:
            raise ValueError("chronological validation windows overlap")

    observations = []
    scored_fixture_ids = set()
    for fold in ordered_folds:
        training = tuple(row for row in rows if row.kickoff_at <= fold.train_cutoff)
        validation = tuple(
            row for row in rows
            if fold.train_cutoff < row.kickoff_at <= fold.validation_end
        )
        if len(training) < min_training_fixtures or not validation:
            continue
        model = fit_hierarchical_poisson(
            training,
            as_of=fold.train_cutoff,
            half_life_days=candidate.half_life_days,
            team_ridge=candidate.team_ridge,
            competition_ridge=candidate.competition_ridge,
        )
        for row in validation:
            if row.fixture_id in scored_fixture_ids:
                raise ValueError("a fixture appears in more than one validation fold")
            rates = model.predict(row.home_team_id, row.away_team_id, row.competition_id)
            observations.append(DixonColesObservation(
                row.home_goals, row.away_goals, rates.home_lambda, rates.away_lambda
            ))
            scored_fixture_ids.add(row.fixture_id)

    if len(observations) < 20:
        raise ValueError("development folds produced fewer than 20 out-of-fold forecasts")
    return estimate_dixon_coles_rho(observations)
