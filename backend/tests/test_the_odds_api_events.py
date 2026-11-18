from datetime import UTC, datetime

import pytest

from app.providers.the_odds_api_events import (
    OddsApiEventPayloadError,
    normalize_event_catalogue,
)


AS_OF = datetime(2026, 11, 18, 0, tzinfo=UTC)


def event(**overrides):
    row = {
        "id": "event-1",
        "sport_key": "soccer_epl",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "commence_time": "2026-11-19T15:00:00Z",
    }
    row.update(overrides)
    return row


def test_normalizes_future_event_without_odds_fields():
    rows = normalize_event_catalogue([event()], requested_sport_key="soccer_epl", as_of=AS_OF)
    assert rows == ({
        "event_id": "event-1",
        "sport_key": "soccer_epl",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "commence_time": "2026-11-19T15:00:00+00:00",
    },)


def test_excludes_live_or_past_events():
    rows = normalize_event_catalogue(
        [event(commence_time="2026-11-17T23:59:00Z")],
        requested_sport_key="soccer_epl",
        as_of=AS_OF,
    )
    assert rows == ()


def test_rejects_wrong_sport_key():
    with pytest.raises(OddsApiEventPayloadError, match="sport_key"):
        normalize_event_catalogue(
            [event(sport_key="soccer_laliga")],
            requested_sport_key="soccer_epl",
            as_of=AS_OF,
        )


def test_rejects_duplicate_event_ids():
    with pytest.raises(OddsApiEventPayloadError, match="duplicate"):
        normalize_event_catalogue(
            [event(), event(home_team="Other FC")],
            requested_sport_key="soccer_epl",
            as_of=AS_OF,
        )


def test_rejects_naive_as_of_and_naive_kickoff():
    with pytest.raises(OddsApiEventPayloadError, match="as_of"):
        normalize_event_catalogue(
            [event()], requested_sport_key="soccer_epl",
            as_of=datetime(2026, 11, 18),
        )
    with pytest.raises(OddsApiEventPayloadError, match="timezone-aware"):
        normalize_event_catalogue(
            [event(commence_time="2026-11-19T15:00:00")],
            requested_sport_key="soccer_epl",
            as_of=AS_OF,
        )


def test_rejects_missing_fields_and_same_teams():
    with pytest.raises(OddsApiEventPayloadError, match="required"):
        normalize_event_catalogue(
            [{"id": "event-1"}], requested_sport_key="soccer_epl", as_of=AS_OF
        )
    with pytest.raises(OddsApiEventPayloadError, match="must differ"):
        normalize_event_catalogue(
            [event(away_team="Home FC")],
            requested_sport_key="soccer_epl",
            as_of=AS_OF,
        )
