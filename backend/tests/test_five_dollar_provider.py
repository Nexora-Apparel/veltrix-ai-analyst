import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.providers.five_dollar import (
    FiveDollarFootballProvider,
    ProviderConfigurationError,
    ProviderLeagueMovedError,
    ProviderRateLimitError,
)


def fixture_row(fixture_id: int, kickoff: str) -> dict[str, object]:
    return {
        "id": fixture_id,
        "league": {"id": 77, "name": "Brazil Serie B", "season": "2026"},
        "teams": {
            "home": {"id": 1001, "name": "Home FC"},
            "away": {"id": 1002, "name": "Away FC"},
        },
        "kickoff_utc": kickoff,
        "status": "finished",
        "goals": {"home": 2, "away": 1},
        "corners": {"home": 6, "away": 3},
        "cards": {
            "home": {"yellow": 2, "red": 0},
            "away": {"yellow": 1, "red": 1},
        },
    }


def response_payload(rows: list[dict[str, object]], has_more: bool = False) -> dict[str, object]:
    return {
        "success": 1,
        "data": rows,
        "pagination": {"page": 1, "per_page": 100, "count": len(rows), "has_more": has_more},
    }


def test_missing_api_key_fails_before_network_request() -> None:
    provider = FiveDollarFootballProvider(api_key="")

    with pytest.raises(ProviderConfigurationError):
        asyncio.run(
            provider.fetch_fixtures(
                datetime(2026, 11, 16, tzinfo=UTC),
                datetime(2026, 11, 17, tzinfo=UTC),
            )
        )


def test_fetch_fixtures_normalizes_scores_stats_and_pagination() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = int(request.url.params["page"])
        if page == 1:
            return httpx.Response(
                200,
                json=response_payload(
                    [fixture_row(501, "2026-11-16T10:00:00+00:00")],
                    has_more=True,
                ),
            )
        return httpx.Response(
            200,
            json=response_payload(
                [fixture_row(502, "2026-11-16T11:00:00+00:00")]
            ),
        )

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    results = asyncio.run(
        provider.fetch_fixtures(
            datetime(2026, 11, 16, tzinfo=UTC),
            datetime(2026, 11, 16, 12, tzinfo=UTC),
            competition_ids=["77"],
        )
    )

    assert len(results) == 2
    assert len(requests) == 2
    assert all(request.url.path == "/v1/leagues/77/fixtures" for request in requests)
    assert requests[0].headers["authorization"] == "Bearer test-key"
    assert results[0].provenance.provider == "5DollarFootballAPI"
    assert results[0].provenance.provider_record_id == "501"
    assert results[0].competition_name == "Brazil Serie B"
    assert results[0].home_goals == 2
    assert results[0].away_goals == 1
    assert results[0].home_corners == 6
    assert results[0].away_red_cards == 1
    assert results[0].status == "finished"


def test_fetch_fixtures_splits_windows_at_24_hours() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=response_payload([]))

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    start = datetime(2026, 11, 16, tzinfo=UTC)
    results = asyncio.run(
        provider.fetch_fixtures(start, start + timedelta(hours=25))
    )

    assert results == []
    assert len(requests) == 2
    durations = [
        int(request.url.params["end_time"]) - int(request.url.params["start_time"])
        for request in requests
    ]
    assert durations == [24 * 60 * 60, 60 * 60]


def test_rate_limit_exposes_retry_after_without_retrying() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(429, headers={"Retry-After": "30"})

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderRateLimitError) as error:
        asyncio.run(
            provider.fetch_fixtures(
                datetime(2026, 11, 16, tzinfo=UTC),
                datetime(2026, 11, 16, 12, tzinfo=UTC),
            )
        )

    assert error.value.retry_after_seconds == 30
    assert requests == 1


def test_retired_league_id_reports_canonical_replacement() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            301,
            json={
                "success": 0,
                "error": {"code": "league_moved", "canonical_id": 88},
            },
        )

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderLeagueMovedError) as error:
        asyncio.run(
            provider.fetch_fixtures(
                datetime(2026, 11, 16, tzinfo=UTC),
                datetime(2026, 11, 16, 12, tzinfo=UTC),
                competition_ids=["77"],
            )
        )

    assert error.value.canonical_competition_id == "88"



def test_fetch_competitions_normalizes_country_and_season_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "success": 1,
                "data": [
                    {
                        "id": 9001,
                        "name": "Brazil Serie B",
                        "country": {"code": "BR", "name": "Brazil"},
                        "is_popular": False,
                        "has_standings": True,
                        "last_fixture_utc": "2026-11-15T22:00:00+00:00",
                        "seasons": [
                            {"season": "2026", "current": True},
                            {"season": "2025", "current": False},
                        ],
                    }
                ],
                "pagination": {"page": 1, "per_page": 100, "has_more": False},
            },
        )

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    competitions = asyncio.run(provider.fetch_competitions(country_code="BR"))

    assert len(competitions) == 1
    assert requests[0].url.path == "/v1/leagues"
    assert requests[0].url.params["country"] == "BR"
    assert requests[0].url.params["include"] == "seasons"
    assert competitions[0].competition_id == "9001"
    assert competitions[0].name == "Brazil Serie B"
    assert competitions[0].country_code == "BR"
    assert competitions[0].seasons == ("2026", "2025")


def test_account_status_returns_plan_and_quota_metadata() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "success": 1,
                "data": {
                    "plan": "community",
                    "limits": {
                        "rate_limit": 300,
                        "rate_window_seconds": 3600,
                        "burst_per_minute": 20,
                    },
                    "usage": {"today": 17},
                },
            },
        )

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    status = asyncio.run(provider.fetch_account_status())

    assert requests[0].url.path == "/v1/status"
    assert status["plan"] == "community"
    assert status["limits"]["rate_limit"] == 300
    assert status["limits"]["burst_per_minute"] == 20
    assert status["usage"]["today"] == 17
