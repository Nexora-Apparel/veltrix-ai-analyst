from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.validation.prospective_dataset import (
    ProspectiveDatasetRow,
    build_expanding_window_folds,
)
from app.validation.prospective_model_evaluation import evaluate_prospective_model


def _synthetic_rows(count: int = 120) -> list[ProspectiveDatasetRow]:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    for index in range(count):
        kickoff = start + timedelta(days=index)
        home = f"team-{index % 6}"
        away = f"team-{(index + 1) % 6}"
        home_goals = (index % 3)
        away_goals = ((index + 1) % 2)
        rows.append(ProspectiveDatasetRow(
            fixture_id=f"league:fixture-{index}",
            provider="5DollarFootballAPI",
            source_id="5dollarfootballapi",
            competition_id="league",
            kickoff_at=kickoff,
            prediction_cutoff_at=kickoff - timedelta(hours=2),
            home_team_id=home,
            away_team_id=away,
            features={},
            feature_lineage=(),
            label={
                "home_goals": home_goals,
                "away_goals": away_goals,
                "home_win": home_goals > away_goals,
                "draw": home_goals == away_goals,
                "away_win": home_goals < away_goals,
                "btts": home_goals > 0 and away_goals > 0,
                "over_25": home_goals + away_goals > 2.5,
            },
            label_observed_at=kickoff + timedelta(hours=3),
            label_observation_id=index + 1,
            label_lineage={"provider_response_id": index + 1001},
        ))
    return rows


def test_prospective_evaluator_scores_1x2_btts_and_totals_with_confidence_intervals():
    rows = _synthetic_rows()
    folds = build_expanding_window_folds(
        rows,
        minimum_training_fixtures=30,
        validation_block_fixtures=25,
    )
    report = evaluate_prospective_model(
        rows,
        folds,
        bootstrap_replicates=200,
        seed=11,
    )
    assert report["status"] == "RESEARCH_ONLY_NOT_PRODUCTION_APPROVAL"
    assert report["fixtures"] > 0
    assert set(report["markets"]) == {"1X2", "BTTS", "OVER_UNDER_2_5"}
    assert "paired_delta_model_minus_baseline" in report["markets"]["BTTS"]
    assert "per_competition" in report["markets"]["OVER_UNDER_2_5"]
    assert report["production_promotion"] == "LOCKED"
    assert report["value_betting"] == "LOCKED"


def test_prospective_evaluator_fails_closed_without_chronological_folds():
    report = evaluate_prospective_model(
        _synthetic_rows(20),
        (),
        bootstrap_replicates=200,
    )
    assert report["status"] == "INSUFFICIENT_PROSPECTIVE_DATA"
    assert report["fixtures"] == 0
    assert report["release_eligible"] is False
