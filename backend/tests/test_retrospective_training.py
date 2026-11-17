from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models.elo import EloSystem, HistoricalResult
from app.models.retrospective import (
    HistoricalRateModel,
    ResearchFixture,
    chronological_research_run,
)


def row(fid: str, day: int, home: str, away: str, hg: int, ag: int) -> ResearchFixture:
    return ResearchFixture(
        fid, datetime(2026, 1, day, 15, tzinfo=UTC), home, away, hg, ag
    )


def test_elo_draw_updates_both_ratings_without_unbound_delta() -> None:
    system = EloSystem()
    system.update(HistoricalResult(
        "draw", datetime(2026, 1, 1, tzinfo=UTC), "A", "B", 1, 1
    ))
    # Home advantage makes a draw a small negative surprise for the home team.
    home = system.rating("A")
    away = system.rating("B")
    assert home.rating < 1500.0
    assert away.rating > 1500.0
    assert home.rating + away.rating == pytest.approx(3000.0)
    assert home.matches_played == away.matches_played == 1


def test_historical_rate_model_rejects_same_or_future_kickoff() -> None:
    history = [row("old", 1, "A", "B", 2, 0)]
    target = row("same", 1, "C", "D", 0, 0)
    with pytest.raises(ValueError, match="strictly earlier"):
        HistoricalRateModel().rates(history, target)


def test_prequential_run_emits_three_model_scorecards_and_excludes_no_rows() -> None:
    fixtures = [
        row("1", 1, "A", "B", 2, 0),
        row("2", 2, "C", "D", 0, 0),
        row("3", 3, "B", "C", 1, 2),
        row("4", 4, "D", "A", 1, 1),
        row("5", 5, "A", "C", 3, 1),
        row("6", 6, "B", "D", 0, 1),
    ]
    report = chronological_research_run(fixtures)
    assert report["dataset_type"] == "RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED"
    assert report["fixture_count"] == 6
    for model in ("elo", "poisson", "ensemble"):
        assert report[model]["matches"] == 6.0
        assert 0 <= report[model]["brier"] <= 2
        assert report[model]["log_loss"] > 0
    assert report["rho_used_for_prequential_predictions"] == "updated_from_prior_results_only"
    assert len(report["predictions"]) == 6


def test_simultaneous_fixtures_are_scored_before_either_result_updates_state() -> None:
    fixtures = [
        ResearchFixture("a", datetime(2026, 1, 1, 15, tzinfo=UTC), "A", "B", 3, 0),
        ResearchFixture("b", datetime(2026, 1, 1, 15, tzinfo=UTC), "C", "D", 0, 3),
        ResearchFixture("c", datetime(2026, 1, 2, 15, tzinfo=UTC), "A", "C", 1, 0),
    ]
    report = chronological_research_run(fixtures)
    predictions = report["predictions"]
    assert predictions[0]["elo_1x2"] == predictions[1]["elo_1x2"] or (
        predictions[0]["elo_1x2"][1] == predictions[1]["elo_1x2"][1]
    )
    assert predictions[2]["elo_1x2"] != predictions[0]["elo_1x2"]


def test_duplicate_fixture_ids_are_rejected() -> None:
    fixture = row("same", 1, "A", "B", 1, 0)
    with pytest.raises(ValueError, match="duplicate fixture IDs"):
        chronological_research_run([fixture, fixture])


def test_dixon_coles_rho_fit_handles_simultaneous_kickoff_batches() -> None:
    from app.models.retrospective import fit_dixon_coles_rho

    fixtures = [
        row("1", 1, "A", "B", 0, 0),
        row("2", 1, "C", "D", 1, 1),
        row("3", 2, "A", "C", 2, 1),
        row("4", 3, "B", "D", 0, 1),
        row("5", 4, "A", "D", 1, 0),
        row("6", 5, "B", "C", 1, 1),
    ] * 6
    fixtures = [
        ResearchFixture(
            f"{item.fixture_id}-{index}",
            item.kickoff_at,
            item.home_team_id,
            item.away_team_id,
            item.home_goals,
            item.away_goals,
        )
        for index, item in enumerate(fixtures)
    ]
    rho = fit_dixon_coles_rho(fixtures)
    assert -0.18 <= rho <= 0.18

def test_ensemble_weight_tuning_uses_prior_prequential_predictions() -> None:
    from datetime import timedelta

    teams = ("A", "B", "C", "D")
    fixtures = [
        ResearchFixture(
            f"tune-{index}",
            datetime(2026, 1, 1, 15, tzinfo=UTC) + timedelta(days=index),
            teams[index % 4],
            teams[(index + 1) % 4],
            2 if index % 5 in (0, 1) else 0,
            1 if index % 3 == 0 else 0,
        )
        for index in range(65)
    ]
    report = chronological_research_run(fixtures)
    assert report["ensemble_weight_selection"] == (
        "PRIOR_PREQUENTIAL_PREDICTIONS_ONLY_WITH_BASELINE_SHRINKAGE"
    )
    assert 0.0 <= report["ensemble_elo_weight_min"] <= 1.0
    assert 0.0 <= report["ensemble_elo_weight_mean"] <= 1.0
    assert 0.0 <= report["ensemble_elo_weight_max"] <= 1.0
    assert report["ensemble_elo_weight_min"] <= report["ensemble_elo_weight_max"]
