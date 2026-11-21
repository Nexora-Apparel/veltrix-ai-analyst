from datetime import UTC, datetime, timedelta

import pytest

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    _solve_linear_system,
    fit_hierarchical_poisson,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _rows():
    fixtures = [
        ("a", 1, "L1", "A", "B", 2, 0),
        ("b", 2, "L1", "B", "C", 1, 1),
        ("c", 3, "L1", "C", "A", 0, 2),
        ("d", 4, "L1", "A", "C", 3, 1),
        ("e", 1, "L2", "D", "E", 1, 0),
        ("f", 2, "L2", "E", "F", 0, 2),
        ("g", 3, "L2", "F", "D", 1, 1),
        ("h", 4, "L2", "D", "F", 2, 2),
    ]
    return [
        HierarchicalGoalResult(
            fixture_id=fid,
            kickoff_at=BASE + timedelta(days=day),
            competition_id=competition,
            home_team_id=home,
            away_team_id=away,
            home_goals=hg,
            away_goals=ag,
        )
        for fid, day, competition, home, away, hg, ag in fixtures
    ]


def test_newton_matches_existing_gradient_descent_predictions():
    rows = _rows()
    kwargs = {
        "as_of": BASE + timedelta(days=5),
        "half_life_days": 365,
        "team_ridge": 0.5,
        "competition_ridge": 0.5,
    }
    reference = fit_hierarchical_poisson(
        rows, optimizer="gradient_descent", max_iterations=12000, **kwargs
    )
    candidate = fit_hierarchical_poisson(
        rows, optimizer="newton", max_iterations=200, **kwargs
    )
    assert candidate.optimizer_converged
    assert candidate.optimizer_iterations <= 200
    assert candidate.optimizer_gradient_norm <= 1e-7
    for home, away, competition in (
        ("A", "B", "L1"),
        ("D", "F", "L2"),
        ("A", "NEW", "L1"),
    ):
        expected = reference.predict(home, away, competition)
        actual = candidate.predict(home, away, competition)
        assert actual.home_lambda == pytest.approx(expected.home_lambda, rel=2e-4)
        assert actual.away_lambda == pytest.approx(expected.away_lambda, rel=2e-4)


def test_newton_matches_lbfgs_on_converged_small_case():
    rows = _rows()
    kwargs = {
        "as_of": BASE + timedelta(days=5),
        "half_life_days": 365,
        "team_ridge": 0.5,
        "competition_ridge": 0.5,
    }
    reference = fit_hierarchical_poisson(
        rows, optimizer="lbfgs", max_iterations=4000, **kwargs
    )
    candidate = fit_hierarchical_poisson(
        rows, optimizer="newton", max_iterations=200, **kwargs
    )
    assert reference.optimizer_converged
    assert candidate.optimizer_converged
    for home, away, competition in (("A", "C", "L1"), ("E", "D", "L2")):
        expected = reference.predict(home, away, competition)
        actual = candidate.predict(home, away, competition)
        assert actual.home_lambda == pytest.approx(expected.home_lambda, rel=2e-4)
        assert actual.away_lambda == pytest.approx(expected.away_lambda, rel=2e-4)


def test_newton_linear_solver_uses_partial_pivoting():
    assert _solve_linear_system([[0.0, 2.0], [1.0, 1.0]], [4.0, 3.0]) == pytest.approx([1.0, 2.0])


def test_newton_linear_solver_rejects_singular_system():
    with pytest.raises(ArithmeticError, match="singular"):
        _solve_linear_system([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0])


def test_newton_reports_non_convergence_without_relaxing_tolerance():
    with pytest.raises(ArithmeticError, match="did not converge"):
        fit_hierarchical_poisson(
            _rows(),
            as_of=BASE + timedelta(days=5),
            optimizer="newton",
            max_iterations=1,
            tolerance=1e-14,
        )
