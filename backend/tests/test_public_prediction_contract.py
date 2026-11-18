from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.contracts.public_prediction import (
    PublicPrediction,
    PublicPredictionMarkets,
)


def make_markets() -> dict[str, dict[str, float]]:
    return {
        "one_x_two": {"HOME": 0.48, "DRAW": 0.27, "AWAY": 0.25},
        "btts": {"YES": 0.54, "NO": 0.46},
        "over_under_1_5": {"OVER": 0.78, "UNDER": 0.22},
        "over_under_2_5": {"OVER": 0.51, "UNDER": 0.49},
        "over_under_3_5": {"OVER": 0.29, "UNDER": 0.71},
    }


def test_public_contract_contains_all_requested_markets_without_diagnostics() -> None:
    prediction = PublicPrediction(
        prediction_id=UUID("00000000-0000-0000-0000-000000000001"),
        fixture={
            "fixture_id": "00000000-0000-0000-0000-000000000002",
            "competition": "Premier League",
            "home_team": "Home FC",
            "away_team": "Away FC",
            "kickoff_at": datetime(2026, 11, 19, 18, 0, tzinfo=UTC),
        },
        markets=make_markets(),
        expected_home_goals=1.45,
        expected_away_goals=1.08,
    )
    payload = prediction.model_dump()
    assert set(payload["markets"]) == {
        "one_x_two", "btts", "over_under_1_5", "over_under_2_5", "over_under_3_5"
    }
    assert "system_report" not in payload
    assert "model_report" not in payload
    assert "notes" not in payload


def test_public_market_contract_rejects_incomplete_or_unbalanced_probabilities() -> None:
    markets = make_markets()
    markets["over_under_3_5"] = {"OVER": 0.7, "UNDER": 0.7}
    with pytest.raises(ValidationError):
        PublicPredictionMarkets(**markets)


def test_public_prediction_rejects_extra_internal_fields() -> None:
    payload = {
        "prediction_id": "00000000-0000-0000-0000-000000000001",
        "fixture": {
            "fixture_id": "00000000-0000-0000-0000-000000000002",
            "competition": "Premier League",
            "home_team": "Home FC",
            "away_team": "Away FC",
            "kickoff_at": datetime(2026, 11, 19, 18, 0, tzinfo=UTC),
        },
        "markets": make_markets(),
        "system_report": "must never be exposed",
    }
    with pytest.raises(ValidationError):
        PublicPrediction(**payload)
