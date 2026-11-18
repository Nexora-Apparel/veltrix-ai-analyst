from datetime import UTC, datetime, timedelta

import pytest

from app.models.attack_defence import GoalResult, fit_attack_defence

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def row(fid, day, home, away, hg, ag):
    return GoalResult(fid, BASE + timedelta(days=day), home, away, hg, ag)


def test_fit_returns_positive_rates_and_team_effects_are_centered():
    results = [
        row("1", 1, "A", "B", 3, 0),
        row("2", 2, "A", "C", 2, 0),
        row("3", 3, "B", "C", 0, 1),
        row("4", 4, "C", "A", 0, 2),
        row("5", 5, "B", "A", 1, 2),
        row("6", 6, "C", "B", 0, 2),
    ]
    model = fit_attack_defence(results)
    rates = model.predict("A", "B")
    assert rates.home_lambda > 0
    assert rates.away_lambda > 0
    assert sum(model.attack.values()) == pytest.approx(0.0, abs=1e-9)
    assert sum(model.defence.values()) == pytest.approx(0.0, abs=1e-9)
    assert model.training_fixtures == 6


def test_recency_weighting_is_configurable():
    results = [
        row("old1", 1, "A", "B", 0, 3),
        row("old2", 2, "B", "A", 0, 3),
        row("new1", 180, "A", "B", 3, 0),
        row("new2", 181, "B", "A", 3, 0),
    ]
    recent = fit_attack_defence(results, half_life_days=30)
    broad = fit_attack_defence(results, half_life_days=10000)
    assert recent.predict("A", "B").home_lambda > broad.predict("A", "B").home_lambda


def test_rejects_future_results_and_duplicate_ids():
    with pytest.raises(ValueError, match="after as_of"):
        fit_attack_defence([row("x", 2, "A", "B", 1, 0)], as_of=BASE + timedelta(days=1))
    repeated = row("x", 1, "A", "B", 1, 0)
    with pytest.raises(ValueError, match="duplicate"):
        fit_attack_defence([repeated, repeated])


def test_unseen_teams_use_neutral_effects_without_fabricated_team_strength():
    from math import exp

    model = fit_attack_defence([row("x", 1, "A", "B", 1, 0)])

    one_unseen = model.predict("A", "C")
    both_unseen = model.predict("C", "D")

    assert one_unseen.home_lambda > 0
    assert one_unseen.away_lambda > 0
    assert both_unseen.home_lambda == pytest.approx(
        exp(model.intercept + model.home_advantage)
    )
    assert both_unseen.away_lambda == pytest.approx(exp(model.intercept))


def test_stronger_ridge_penalty_shrinks_team_effects():
    teams = ("A", "B", "C", "D")
    rows = [
        row(
            f"ridge-{day}",
            day + 1,
            teams[day % 4],
            teams[(day + 1) % 4],
            3 if day % 5 == 0 else day % 2,
            0 if day % 4 else 2,
        )
        for day in range(40)
    ]
    weak = fit_attack_defence(rows, ridge=0.001, max_iterations=2500)
    strong = fit_attack_defence(rows, ridge=20.0, max_iterations=2500)
    weak_effect = sum(abs(v) for v in weak.attack.values()) + sum(
        abs(v) for v in weak.defence.values()
    )
    strong_effect = sum(abs(v) for v in strong.attack.values()) + sum(
        abs(v) for v in strong.defence.values()
    )
    assert strong_effect < weak_effect
