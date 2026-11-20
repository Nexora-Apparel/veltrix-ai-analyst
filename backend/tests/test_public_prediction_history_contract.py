from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.contracts.public_prediction import (
    PublicPredictionHistoryItem,
    PublicPredictionMarkets,
)


def _history_payload() -> dict:
    return {
        "prediction_id": UUID("00000000-0000-0000-0000-000000000001"),
        "fixture": {
            "fixture_id": UUID("00000000-0000-0000-0000-000000000002"),
            "competition": "Premier League",
            "home_team": "Home FC",
            "away_team": "Away FC",
            "kickoff_at": datetime(2026, 11, 19, 18, 0, tzinfo=UTC),
        },
        "markets": {
            "one_x_two": {"HOME": 0.48, "DRAW": 0.27, "AWAY": 0.25},
            "btts": {"YES": 0.54, "NO": 0.46},
            "over_under_1_5": {"OVER": 0.78, "UNDER": 0.22},
            "over_under_2_5": {"OVER": 0.51, "UNDER": 0.49},
            "over_under_3_5": {"OVER": 0.29, "UNDER": 0.71},
        },
        "expected_home_goals": 1.4,
        "expected_away_goals": 1.1,
        "generated_at": datetime(2026, 11, 19, 17, 0, tzinfo=UTC),
        "published_at": datetime(2026, 11, 19, 17, 5, tzinfo=UTC),
        "publication_status": "PUBLISHED",
        "settlement_status": "SETTLED",
        "final_score": {"home_goals": 2, "away_goals": 1},
        "settled_at": datetime(2026, 11, 19, 20, 10, tzinfo=UTC),
    }


def test_public_history_contract_exposes_verified_final_score():
    item = PublicPredictionHistoryItem(**_history_payload())

    assert item.settlement_status == "SETTLED"
    assert item.final_score is not None
    assert item.final_score.home_goals == 2
    assert item.final_score.away_goals == 1
    assert item.markets.one_x_two["HOME"] == 0.48


def test_public_history_contract_allows_pending_result_without_score():
    payload = _history_payload()
    payload["settlement_status"] = "PENDING_RESULT"
    payload["final_score"] = None
    payload["settled_at"] = None

    item = PublicPredictionHistoryItem(**payload)

    assert item.settlement_status == "PENDING_RESULT"
    assert item.final_score is None


def test_public_history_contract_rejects_score_without_settlement_time():
    payload = _history_payload()
    payload["settled_at"] = None

    with pytest.raises(ValidationError):
        PublicPredictionHistoryItem(**payload)


def test_public_history_contract_rejects_unsettled_status_with_score():
    payload = _history_payload()
    payload["settlement_status"] = "PENDING_RESULT"

    with pytest.raises(ValidationError):
        PublicPredictionHistoryItem(**payload)
