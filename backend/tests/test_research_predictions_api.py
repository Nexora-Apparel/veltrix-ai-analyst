from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.routes.research_predictions import _research_prediction


def test_research_mapper_preserves_markets_and_stable_nonpublication_identity() -> None:
    fixture_id = UUID("00000000-0000-0000-0000-000000000002")
    row = {
        "run_key": "a" * 64,
        "generated_at": datetime(2026, 11, 21, 6, 0, tzinfo=UTC),
        "training_fixture_count": 996,
        "model_version": "hierarchical-poisson-shadow-v1",
        "forecast": {
            "canonical_fixture_id": str(fixture_id),
            "markets": {
                "1X2": {"HOME": 0.5, "DRAW": 0.25, "AWAY": 0.25},
                "BTTS": {"YES": 0.6, "NO": 0.4},
                "TOTALS_1_5": {"OVER": 0.7, "UNDER": 0.3},
                "TOTALS_2_5": {"OVER": 0.5, "UNDER": 0.5},
                "TOTALS_3_5": {"OVER": 0.2, "UNDER": 0.8},
            },
            "expected_home_goals": 1.4,
            "expected_away_goals": 1.1,
            "publication_status": "NOT_PUBLISHED",
            "value_betting_status": "LOCKED",
        },
        "canonical_fixture_id": fixture_id,
        "competition": "Premier League",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "kickoff_at": datetime(2026, 11, 21, 18, 0, tzinfo=UTC),
    }

    first = _research_prediction(row)
    second = _research_prediction(row)

    assert first == second
    assert first["fixture"]["fixture_id"] == str(fixture_id)
    assert first["markets"]["one_x_two"]["HOME"] == 0.5
    assert first["markets"]["btts"]["YES"] == 0.6
    assert first["markets"]["over_under_1_5"]["OVER"] == 0.7
    assert first["expected_home_goals"] == 1.4
    assert first["prediction_id"]



def test_research_api_keeps_daily_report_available_through_next_matchday() -> None:
    from app.routes.research_predictions import _RESEARCH_QUERY

    assert "INTERVAL '36 hours'" in _RESEARCH_QUERY
    assert "INTERVAL '6 hours'" not in _RESEARCH_QUERY
