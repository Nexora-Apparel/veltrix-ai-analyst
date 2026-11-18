"""Offline contract tests based on the bounded 5Dollar endpoint probe.

The provider response itself is not embedded here: tests exercise the observed
field names and pagination envelope with synthetic values, without retaining
raw provider data or making network calls.
"""
import asyncio
from datetime import UTC, datetime

import httpx

from app.providers.five_dollar import FiveDollarFootballProvider


def observed_fixture_row(fixture_id: int) -> dict[str, object]:
    return {
        "id": fixture_id,
        "league": {"id": 522514093, "name": "Brazil Serie B", "season": "2026"},
        "teams": {
            "home": {"id": 101, "name": "Home Club"},
            "away": {"id": 202, "name": "Away Club"},
        },
        "kickoff_utc": "2026-11-08T22:15:00+00:00",
        "kickoff_ts": 1794176100,
        "status": "finished",
        "status_code": "FT",
        "status_reason": "Full Time",
        "goals": {"home": 1, "away": 0},
        "corners": {"home": 5, "away": 3},
        "cards": {
            "home": {"yellow": 2, "red": 0},
            "away": {"yellow": 1, "red": 0},
        },
    }


def test_observed_fixture_fields_and_pagination_are_normalized_offline() -> None:
    requests: list[httpx.Request] = []
    rows = [observed_fixture_row(3728617600 + index) for index in range(8)]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "success": 1,
                "data": rows,
                "pagination": {
                    "page": 1,
                    "per_page": 50,
                    "count": 8,
                    "has_more": False,
                },
            },
        )

    provider = FiveDollarFootballProvider(
        api_key="offline-test-key",
        transport=httpx.MockTransport(handler),
    )
    fixtures = asyncio.run(
        provider.fetch_fixtures(
            datetime(2026, 11, 7, tzinfo=UTC),
            datetime(2026, 11, 9, tzinfo=UTC),
            competition_ids=["522514093"],
        )
    )

    assert len(requests) == 1
    assert requests[0].url.path == "/v1/leagues/522514093/fixtures"
    assert requests[0].url.params["page"] == "1"
    assert requests[0].url.params["per_page"] == "50"
    assert requests[0].url.params["status"] == "all"
    assert requests[0].url.params["start_time"] == "1794009600"
    assert requests[0].url.params["end_time"] == "1794182400"
    assert len(fixtures) == 8

    first = fixtures[0]
    assert first.provenance.provider_record_id == "3728617600"
    assert first.competition_id == "522514093"
    assert first.competition_name == "Brazil Serie B"
    assert first.home_team_id == "101"
    assert first.away_team_id == "202"
    assert first.kickoff_at == datetime(2026, 11, 8, 22, 15, tzinfo=UTC)
    assert first.status == "finished"
    assert first.status_code == "FT"
    assert first.status_reason == "Full Time"
    assert (first.home_goals, first.away_goals) == (1, 0)
    assert (first.home_corners, first.away_corners) == (5, 3)
    assert (first.home_yellow_cards, first.away_yellow_cards) == (2, 1)
    assert (first.home_red_cards, first.away_red_cards) == (0, 0)


def test_observed_kickoff_timestamp_fallback_is_supported() -> None:
    row = observed_fixture_row(3728617699)
    row.pop("kickoff_utc")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "success": 1,
                "data": [row],
                "pagination": {
                    "page": 1,
                    "per_page": 50,
                    "count": 1,
                    "has_more": False,
                },
            },
        )

    provider = FiveDollarFootballProvider(
        api_key="offline-test-key",
        transport=httpx.MockTransport(handler),
    )
    fixtures = asyncio.run(
        provider.fetch_fixtures(
            datetime(2026, 11, 7, tzinfo=UTC),
            datetime(2026, 11, 9, tzinfo=UTC),
            competition_ids=["522514093"],
        )
    )

    assert len(fixtures) == 1
    assert fixtures[0].kickoff_at == datetime.fromtimestamp(1794176100, tz=UTC)
