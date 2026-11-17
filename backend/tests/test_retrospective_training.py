from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
    assert system.rating("A").rating == pytest.approx(1500.0)
    assert system.rating("B").rating == pytest.approx(1500.0)
    assert system.rating("A").matches_played == 1


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
    assert report["rho_used_for_prequential_predictions"] == 0.0
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
