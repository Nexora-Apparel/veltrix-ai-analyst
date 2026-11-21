from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from math import exp, log
from statistics import mean, median

import pytest

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)


def _poisson(rate: float, rng: random.Random) -> int:
    threshold = exp(-rate)
    product = 1.0
    count = 0
    while product > threshold:
        count += 1
        product *= rng.random()
    return count - 1


@pytest.fixture(scope="module")
def known_strength_results():
    rng = random.Random(20261121)
    team_count = 136
    strong = {f"team-{index:03d}" for index in range(10)}
    weak = {f"team-{index:03d}" for index in range(126, 136)}
    attack = {
        f"team-{index:03d}": (0.50 if index < 10 else -0.50 if index >= 126 else 0.0)
        for index in range(team_count)
    }
    defence = {
        f"team-{index:03d}": (-0.30 if index < 10 else 0.30 if index >= 126 else 0.0)
        for index in range(team_count)
    }
    base = datetime(2025, 11, 22, tzinfo=UTC)
    results = []
    for index in range(1000):
        home_index = index % team_count
        away_index = (index * 37 + 1) % team_count
        home = f"team-{home_index:03d}"
        away = f"team-{away_index:03d}"
        kickoff = base + timedelta(days=index // 3)
        home_rate = 1.40 * exp(0.18 + attack[home] - defence[away])
        away_rate = 1.40 * exp(attack[away] - defence[home])
        results.append(HierarchicalGoalResult(
            fixture_id=f"synthetic-{index:04d}",
            kickoff_at=kickoff,
            competition_id="synthetic-league",
            home_team_id=home,
            away_team_id=away,
            home_goals=_poisson(home_rate, rng),
            away_goals=_poisson(away_rate, rng),
        ))
    return results, strong, weak


def _fit(results, team_ridge: float, competition_ridge: float):
    return fit_hierarchical_poisson(
        results,
        as_of=datetime(2026, 11, 21, tzinfo=UTC),
        half_life_days=365.0,
        team_ridge=team_ridge,
        competition_ridge=competition_ridge,
    )


def _recovery_metrics(model, strong: set[str], weak: set[str]):
    group_gap = mean(
        model.attack[team] - model.defence[team] for team in strong
    ) - mean(
        model.attack[team] - model.defence[team] for team in weak
    )
    rates = model.predict("team-000", "team-135", "synthetic-league")
    match_contrast = log(rates.home_lambda / rates.away_lambda)
    return group_gap, match_contrast


def _recovery_passes(model, strong: set[str], weak: set[str]) -> bool:
    group_gap, match_contrast = _recovery_metrics(model, strong, weak)
    return group_gap >= 0.70 and match_contrast >= 0.70


def _median_effect_retention(fitted, reference) -> float:
    ratios = []
    for team in fitted.attack:
        if abs(reference.attack[team]) > 0.05:
            ratios.append(abs(fitted.attack[team] / reference.attack[team]))
        if abs(reference.defence[team]) > 0.05:
            ratios.append(abs(fitted.defence[team] / reference.defence[team]))
    return median(ratios)


def test_current_quarantined_configuration_is_rejected_by_recovery_and_shrinkage(
    known_strength_results,
):
    results, strong, weak = known_strength_results
    current = _fit(results, team_ridge=0.5, competition_ridge=0.5)
    near_unpenalized = _fit(results, team_ridge=1e-9, competition_ridge=1e-9)

    # The reference fit must recover the deliberately strong/weak synthetic signal.
    assert _recovery_passes(near_unpenalized, strong, weak)

    # These are explicit admission-gate rejections, not CI failures.
    assert not _recovery_passes(current, strong, weak)
    assert _median_effect_retention(current, near_unpenalized) < 0.50


def test_absurdly_large_prior_is_rejected_by_recovery_negative_control(
    known_strength_results,
):
    results, strong, weak = known_strength_results
    try:
        excessive_prior = _fit(
            results, team_ridge=1_000_000.0, competition_ridge=1_000_000.0
        )
    except (ArithmeticError, ValueError):
        # A numerical failure is also a valid fail-closed rejection.
        return

    assert not _recovery_passes(excessive_prior, strong, weak)
