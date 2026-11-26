from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.routes.public_predictions import (
    _public_prediction,
    _public_prediction_history_item,
)


def test_public_prediction_mapper_returns_only_fixture_and_market_data() -> None:
    prediction_id = UUID("00000000-0000-0000-0000-000000000001")
    fixture_id = UUID("00000000-0000-0000-0000-000000000002")
    fixture = {
        "prediction_id": prediction_id,
        "canonical_fixture_id": fixture_id,
        "competition": "Premier League",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "kickoff_at": datetime(2026, 11, 19, 18, 0, tzinfo=UTC),
        "expected_home_goals": 1.4,
        "expected_away_goals": 1.1,
    }
    market_rows = [
        {"market": "1X2", "outcome": "HOME", "probability": 0.48},
        {"market": "1X2", "outcome": "DRAW", "probability": 0.27},
        {"market": "1X2", "outcome": "AWAY", "probability": 0.25},
        {"market": "BTTS", "outcome": "YES", "probability": 0.54},
        {"market": "BTTS", "outcome": "NO", "probability": 0.46},
        {"market": "TOTALS_1_5", "outcome": "OVER", "probability": 0.78},
        {"market": "TOTALS_1_5", "outcome": "UNDER", "probability": 0.22},
        {"market": "TOTALS_2_5", "outcome": "OVER", "probability": 0.51},
        {"market": "TOTALS_2_5", "outcome": "UNDER", "probability": 0.49},
        {"market": "TOTALS_3_5", "outcome": "OVER", "probability": 0.29},
        {"market": "TOTALS_3_5", "outcome": "UNDER", "probability": 0.71},
    ]

    result = _public_prediction(fixture, market_rows)
    payload = result.model_dump()

    assert payload["prediction_id"] == prediction_id
    assert payload["fixture"]["fixture_id"] == fixture_id
    assert payload["markets"]["one_x_two"]["HOME"] == 0.48
    assert payload["markets"]["btts"]["YES"] == 0.54
    assert payload["markets"]["over_under_1_5"]["OVER"] == 0.78
    assert payload["markets"]["over_under_2_5"]["OVER"] == 0.51
    assert payload["markets"]["over_under_3_5"]["UNDER"] == 0.71
    assert "notes" not in payload
    assert "system_report" not in payload
    assert "model_report" not in payload


def test_public_prediction_mapper_rejects_incomplete_market_data() -> None:
    fixture = {
        "prediction_id": UUID("00000000-0000-0000-0000-000000000001"),
        "canonical_fixture_id": UUID("00000000-0000-0000-0000-000000000002"),
        "competition": "Premier League",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "kickoff_at": datetime(2026, 11, 19, 18, 0, tzinfo=UTC),
        "expected_home_goals": 1.4,
        "expected_away_goals": 1.1,
    }
    with pytest.raises(ValidationError):
        _public_prediction(fixture, [])


def test_public_history_mapper_includes_only_supplied_verified_settlement() -> None:
    prediction_id = UUID("00000000-0000-0000-0000-000000000011")
    fixture_id = UUID("00000000-0000-0000-0000-000000000012")
    fixture = {
        "prediction_id": prediction_id,
        "canonical_fixture_id": fixture_id,
        "competition": "Premier League",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "kickoff_at": datetime(2026, 11, 19, 18, 0, tzinfo=UTC),
        "expected_home_goals": 1.4,
        "expected_away_goals": 1.1,
        "generated_at": datetime(2026, 11, 19, 17, 0, tzinfo=UTC),
        "published_at": datetime(2026, 11, 19, 17, 5, tzinfo=UTC),
        "publication_status": "PUBLISHED",
        "settled_home_goals": 2,
        "settled_away_goals": 1,
        "settled_at": datetime(2026, 11, 19, 20, 10, tzinfo=UTC),
    }
    markets = [
        {"market": "1X2", "outcome": "HOME", "probability": 0.48},
        {"market": "1X2", "outcome": "DRAW", "probability": 0.27},
        {"market": "1X2", "outcome": "AWAY", "probability": 0.25},
        {"market": "BTTS", "outcome": "YES", "probability": 0.54},
        {"market": "BTTS", "outcome": "NO", "probability": 0.46},
        {"market": "TOTALS_1_5", "outcome": "OVER", "probability": 0.78},
        {"market": "TOTALS_1_5", "outcome": "UNDER", "probability": 0.22},
        {"market": "TOTALS_2_5", "outcome": "OVER", "probability": 0.51},
        {"market": "TOTALS_2_5", "outcome": "UNDER", "probability": 0.49},
        {"market": "TOTALS_3_5", "outcome": "OVER", "probability": 0.29},
        {"market": "TOTALS_3_5", "outcome": "UNDER", "probability": 0.71},
    ]

    result = _public_prediction_history_item(fixture, markets)

    assert result.prediction_id == prediction_id
    assert result.settlement_status == "SETTLED"
    assert result.final_score is not None
    assert result.final_score.home_goals == 2
    assert result.final_score.away_goals == 1
    assert result.published_at == fixture["published_at"]


def test_public_history_mapper_keeps_unsettled_results_pending() -> None:
    fixture = {
        "prediction_id": UUID("00000000-0000-0000-0000-000000000021"),
        "canonical_fixture_id": UUID("00000000-0000-0000-0000-000000000022"),
        "competition": "Premier League",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "kickoff_at": datetime(2026, 11, 19, 18, 0, tzinfo=UTC),
        "expected_home_goals": 1.4,
        "expected_away_goals": 1.1,
        "generated_at": datetime(2026, 11, 19, 17, 0, tzinfo=UTC),
        "published_at": datetime(2026, 11, 19, 17, 5, tzinfo=UTC),
        "publication_status": "PUBLISHED",
        "settled_home_goals": None,
        "settled_away_goals": None,
        "settled_at": None,
    }
    markets = [
        {"market": "1X2", "outcome": "HOME", "probability": 0.48},
        {"market": "1X2", "outcome": "DRAW", "probability": 0.27},
        {"market": "1X2", "outcome": "AWAY", "probability": 0.25},
        {"market": "BTTS", "outcome": "YES", "probability": 0.54},
        {"market": "BTTS", "outcome": "NO", "probability": 0.46},
        {"market": "TOTALS_1_5", "outcome": "OVER", "probability": 0.78},
        {"market": "TOTALS_1_5", "outcome": "UNDER", "probability": 0.22},
        {"market": "TOTALS_2_5", "outcome": "OVER", "probability": 0.51},
        {"market": "TOTALS_2_5", "outcome": "UNDER", "probability": 0.49},
        {"market": "TOTALS_3_5", "outcome": "OVER", "probability": 0.29},
        {"market": "TOTALS_3_5", "outcome": "UNDER", "probability": 0.71},
    ]

    result = _public_prediction_history_item(fixture, markets)

    assert result.settlement_status == "PENDING_RESULT"
    assert result.final_score is None
    assert result.settled_at is None



def test_published_daily_feed_uses_wat_calendar_bounds():
    from app.routes import public_predictions

    assert "fixture.kickoff_at >= %s" in public_predictions._FIXTURE_QUERY + """
        WHERE fixture.kickoff_at >= %s AND fixture.kickoff_at < %s
    """
    assert "fixture.kickoff_at < %s" in public_predictions._FIXTURE_QUERY + """
        WHERE fixture.kickoff_at >= %s AND fixture.kickoff_at < %s
    """
