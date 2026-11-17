from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.elo import EloConfig, EloSystem, HistoricalResult
from app.models.scoreline import build_scoreline_distribution


def result(fixture_id: str, home: str, away: str, hg: int, ag: int, day: int = 1) -> HistoricalResult:
    return HistoricalResult(
        fixture_id=fixture_id,
        kickoff_at=datetime(2026, 1, day, 15, 0, tzinfo=UTC),
        home_team_id=home,
        away_team_id=away,
        home_goals=hg,
        away_goals=ag,
    )


def test_elo_winner_rating_increases_and_loser_decreases() -> None:
    system = EloSystem(EloConfig(home_advantage=0))
    system.update(result("f1", "A", "B", 2, 0))
    assert system.rating("A").rating > 1500
    assert system.rating("B").rating < 1500
    assert system.rating("A").matches_played == 1


def test_elo_batch_uses_pre_batch_ratings_and_is_order_invariant() -> None:
    fixtures = [result("f1", "A", "B", 2, 0), result("f2", "C", "D", 0, 1)]
    left = EloSystem()
    right = EloSystem()
    left.update_batch(fixtures)
    right.update_batch(reversed(fixtures))
    assert {team: left.rating(team).rating for team in "ABCD"} == {
        team: right.rating(team).rating for team in "ABCD"
    }


def test_elo_rejects_same_team_in_simultaneous_fixtures() -> None:
    system = EloSystem()
    with pytest.raises(ValueError, match="multiple simultaneous fixtures"):
        system.update_batch([result("f1", "A", "B", 1, 0), result("f2", "A", "C", 0, 1)])


def test_elo_chronological_fit_groups_same_kickoff() -> None:
    rows = [result("f2", "C", "D", 0, 1), result("f1", "A", "B", 2, 0)]
    system = EloSystem.fit_chronologically(rows)
    assert system.rating("A").matches_played == 1
    assert system.rating("D").matches_played == 1


def test_poisson_markets_are_coherent_and_normalized() -> None:
    distribution = build_scoreline_distribution(1.45, 1.05, rho=0.0, max_goals=15)
    assert sum(sum(row) for row in distribution.probabilities) == pytest.approx(1.0)
    markets = distribution.market_probabilities()
    assert sum(markets["1X2"].values()) == pytest.approx(1.0)
    assert sum(markets["BTTS"].values()) == pytest.approx(1.0)
    assert sum(markets["TOTALS_2_5"].values()) == pytest.approx(1.0)
    assert 0 <= markets["1X2"]["HOME"] <= 1


def test_dixon_coles_adjustment_changes_low_scores_without_negative_cells() -> None:
    independent = build_scoreline_distribution(1.4, 1.1, rho=0.0, max_goals=15)
    corrected = build_scoreline_distribution(1.4, 1.1, rho=-0.08, max_goals=15)
    assert corrected.rho == pytest.approx(-0.08)
    assert corrected.probabilities[0][0] != pytest.approx(independent.probabilities[0][0])
    assert all(value >= 0 for row in corrected.probabilities for value in row)
    assert sum(sum(row) for row in corrected.probabilities) == pytest.approx(1.0)


def test_dixon_coles_rho_is_clamped_to_nonnegative_correction_region() -> None:
    distribution = build_scoreline_distribution(2.0, 2.0, rho=5.0, max_goals=15)
    assert distribution.rho == pytest.approx(0.25)
    assert all(value >= 0 for row in distribution.probabilities for value in row)


def test_scoreline_rejects_invalid_rates_and_goal_cap() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        build_scoreline_distribution(0.0, 1.0)
    with pytest.raises(ValueError, match="at least 2"):
        build_scoreline_distribution(1.0, 1.0, max_goals=1)
