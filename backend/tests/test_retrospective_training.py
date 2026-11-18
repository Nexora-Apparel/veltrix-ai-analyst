from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.models.chronology_adjudication import (
    apply_kickoff_adjudications,
    load_kickoff_adjudications,
)
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

def test_overall_team_attack_informs_predictions_at_the_other_venue() -> None:
    model = HistoricalRateModel()
    target = row("target", 10, "A", "E", 0, 0)
    strong_away = [
        row("a1", 1, "A", "B", 4, 0),
        row("a2", 2, "C", "D", 1, 1),
        row("a3", 3, "D", "B", 1, 1),
        row("a4", 4, "C", "E", 1, 1),
    ]
    neutral_away = [
        row("a1", 1, "A", "B", 0, 0),
        *strong_away[1:],
    ]
    strong_rate, _ = model.rates(strong_away, target)
    neutral_rate, _ = model.rates(neutral_away, target)
    assert strong_rate > neutral_rate


def test_official_kickoff_adjudication_changes_research_time_and_preserves_raw_evidence():
    registry = Path(__file__).resolve().parents[1] / "data/research/official_kickoff_adjudications.json"
    adjudications = load_kickoff_adjudications(registry)
    raw = datetime.fromisoformat("2026-09-10T23:49:59+00:00")
    fixture = ResearchFixture("2179333578", raw, "SB", "LON", 1, 2)

    corrected, audit = apply_kickoff_adjudications([fixture], adjudications)

    assert corrected[0].kickoff_at == datetime.fromisoformat("2026-09-10T22:30:00+00:00")
    assert fixture.kickoff_at == raw  # immutable original object / provider timestamp
    assert audit[0]["raw_provider_kickoff_at"] == raw.isoformat()
    assert audit[0]["cbf_match_reference"] == "262"


def test_official_kickoff_adjudication_fails_closed_on_raw_timestamp_mismatch():
    adjudications = {
        "2179333578": {
            "raw_provider_kickoff_at": "2026-09-10T23:49:59+00:00",
            "official_kickoff_at": "2026-09-10T22:30:00+00:00",
            "source_url": "https://example.invalid/cbf",
            "reason": "test",
        }
    }
    fixture = ResearchFixture(
        "2179333578", datetime.fromisoformat("2026-09-10T23:50:00+00:00"), "SB", "LON", 1, 2
    )
    with pytest.raises(ValueError, match="raw timestamp mismatch"):
        apply_kickoff_adjudications([fixture], adjudications)


def test_official_kickoff_adjudication_restores_simultaneous_cbf_batch():
    registry = Path(__file__).resolve().parents[1] / "data/research/official_kickoff_adjudications.json"
    adjudications = load_kickoff_adjudications(registry)
    official = datetime.fromisoformat("2026-09-10T22:30:00+00:00")
    fixtures = [
        ResearchFixture("3196722470", official, "VIL", "GOI", 2, 0),
        ResearchFixture(
            "2179333578", datetime.fromisoformat("2026-09-10T23:49:59+00:00"), "SB", "LON", 1, 2
        ),
    ]
    corrected, audit = apply_kickoff_adjudications(fixtures, adjudications)
    report = chronological_research_run(corrected)

    assert len(audit) == 1
    assert {row["kickoff_at"] for row in report["predictions"]} == {official.isoformat()}
    assert len(report["predictions"]) == 2
