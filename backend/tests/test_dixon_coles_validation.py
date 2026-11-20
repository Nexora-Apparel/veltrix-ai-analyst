from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models.hierarchical_poisson import HierarchicalGoalResult
from app.validation.dixon_coles import (
    DixonColesObservation,
    estimate_dixon_coles_rho,
    estimate_rho_from_development_folds,
)
from app.validation.hierarchical_tuning import ChronologicalFold, HierarchicalCandidate


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



def _chronological_goal_results():
    origin = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    availability = {}
    for index in range(100):
        fixture_id = f"fixture-{index}"
        kickoff = origin + timedelta(days=index)
        rows.append(HierarchicalGoalResult(
            fixture_id=fixture_id,
            kickoff_at=kickoff,
            competition_id=f"league-{index % 2}",
            home_team_id=f"team-{index % 10}",
            away_team_id=f"team-{(index + 3) % 10}",
            home_goals=index % 4,
            away_goals=(index + 1) % 3,
        ))
        availability[fixture_id] = (
            origin + timedelta(days=70)
            if index <= 20
            else kickoff + timedelta(hours=1)
        )
    return origin, rows, availability


def test_rho_oof_folds_enforce_label_availability_and_report_strict_protocol():
    origin, rows, availability = _chronological_goal_results()
    fold = ChronologicalFold(
        train_cutoff=origin + timedelta(days=60),
        validation_end=origin + timedelta(days=100),
    )
    candidate = HierarchicalCandidate(
        half_life_days=180.0,
        team_ridge=0.5,
        competition_ridge=1.0,
    )

    estimate = estimate_rho_from_development_folds(
        rows,
        (fold,),
        candidate,
        min_training_fixtures=30,
        label_available_at=availability,
        evaluation_as_of=origin + timedelta(days=110),
    )

    assert estimate.observations == 39
    assert estimate.protocol == (
        "OOF_DIXON_COLES_PROFILE_NLL_LABEL_AVAILABILITY_AWARE_V2"
    )


def test_rho_oof_does_not_count_delayed_labels_as_fold_training_data():
    origin, rows, availability = _chronological_goal_results()
    fold = ChronologicalFold(
        train_cutoff=origin + timedelta(days=60),
        validation_end=origin + timedelta(days=100),
    )
    candidate = HierarchicalCandidate(
        half_life_days=180.0,
        team_ridge=0.5,
        competition_ridge=1.0,
    )

    with pytest.raises(ValueError, match="fewer than 20 out-of-fold forecasts"):
        estimate_rho_from_development_folds(
            rows,
            (fold,),
            candidate,
            min_training_fixtures=45,
            label_available_at=availability,
            evaluation_as_of=origin + timedelta(days=110),
        )
