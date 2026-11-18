from __future__ import annotations

import pytest

from app.validation.dixon_coles import (
    DixonColesObservation,
    estimate_dixon_coles_rho,
)


def test_rho_estimator_uses_out_of_fold_observations_and_returns_feasible_value():
    rows = []
    outcomes = ((0, 0), (0, 1), (1, 0), (1, 1), (2, 1), (1, 2))
    for index in range(60):
        home_goals, away_goals = outcomes[index % len(outcomes)]
        rows.append(DixonColesObservation(home_goals, away_goals, 1.35, 1.05))

    estimate = estimate_dixon_coles_rho(rows)
    assert estimate.observations == 60
    assert estimate.lower_bound < estimate.rho < estimate.upper_bound
    assert estimate.negative_log_likelihood > 0
    assert estimate.protocol == "OOF_DIXON_COLES_PROFILE_NLL_V1"


def test_rho_estimator_requires_minimum_out_of_fold_sample():
    rows = [DixonColesObservation(1, 0, 1.2, 0.9)] * 19
    with pytest.raises(ValueError, match="at least 20"):
        estimate_dixon_coles_rho(rows)


def test_rho_observation_rejects_invalid_rates():
    with pytest.raises(ValueError, match="positive and finite"):
        DixonColesObservation(0, 0, 0.0, 1.0)
