from datetime import UTC, datetime, timedelta

from app.validation.retrospective_features import (
    HistoricalFixture,
    build_retrospective_lagged_features,
)


def _fixture(
    fixture_id: str,
    day: int,
    home: str,
    away: str,
    home_goals: int,
    away_goals: int,
    *,
    competition: str = "league-a",
    home_corners: int | None = 4,
    away_corners: int | None = 3,
) -> HistoricalFixture:
    return HistoricalFixture(
        fixture_id=fixture_id,
        competition_id=competition,
        kickoff_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day),
        home_team_id=home,
        away_team_id=away,
        home_goals=home_goals,
        away_goals=away_goals,
        home_corners=home_corners,
        away_corners=away_corners,
        home_yellow_cards=1,
        away_yellow_cards=2,
        home_red_cards=0,
        away_red_cards=0,
    )


def test_features_use_only_strictly_earlier_same_competition_fixtures():
    rows = [
        _fixture("m1", 1, "A", "B", 2, 0, home_corners=8, away_corners=2),
        _fixture("m2", 2, "C", "A", 1, 3, home_corners=5, away_corners=7),
        _fixture("target", 3, "A", "D", 99, 0),
        # Same kickoff as target: must not leak into target features.
        _fixture("simultaneous", 3, "A", "E", 0, 99),
        # Another competition must not enter A's history.
        _fixture("other-league", 2, "A", "F", 50, 0, competition="league-b"),
    ]

    result = {row["fixture_id"]: row for row in build_retrospective_lagged_features(rows)}
    target = result["target"]

    assert target["features"]["home_prior_match_count"] == 2
    assert target["features"]["home_goals_for_mean"] == 2.5
    assert target["features"]["home_goals_against_mean"] == 0.5
    assert target["features"]["home_corners_for_mean"] == 7.5
    assert target["features"]["away_prior_match_count"] == 0
    assert "simultaneous" not in target["feature_provenance"]["history_fixture_ids"]
    assert "other-league" not in target["feature_provenance"]["history_fixture_ids"]
    assert target["validation_eligible"] is False
    assert target["feature_provenance"]["point_in_time_certifiable"] is False


def test_missing_supporting_features_remain_missing_not_imputed():
    rows = [
        _fixture("m1", 1, "A", "B", 1, 0, home_corners=None, away_corners=None),
        _fixture("target", 2, "A", "C", 0, 0),
    ]

    target = build_retrospective_lagged_features(rows)[1]
    assert target["features"]["home_prior_match_count"] == 1
    assert target["features"]["home_corners_for_mean"] is None
    assert target["features"]["home_corners_against_mean"] is None


def test_duplicate_fixture_ids_and_naive_timestamps_are_rejected():
    duplicate = _fixture("same", 1, "A", "B", 1, 0)
    import pytest

    with pytest.raises(ValueError, match="duplicate fixture"):
        build_retrospective_lagged_features([duplicate, duplicate])

    naive = HistoricalFixture(
        fixture_id="naive",
        competition_id="league-a",
        kickoff_at=datetime(2026, 1, 1),
        home_team_id="A",
        away_team_id="B",
        home_goals=0,
        away_goals=0,
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        build_retrospective_lagged_features([naive])
