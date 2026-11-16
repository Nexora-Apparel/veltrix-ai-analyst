import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.providers.five_dollar import (
    FiveDollarFootballProvider,
    ProviderAPIError,
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



def test_malformed_score_is_rejected_instead_of_silently_truncated() -> None:
    row = fixture_row(503, "2026-11-16T10:00:00+00:00")
    row["goals"] = {"home": 1.5, "away": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_payload([row]))

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderAPIError):
        asyncio.run(
            provider.fetch_fixtures(
                datetime(2026, 11, 16, tzinfo=UTC),
                datetime(2026, 11, 16, 12, tzinfo=UTC),
                competition_ids=["77"],
            )
        )



def test_unknown_fixture_never_exposes_partial_goals_as_final_score() -> None:
    row = fixture_row(504, "2026-11-16T10:00:00+00:00")
    row["status"] = "unknown"
    row["status_reason"] = "result_unconfirmed"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_payload([row]))

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

    assert results[0].status == "unknown"
    assert results[0].status_reason == "result_unconfirmed"
    assert results[0].home_goals is None
    assert results[0].away_goals is None


def test_finished_fixture_without_both_scores_is_downgraded_to_unknown() -> None:
    row = fixture_row(505, "2026-11-16T10:00:00+00:00")
    row["goals"] = {"home": None, "away": None}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_payload([row]))

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

    assert results[0].status == "unknown"
    assert results[0].home_goals is None
    assert results[0].away_goals is None



@pytest.mark.parametrize("status_code", [401, 403, 500])
def test_auth_permission_and_server_failures_stop_without_retry(status_code: int) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(status_code, json={"success": 0, "error": "stop"})

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderAPIError, match=f"HTTP {status_code}"):
        asyncio.run(
            provider.fetch_fixtures(
                datetime(2026, 11, 16, tzinfo=UTC),
                datetime(2026, 11, 16, 12, tzinfo=UTC),
                competition_ids=["522514093"],
            )
        )

    assert requests == 1



def test_historical_fetch_requires_request_reserver_before_network() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json=response_payload([]))

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(
        ProviderConfigurationError,
        match="HISTORICAL_COLLECTION_REQUIRES_PERSISTENT_REQUEST_RESERVATION",
    ):
        asyncio.run(
            provider.fetch_fixtures(
                datetime(2026, 11, 16, tzinfo=UTC),
                datetime(2026, 11, 17, tzinfo=UTC),
                competition_ids=["522514093"],
                require_request_reservation=True,
            )
        )

    assert requests == 0


def test_historical_fetch_reserves_each_page_before_http_request() -> None:
    events: list[str] = []
    reservations: list[tuple[str, str, int]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        events.append("http")
        page = int(request.url.params["page"])
        rows = [fixture_row(601 + page, "2026-11-16T10:00:00+00:00")]
        return httpx.Response(
            200,
            json=response_payload(rows, has_more=page == 1),
        )

    def reserve(
        request_key: str,
        window_start: datetime,
        window_end: datetime,
        page_number: int,
        endpoint: str,
        request_params: dict[str, str | int],
    ) -> bool:
        events.append("reserve")
        reservations.append((request_key, endpoint, page_number))
        assert window_start == datetime(2026, 11, 16, tzinfo=UTC)
        assert window_end == datetime(2026, 11, 17, tzinfo=UTC)
        assert endpoint == "/leagues/522514093/fixtures"
        assert request_params["per_page"] == 100
        return True

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    results = asyncio.run(
        provider.fetch_fixtures(
            datetime(2026, 11, 16, tzinfo=UTC),
            datetime(2026, 11, 17, tzinfo=UTC),
            competition_ids=["522514093"],
            request_reserver=reserve,
            require_request_reservation=True,
        )
    )

    assert len(results) == 2
    assert events == ["reserve", "http", "reserve", "http"]
    assert [item[2] for item in reservations] == [1, 2]
    assert len({item[0] for item in reservations}) == 2


def test_existing_reservation_refuses_duplicate_http_request() -> None:
    requests = 0
    reservation_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(
            200,
            json=response_payload([fixture_row(701, "2026-11-16T10:00:00+00:00")], has_more=True),
        )

    def reserve(
        request_key: str,
        window_start: datetime,
        window_end: datetime,
        page_number: int,
        endpoint: str,
        request_params: dict[str, str | int],
    ) -> bool:
        nonlocal reservation_calls
        reservation_calls += 1
        return reservation_calls == 1

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderAPIError, match="request reservation already exists"):
        asyncio.run(
            provider.fetch_fixtures(
                datetime(2026, 11, 16, tzinfo=UTC),
                datetime(2026, 11, 17, tzinfo=UTC),
                competition_ids=["522514093"],
                request_reserver=reserve,
                require_request_reservation=True,
            )
        )

    assert reservation_calls == 2
    assert requests == 1



def test_response_observer_receives_raw_page_evidence_and_resume_page() -> None:
    requests: list[int] = []
    observed: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        requests.append(page)
        return httpx.Response(
            200,
            json=response_payload(
                [fixture_row(900 + page, "2026-11-16T10:00:00+00:00")],
                has_more=False,
            ),
            headers={"X-Request-Id": f"request-page-{page}"},
        )

    def reserve(
        request_key: str,
        window_start: datetime,
        window_end: datetime,
        page_number: int,
        endpoint: str,
        request_params: dict[str, str | int],
    ) -> bool:
        return True

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    results = asyncio.run(
        provider.fetch_fixtures(
            datetime(2026, 11, 16, tzinfo=UTC),
            datetime(2026, 11, 17, tzinfo=UTC),
            competition_ids=["522514093"],
            request_reserver=reserve,
            require_request_reservation=True,
            response_observer=observed.append,
            start_page=2,
        )
    )

    assert requests == [2]
    assert len(results) == 1
    assert len(observed) == 1
    page = observed[0]
    assert page["page_number"] == 2
    assert page["request_key"].endswith(":page:2")
    assert page["endpoint"] == "/leagues/522514093/fixtures"
    assert page["http_status"] == 200
    assert isinstance(page["raw_body"], bytes) and page["raw_body"]
    assert page["response_headers"]["x-request-id"] == "request-page-2"
    assert len(page["fixtures"]) == 1
    assert page["has_more"] is False



def test_historical_request_spacing_is_enforced_between_pages() -> None:
    import time

    request_times: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_times.append(time.monotonic())
        page = int(request.url.params["page"])
        return httpx.Response(
            200,
            json=response_payload([], has_more=page == 1),
        )

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        min_request_interval_seconds=0.02,
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(
        provider.fetch_fixtures(
            datetime(2026, 11, 16, tzinfo=UTC),
            datetime(2026, 11, 17, tzinfo=UTC),
            competition_ids=["522514093"],
        )
    )

    assert len(request_times) == 2
    assert request_times[1] - request_times[0] >= 0.015



def test_raw_response_observer_runs_before_rate_limit_stop() -> None:
    raw_pages: list[dict[str, object]] = []
    parsed_pages: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            content=b'{"error":"rate_limited"}',
            headers={"Retry-After": "17", "X-Request-Id": "rate-limit-request"},
        )

    def reserve(
        request_key: str,
        window_start: datetime,
        window_end: datetime,
        page_number: int,
        endpoint: str,
        request_params: dict[str, str | int],
    ) -> bool:
        return True

    provider = FiveDollarFootballProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderRateLimitError):
        asyncio.run(
            provider.fetch_fixtures(
                datetime(2026, 11, 16, tzinfo=UTC),
                datetime(2026, 11, 17, tzinfo=UTC),
                competition_ids=["522514093"],
                request_reserver=reserve,
                require_request_reservation=True,
                raw_response_observer=lambda item: raw_pages.append(dict(item)) or 17,
                response_observer=parsed_pages.append,
            )
        )

    assert len(raw_pages) == 1
    assert raw_pages[0]["http_status"] == 429
    assert raw_pages[0]["raw_body"] == b'{"error":"rate_limited"}'
    assert raw_pages[0]["response_headers"]["retry-after"] == "17"
    assert parsed_pages == []
