from datetime import UTC, datetime, timedelta

import pytest

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def result(fid, day, competition, home, away, hg, ag):
    return HierarchicalGoalResult(
        fixture_id=fid,
        kickoff_at=BASE + timedelta(days=day),
        competition_id=competition,
        home_team_id=home,
        away_team_id=away,
        home_goals=hg,
        away_goals=ag,
    )


def sample_results():
    return [
        result("1", 1, "league-a", "A", "B", 2, 0),
        result("2", 2, "league-a", "B", "C", 1, 1),
        result("3", 3, "league-a", "C", "A", 0, 2),
        result("4", 1, "league-b", "D", "E", 1, 0),
        result("5", 2, "league-b", "E", "F", 0, 2),
        result("6", 3, "league-b", "F", "D", 1, 1),
    ]


def test_model_fits_competition_and_team_effects_from_observed_results():
    model = fit_hierarchical_poisson(sample_results())
    assert model.training_fixtures == 6
    assert model.competition_match_counts == {"league-a": 3, "league-b": 3}
    assert model.team_match_counts["A"] == 2
    assert model.home_advantage != 0.12


def test_one_unseen_team_uses_observed_competition_baseline():
    model = fit_hierarchical_poisson(sample_results())
    rates = model.predict("A", "NEW", "league-a")
    assert rates.home_lambda > 0
    assert rates.away_lambda > 0
    assert rates.competition_seen is True
    assert rates.home_team_history == 2
    assert rates.away_team_history == 0
    assert rates.calculation_mode == "ONE_SIDED_TEAM_HISTORY"


def test_both_unseen_teams_use_competition_context_not_fixed_probabilities():
    model = fit_hierarchical_poisson(sample_results())
    rates = model.predict("NEW-A", "NEW-B", "league-a")
    other_competition = model.predict("NEW-A", "NEW-B", "league-b")
    assert rates.home_lambda > 0
    assert rates.away_lambda > 0
    assert rates.competition_seen is True
    assert rates.calculation_mode == "COMPETITION_ONLY"
    assert (rates.home_lambda, rates.away_lambda) != (
        other_competition.home_lambda,
        other_competition.away_lambda,
    )


def test_unknown_competition_falls_back_to_observed_global_goal_rate():
    model = fit_hierarchical_poisson(sample_results())
    rates = model.predict("NEW-A", "NEW-B", "new-league")
    assert rates.competition_seen is False
    assert rates.home_lambda > 0
    assert rates.away_lambda > 0
    assert rates.calculation_mode == "GLOBAL_CONTEXT_ONLY"


def test_sparse_team_history_is_retained_and_reported():
    rows = sample_results() + [
        result("7", 4, "league-a", "NEW", "A", 1, 0),
    ]
    model = fit_hierarchical_poisson(rows)
    rates = model.predict("NEW", "B", "league-a")
    assert rates.home_team_history == 1
    assert rates.away_team_history == 2
    assert rates.calculation_mode == "TEAM_AND_COMPETITION_HISTORY"


def test_fit_rejects_future_rows_and_duplicate_fixtures():
    with pytest.raises(ValueError, match="after as_of"):
        fit_hierarchical_poisson(
            [result("future", 2, "league-a", "A", "B", 1, 0)],
            as_of=BASE + timedelta(days=1),
        )
    repeated = result("duplicate", 1, "league-a", "A", "B", 1, 0)
    with pytest.raises(ValueError, match="duplicate"):
        fit_hierarchical_poisson([repeated, repeated])


def test_no_positive_goal_signal_is_not_replaced_with_a_fabricated_rate():
    rows = [result("zero", 1, "league-a", "A", "B", 0, 0)]
    with pytest.raises(ValueError, match="positive weighted goal signal"):
        fit_hierarchical_poisson(rows)



def test_known_team_with_unseen_competition_uses_global_context_and_reports_mode():
    model = fit_hierarchical_poisson(sample_results())
    rates = model.predict("A", "NEW", "unseen-league")

    assert rates.competition_seen is False
    assert rates.home_team_history == 2
    assert rates.away_team_history == 0
    assert rates.home_lambda > 0
    assert rates.away_lambda > 0
    assert rates.calculation_mode == "TEAM_HISTORY_GLOBAL_CONTEXT"


def test_no_team_or_competition_history_is_explicit_global_context_only():
    model = fit_hierarchical_poisson(sample_results())
    rates = model.predict("UNKNOWN-HOME", "UNKNOWN-AWAY", "unknown-league")

    assert rates.home_team_history == 0
    assert rates.away_team_history == 0
    assert rates.competition_seen is False
    assert rates.calculation_mode == "GLOBAL_CONTEXT_ONLY"
