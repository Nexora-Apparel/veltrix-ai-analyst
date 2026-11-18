from datetime import UTC, datetime

import pytest

from app.providers.the_odds_api_markets import (
    OddsApiMarketPayloadError,
    normalize_event_h2h_odds_response,
)


RETRIEVED = datetime(2026, 11, 18, 2, 30, tzinfo=UTC)
EVENT = {
    "event_id": "event-1",
    "sport_key": "soccer_epl",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "commence_time": "2026-11-20T19:00:00Z",
}
FIXTURE = {
    "provider_fixture_id": "fixture-1",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "kickoff_at": "2026-11-20T19:02:00+00:00",
}


def payload(**overrides):
    result = {
        "id": "event-1",
        "sport_key": "soccer_epl",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "commence_time": "2026-11-20T19:00:00Z",
        "bookmakers": [
            {
                "key": "book-a",
                "title": "Book A",
                "last_update": "2026-11-18T02:29:00Z",
                "markets": [
                    {
                        "key": "h2h",
                        "last_update": "2026-11-18T02:29:00Z",
                        "outcomes": [
                            {"name": "Arsenal", "price": 1.8},
                            {"name": "Draw", "price": 3.5},
                            {"name": "Chelsea", "price": 4.2},
                        ],
                    }
                ],
            }
        ],
    }
    result.update(overrides)
    return result


def normalize(response=None, *, expected=EVENT, fixture=FIXTURE, retrieved=RETRIEVED):
    return normalize_event_h2h_odds_response(
        payload() if response is None else response,
        expected_event=expected,
        canonical_fixture=fixture,
        retrieved_at=retrieved,
    )


def test_normalizes_three_timestamped_h2h_selections():
    result = normalize()
    assert result["quote_count"] == 3
    assert result["bookmaker_count"] == 1
    assert {quote["selection"] for quote in result["timestamped_quotes"]} == {
        "HOME", "DRAW", "AWAY"
    }
    assert all(quote["source_tick_at"] == "2026-11-18T02:29:00+00:00" for quote in result["timestamped_quotes"])


def test_rejects_event_or_sport_identity_mismatch():
    with pytest.raises(OddsApiMarketPayloadError, match="EVENT_ID_MISMATCH"):
        normalize(payload(id="other-event"))
    with pytest.raises(OddsApiMarketPayloadError, match="SPORT_KEY_MISMATCH"):
        normalize(payload(sport_key="soccer_spain_la_liga"))


def test_rejects_reversed_team_or_kickoff_mismatch():
    with pytest.raises(OddsApiMarketPayloadError, match="HOME_TEAM_MISMATCH"):
        normalize(payload(home_team="Chelsea"))
    with pytest.raises(OddsApiMarketPayloadError, match="CANONICAL_FIXTURE"):
        normalize(
            payload(),
            fixture={**FIXTURE, "kickoff_at": "2026-11-20T19:30:00Z"},
        )


def test_skips_quotes_without_timestamps_and_invalid_prices():
    response = payload()
    response["bookmakers"].append({
        "key": "book-b",
        "title": "Book B",
        "markets": [{"key": "h2h", "outcomes": [{"name": "Arsenal", "price": 2.0}]}],
    })
    response["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = float("nan")
    result = normalize(response)
    assert result["quote_count"] == 0
    assert result["rejected_missing_timestamp_count"] == 1
    assert result["rejected_invalid_quote_count"] == 1
    assert result["rejected_incomplete_bookmaker_count"] == 1


def test_rejects_future_tick_naive_retrieval_and_past_kickoff():
    response = payload()
    response["bookmakers"][0]["markets"][0]["last_update"] = "2026-11-18T02:31:00Z"
    result = normalize(response)
    assert result["quote_count"] == 0
    assert result["rejected_invalid_quote_count"] == 1
    with pytest.raises(OddsApiMarketPayloadError, match="TIMEZONE_AWARE"):
        normalize(retrieved=datetime(2026, 11, 18, 2, 30))
    with pytest.raises(OddsApiMarketPayloadError, match="KICKOFF_PASSED"):
        normalize(retrieved=datetime(2026, 11, 21, tzinfo=UTC))
