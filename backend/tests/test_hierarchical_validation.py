from datetime import UTC, datetime, timedelta

import pytest

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)
from app.models.hierarchical_scoreline import forecast_hierarchical_fixture
from app.validation.hierarchical_tuning import (
    ChronologicalFold,
    select_hierarchical_hyperparameters,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def make_result(fid: str, day: int, home: str, away: str, hg: int, ag: int):
    return HierarchicalGoalResult(
        fixture_id=fid,
        kickoff_at=BASE + timedelta(days=day),
        competition_id="league-a",
        home_team_id=home,
        away_team_id=away,
        home_goals=hg,
        away_goals=ag,
    )


def fixture_history():
    teams = ("A", "B", "C", "D", "E", "F")
    return [
        make_result(
            str(day),
            day,
            teams[day % len(teams)],
            teams[(day + 1) % len(teams)],
            (day * 3) % 4,
            (day * 5) % 3,
        )
        for day in range(1, 41)
    ]


def test_optimizer_reports_convergence_and_finite_gradient():
    model = fit_hierarchical_poisson(fixture_history())
    assert model.optimizer_converged is True
    assert model.optimizer_iterations > 0
    assert model.optimizer_gradient_norm <= 1e-6
    assert model.training_fixtures == 40


@pytest.mark.parametrize(
    ("home", "away", "expected_counts"),
    [
        ("A", "UNSEEN", (12, 0)),
        ("UNSEEN-H", "UNSEEN-A", (0, 0)),
    ],
)
def test_sparse_team_forecasts_flow_through_dixon_coles(home, away, expected_counts):
    model = fit_hierarchical_poisson(fixture_history())
    forecast = forecast_hierarchical_fixture(model, home, away, "league-a", rho=0.0)
    assert (
        forecast.rates.home_team_history,
        forecast.rates.away_team_history,
    ) == expected_counts
    assert forecast.rates.home_lambda > 0
    assert forecast.rates.away_lambda > 0
    assert forecast.scoreline.probabilities
    markets = forecast.markets
    assert set(markets["1X2"]) == {"HOME", "DRAW", "AWAY"}
    assert sum(markets["1X2"].values()) == pytest.approx(1.0)
    assert sum(markets["BTTS"].values()) == pytest.approx(1.0)
    assert all(0.0 <= p <= 1.0 for market in markets.values() for p in market.values())


def test_competition_context_changes_unseen_team_goal_rates():
    model = fit_hierarchical_poisson(
        fixture_history()
        + [
            HierarchicalGoalResult(
                fixture_id="other",
                kickoff_at=BASE + timedelta(days=41),
                competition_id="league-b",
                home_team_id="X",
                away_team_id="Y",
                home_goals=0,
                away_goals=4,
            )
        ]
    )
    a = forecast_hierarchical_fixture(model, "NEW1", "NEW2", "league-a", rho=0.0)
    b = forecast_hierarchical_fixture(model, "NEW1", "NEW2", "league-b", rho=0.0)
    assert (a.rates.home_lambda, a.rates.away_lambda) != (
        b.rates.home_lambda,
        b.rates.away_lambda,
    )
    assert a.markets != b.markets


def test_chronological_tuner_only_scores_after_training_cutoff():
    rows = fixture_history()
    fold = ChronologicalFold(
        train_cutoff=BASE + timedelta(days=30),
        validation_end=BASE + timedelta(days=40),
    )
    availability = {
        row.fixture_id: row.kickoff_at + timedelta(hours=1)
        for row in rows
    }
    selected = select_hierarchical_hyperparameters(
        rows,
        [fold],
        label_available_at=availability,
        evaluation_as_of=BASE + timedelta(days=50),
        half_lives=(90.0, 180.0),
        team_ridges=(0.5, 2.0),
        competition_ridges=(1.0,),
        min_training_fixtures=20,
    )
    assert selected.protocol == "EXPANDING_WINDOW_LABEL_AVAILABILITY_AWARE_PAIRED_POISSON_NLL_V2"
    assert selected.leaderboard
    assert selected.leaderboard[0].scored_matches == 10
    assert selected.selected == selected.leaderboard[0].candidate


def test_chronological_tuner_rejects_overlapping_validation_windows():
    rows = fixture_history()
    folds = [
        ChronologicalFold(BASE + timedelta(days=20), BASE + timedelta(days=35)),
        ChronologicalFold(BASE + timedelta(days=30), BASE + timedelta(days=40)),
    ]
    with pytest.raises(ValueError, match="overlap"):
        select_hierarchical_hyperparameters(rows, folds)
