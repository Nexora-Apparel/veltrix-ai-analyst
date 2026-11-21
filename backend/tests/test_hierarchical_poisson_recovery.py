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
    attack_truth = {
        f"team-{index:03d}": (0.50 if index < 10 else -0.50 if index >= 126 else 0.0)
        for index in range(team_count)
    }
    defence_truth = {
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
        home_rate = 1.40 * exp(0.18 + attack_truth[home] - defence_truth[away])
        away_rate = 1.40 * exp(attack_truth[away] - defence_truth[home])
        results.append(HierarchicalGoalResult(
            fixture_id=f"synthetic-{index:04d}",
            kickoff_at=kickoff,
            competition_id="synthetic-league",
            home_team_id=home,
            away_team_id=away,
            home_goals=_poisson(home_rate, rng),
            away_goals=_poisson(away_rate, rng),
        ))
    return results, strong, weak, attack_truth, defence_truth


def _fit(
    results,
    team_ridge: float,
    competition_ridge: float,
    *,
    max_iterations: int = 4000,
):
    return fit_hierarchical_poisson(
        results,
        as_of=datetime(2026, 11, 21, tzinfo=UTC),
        half_life_days=365.0,
        team_ridge=team_ridge,
        competition_ridge=competition_ridge,
        max_iterations=max_iterations,
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


def _median_truth_retention(model, attack_truth, defence_truth) -> float:
    ratios = []
    for team in model.attack:
        if abs(attack_truth[team]) > 0.05:
            ratios.append(abs(model.attack[team] / attack_truth[team]))
        if abs(defence_truth[team]) > 0.05:
            ratios.append(abs(model.defence[team] / defence_truth[team]))
    return median(ratios)


def test_current_quarantined_configuration_is_rejected_by_recovery_and_shrinkage(
    known_strength_results,
):
    results, strong, weak, attack_truth, defence_truth = known_strength_results
    current = _fit(results, team_ridge=0.5, competition_ridge=0.5)

    # Synthetic truth has a 1.6 log-strength gap and a 1.78 strong-home contrast.
    assert not _recovery_passes(current, strong, weak)
    assert _median_truth_retention(current, attack_truth, defence_truth) < 0.50


def test_absurdly_large_prior_is_rejected_by_recovery_negative_control(
    known_strength_results,
):
    results, strong, weak, _, _ = known_strength_results
    try:
        excessive_prior = _fit(
            results,
            team_ridge=1_000_000.0,
            competition_ridge=1_000_000.0,
            max_iterations=100,
        )
    except (ArithmeticError, ValueError):
        # A numerical failure is a fail-closed rejection of the negative control.
        return

    assert not _recovery_passes(excessive_prior, strong, weak)


@pytest.fixture(scope="module")
def abundant_strength_results():
    rng = random.Random(20261122)
    team_count = 16
    strong = {f"team-{index:03d}" for index in range(3)}
    weak = {f"team-{index:03d}" for index in range(13, 16)}
    attack_truth = {
        f"team-{index:03d}": (0.45 if index < 3 else -0.45 if index >= 13 else 0.0)
        for index in range(team_count)
    }
    defence_truth = {
        f"team-{index:03d}": (-0.25 if index < 3 else 0.25 if index >= 13 else 0.0)
        for index in range(team_count)
    }
    base = datetime(2025, 11, 22, tzinfo=UTC)
    results = []
    for index in range(1000):
        home_index = index % team_count
        away_index = (index * 5 + 1) % team_count
        home = f"team-{home_index:03d}"
        away = f"team-{away_index:03d}"
        kickoff = base + timedelta(days=index // 3)
        home_rate = 1.40 * exp(0.18 + attack_truth[home] - defence_truth[away])
        away_rate = 1.40 * exp(attack_truth[away] - defence_truth[home])
        results.append(HierarchicalGoalResult(
            fixture_id=f"abundant-{index:04d}",
            kickoff_at=kickoff,
            competition_id="synthetic-league",
            home_team_id=home,
            away_team_id=away,
            home_goals=_poisson(home_rate, rng),
            away_goals=_poisson(away_rate, rng),
        ))
    return results, strong, weak, attack_truth, defence_truth


@pytest.fixture(scope="module")
def candidate_and_unpenalized_reference(abundant_strength_results):
    from app.models.hierarchical_poisson_v2 import fit_hierarchical_poisson_v2

    results, *_ = abundant_strength_results
    as_of = datetime(2026, 11, 21, tzinfo=UTC)
    candidate = fit_hierarchical_poisson_v2(
        results,
        as_of=as_of,
        half_life_days=365.0,
        k_team=2.0,
        k_competition=2.0,
        k_home_competition=2.0,
        k_home_global=10.0,
    )
    reference = fit_hierarchical_poisson(
        results,
        as_of=as_of,
        half_life_days=365.0,
        team_ridge=1e-9,
        competition_ridge=1e-9,
    )
    return candidate, reference


def test_pseudo_match_candidate_recovers_strength_and_matches_unpenalized_fit(
    abundant_strength_results, candidate_and_unpenalized_reference
):
    _, strong, weak, attack_truth, defence_truth = abundant_strength_results
    candidate, reference = candidate_and_unpenalized_reference

    group_gap = mean(
        candidate.attack[("synthetic-league", team)]
        - candidate.defence[("synthetic-league", team)]
        for team in strong
    ) - mean(
        candidate.attack[("synthetic-league", team)]
        - candidate.defence[("synthetic-league", team)]
        for team in weak
    )
    rates = candidate.predict("team-000", "team-015", "synthetic-league")
    match_contrast = log(rates.home_lambda / rates.away_lambda)
    retention = median([
        abs(candidate.attack[("synthetic-league", team)] / attack_truth[team])
        for team in attack_truth if abs(attack_truth[team]) > 0.05
    ] + [
        abs(candidate.defence[("synthetic-league", team)] / defence_truth[team])
        for team in defence_truth if abs(defence_truth[team]) > 0.05
    ])
    attack_reference_ratios = [
        abs(candidate.attack[team] / reference.attack[team[1]])
        for team in candidate.attack
        if abs(reference.attack[team[1]]) > 0.05
    ]
    defence_reference_ratios = [
        abs(candidate.defence[team] / reference.defence[team[1]])
        for team in candidate.defence
        if abs(reference.defence[team[1]]) > 0.05
    ]

    assert group_gap >= 0.70
    assert match_contrast >= 0.70
    assert retention >= 0.50
    assert median(attack_reference_ratios) >= 0.90
    assert median(defence_reference_ratios) >= 0.90
    assert candidate.optimizer_converged


def test_candidate_abstains_for_unseen_competition_scoped_team(
    candidate_and_unpenalized_reference
):
    candidate, _ = candidate_and_unpenalized_reference
    with pytest.raises(ValueError, match="TEAM_HISTORY_INSUFFICIENT"):
        candidate.predict("newly-promoted-no-history", "team-015", "synthetic-league")
