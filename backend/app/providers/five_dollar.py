"""5DollarFootballAPI adapter.

The adapter is intentionally limited to fixture/result ingestion. It does not
import legacy prediction code, calculate probabilities, or persist provider
responses. API keys are read only at runtime from FIVE_DOLLAR_FOOTBALL_API_KEY.
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.providers.contracts import ProviderCompetition, ProviderFixture, SourceProvenance


DEFAULT_BASE_URL = "https://api.5dollarfootballapi.com/v1"
MAX_FIXTURE_WINDOW = timedelta(hours=24)
MAX_PAGES_PER_WINDOW = 100


class ProviderError(RuntimeError):
    """Base exception for sanitized provider failures."""


class ProviderConfigurationError(ProviderError):
    """Raised when required runtime configuration is missing."""


class ProviderAPIError(ProviderError):
    """Raised when the provider response is unsuccessful or malformed."""


class ProviderRateLimitError(ProviderError):
    """Raised on HTTP 429 so the scheduler can defer and retry safely."""

    def __init__(self, retry_after_seconds: float | None) -> None:
        self.retry_after_seconds = retry_after_seconds
        message = "5DollarFootballAPI rate limit reached"
        if retry_after_seconds is not None:
            message += f"; retry after {retry_after_seconds:g} seconds"
        super().__init__(message)


class ProviderLeagueMovedError(ProviderError):
    """Raised when a retired competition ID has a canonical replacement."""

    def __init__(self, canonical_competition_id: str | None) -> None:
        self.canonical_competition_id = canonical_competition_id
        super().__init__(
            "5DollarFootballAPI reports that this competition ID has moved"
            + (
                f" to {canonical_competition_id}"
                if canonical_competition_id is not None
                else ""
            )
        )


def _utc(value: datetime, field_name: str) -> datetime:
    if value.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return value.astimezone(UTC)


def _time_windows(start: datetime, end: datetime) -> list[datetime]:
    cursor = start
    windows: list[datetime] = []
    while cursor < end:
        windows.append(cursor)
        cursor += MAX_FIXTURE_WINDOW
    return windows


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if result >= 0 else None


def _kickoff(item: dict[str, Any]) -> datetime:
    raw = item.get("kickoff_utc")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ProviderAPIError("5DollarFootballAPI returned an invalid kickoff_utc") from exc
        if parsed.utcoffset() is None:
            raise ProviderAPIError("5DollarFootballAPI kickoff_utc was missing its timezone")
        return parsed.astimezone(UTC)

    timestamp = item.get("kickoff_ts")
    if timestamp is not None:
        try:
            return datetime.fromtimestamp(float(timestamp), tz=UTC)
        except (TypeError, ValueError, OverflowError, OSError) as exc:
            raise ProviderAPIError("5DollarFootballAPI returned an invalid kickoff_ts") from exc

    raise ProviderAPIError("5DollarFootballAPI fixture is missing kickoff_utc/kickoff_ts")


def _normalize_fixture(item: dict[str, Any], retrieved_at: datetime) -> ProviderFixture:
    league = item.get("league")
    teams = item.get("teams")
    goals = item.get("goals")
    corners = item.get("corners")
    cards = item.get("cards")
    if not all(isinstance(value, dict) for value in (league, teams)):
        raise ProviderAPIError("5DollarFootballAPI fixture is missing league or teams data")

    home = teams.get("home")
    away = teams.get("away")
    if not isinstance(home, dict) or not isinstance(away, dict):
        raise ProviderAPIError("5DollarFootballAPI fixture is missing home/away team data")

    fixture_id = item.get("id")
    competition_id = league.get("id")
    home_id = home.get("id")
    away_id = away.get("id")
    if fixture_id is None or competition_id is None or home_id is None or away_id is None:
        raise ProviderAPIError("5DollarFootballAPI fixture is missing a required source ID")

    status_raw = str(item.get("status") or "unknown").strip().casefold()
    status_map = {
        "scheduled": "scheduled",
        "live": "live",
        "in_play": "live",
        "inplay": "live",
        "finished": "finished",
        "postponed": "postponed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "abandoned": "abandoned",
        "unknown": "unknown",
    }
    status = status_map.get(status_raw, "unknown")
    goals = goals if isinstance(goals, dict) else {}
    corners = corners if isinstance(corners, dict) else {}
    cards = cards if isinstance(cards, dict) else {}
    home_cards = cards.get("home") if isinstance(cards.get("home"), dict) else {}
    away_cards = cards.get("away") if isinstance(cards.get("away"), dict) else {}

    return ProviderFixture(
        provenance=SourceProvenance(
            provider="5DollarFootballAPI",
            provider_record_id=str(fixture_id),
            retrieved_at=retrieved_at,
        ),
        competition_id=str(competition_id),
        competition_name=str(league.get("name") or "") or None,
        season_id=str(league.get("season")) if league.get("season") is not None else None,
        home_team_id=str(home_id),
        home_team_name=str(home.get("name") or "") or None,
        away_team_id=str(away_id),
        away_team_name=str(away.get("name") or "") or None,
        kickoff_at=_kickoff(item),
        status=status,
        home_goals=_optional_int(goals.get("home")),
        away_goals=_optional_int(goals.get("away")),
        home_corners=_optional_int(corners.get("home")),
        away_corners=_optional_int(corners.get("away")),
        home_yellow_cards=_optional_int(home_cards.get("yellow")),
        away_yellow_cards=_optional_int(away_cards.get("yellow")),
        home_red_cards=_optional_int(home_cards.get("red")),
        away_red_cards=_optional_int(away_cards.get("red")),
    )


class FiveDollarFootballProvider:
    """Read-only 5DollarFootballAPI fixture/result provider."""

    provider_name = "5DollarFootballAPI"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 20.0,
        max_pages_per_window: int = MAX_PAGES_PER_WINDOW,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        configured_key = (
            api_key if api_key is not None else os.getenv("FIVE_DOLLAR_FOOTBALL_API_KEY", "")
        )
        self._api_key = configured_key.strip()
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_pages_per_window = max_pages_per_window
        self._transport = transport

    async def fetch_competitions(
        self,
        country_code: str | None = None,
        active_since: datetime | None = None,
    ) -> Sequence[ProviderCompetition]:
        if not self._api_key:
            raise ProviderConfigurationError(
                "FIVE_DOLLAR_FOOTBALL_API_KEY is not configured"
            )

        retrieved_at = datetime.now(UTC)
        params: dict[str, str | int] = {"include": "seasons", "per_page": 100}
        if country_code:
            params["country"] = country_code
        if active_since is not None:
            params["active_since"] = int(_utc(active_since, "active_since").timestamp())

        competitions: list[ProviderCompetition] = []
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            page = 1
            while True:
                params["page"] = page
                try:
                    response = await client.get(
                        "leagues",
                        params=params,
                        headers={
                            "Authorization": f"Bearer {self._api_key}",
                            "Accept": "application/json",
                        },
                    )
                except httpx.HTTPError as exc:
                    raise ProviderAPIError(
                        f"5DollarFootballAPI network request failed ({type(exc).__name__})"
                    ) from None

                if response.status_code == 429:
                    raw_retry = response.headers.get("Retry-After")
                    try:
                        retry_after = float(raw_retry) if raw_retry is not None else None
                    except ValueError:
                        retry_after = None
                    raise ProviderRateLimitError(retry_after)

                if response.status_code >= 400:
                    raise ProviderAPIError(
                        f"5DollarFootballAPI returned HTTP {response.status_code}"
                    )
                try:
                    payload = response.json()
                except ValueError:
                    raise ProviderAPIError(
                        "5DollarFootballAPI returned invalid JSON"
                    ) from None

                if not isinstance(payload, dict) or payload.get("success") != 1:
                    raise ProviderAPIError(
                        "5DollarFootballAPI returned an unsuccessful response"
                    )
                rows = payload.get("data")
                if not isinstance(rows, list):
                    raise ProviderAPIError(
                        "5DollarFootballAPI leagues response is missing its data list"
                    )

                for row in rows:
                    if not isinstance(row, dict) or row.get("id") is None or not row.get("name"):
                        raise ProviderAPIError(
                            "5DollarFootballAPI returned a malformed competition row"
                        )
                    country = row.get("country")
                    country = country if isinstance(country, dict) else {}
                    seasons = row.get("seasons")
                    season_names = tuple(
                        str(season.get("season"))
                        for season in seasons
                        if isinstance(season, dict) and season.get("season") is not None
                    ) if isinstance(seasons, list) else ()
                    last_fixture_at = row.get("last_fixture_utc")
                    if last_fixture_at is not None:
                        try:
                            last_fixture_at = datetime.fromisoformat(
                                str(last_fixture_at).replace("Z", "+00:00")
                            )
                        except ValueError:
                            raise ProviderAPIError(
                                "5DollarFootballAPI returned invalid last_fixture_utc"
                            ) from None
                    competitions.append(
                        ProviderCompetition(
                            provenance=SourceProvenance(
                                provider=self.provider_name,
                                provider_record_id=str(row["id"]),
                                retrieved_at=retrieved_at,
                            ),
                            competition_id=str(row["id"]),
                            name=str(row["name"]),
                            country_code=(
                                str(country["code"]) if country.get("code") is not None else None
                            ),
                            country_name=(
                                str(country["name"]) if country.get("name") is not None else None
                            ),
                            is_popular=(
                                bool(row["is_popular"]) if row.get("is_popular") is not None else None
                            ),
                            has_standings=(
                                bool(row["has_standings"])
                                if row.get("has_standings") is not None
                                else None
                            ),
                            last_fixture_at=last_fixture_at,
                            seasons=season_names,
                        )
                    )

                pagination = payload.get("pagination") or {}
                if not isinstance(pagination, dict):
                    raise ProviderAPIError(
                        "5DollarFootballAPI returned malformed pagination metadata"
                    )
                if not pagination.get("has_more", False):
                    break
                page += 1
                if page > self._max_pages_per_window:
                    raise ProviderAPIError(
                        "5DollarFootballAPI competition pagination exceeded the configured safety limit"
                    )

        return competitions

    async def fetch_fixtures(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_ids: Sequence[str] | None = None,
    ) -> Sequence[ProviderFixture]:
        if not self._api_key:
            raise ProviderConfigurationError(
                "FIVE_DOLLAR_FOOTBALL_API_KEY is not configured"
            )

        start = _utc(start_at, "start_at")
        end = _utc(end_at, "end_at")
        if end <= start:
            raise ValueError("end_at must be later than start_at")

        competitions = list(dict.fromkeys(str(value) for value in (competition_ids or [])))
        retrieved_at = datetime.now(UTC)
        fixtures: list[ProviderFixture] = []

        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            transport=self._transport,
            follow_redirects=False,
        ) as client:
            # The global fixture endpoint is limited to 24-hour windows.
            # League fixture history accepts an unrestricted start/end window,
            # so use it for targeted historical imports to conserve quota.
            windows = (
                [(start, end)]
                if competitions
                else [
                    (cursor, min(cursor + MAX_FIXTURE_WINDOW, end))
                    for cursor in _time_windows(start, end)
                ]
            )
            for window_start, window_end in windows:
                for competition_id in (competitions or [None]):
                    page = 1
                    while True:
                        params: dict[str, str | int] = {
                            "start_time": int(window_start.timestamp()),
                            "end_time": int(window_end.timestamp()),
                            "status": "all",
                            "page": page,
                            "per_page": 100,
                        }
                        path = (
                            f"leagues/{competition_id}/fixtures"
                            if competition_id is not None
                            else "fixtures"
                        )

                        try:
                            response = await client.get(
                                path,
                                params=params,
                                headers={
                                    "Authorization": f"Bearer {self._api_key}",
                                    "Accept": "application/json",
                                },
                            )
                        except httpx.HTTPError as exc:
                            raise ProviderAPIError(
                                f"5DollarFootballAPI network request failed ({type(exc).__name__})"
                            ) from None

                        if response.status_code == 429:
                            raw_retry = response.headers.get("Retry-After")
                            try:
                                retry_after = float(raw_retry) if raw_retry is not None else None
                            except ValueError:
                                retry_after = None
                            raise ProviderRateLimitError(retry_after)

                        try:
                            payload = response.json()
                        except ValueError:
                            raise ProviderAPIError(
                                "5DollarFootballAPI returned invalid JSON"
                            ) from None

                        if response.status_code == 301:
                            error = payload.get("error") if isinstance(payload, dict) else {}
                            canonical_id = (
                                error.get("canonical_id") if isinstance(error, dict) else None
                            )
                            raise ProviderLeagueMovedError(
                                str(canonical_id) if canonical_id is not None else None
                            )

                        if response.status_code >= 400:
                            raise ProviderAPIError(
                                f"5DollarFootballAPI returned HTTP {response.status_code}"
                            )

                        if not isinstance(payload, dict) or payload.get("success") != 1:
                            raise ProviderAPIError(
                                "5DollarFootballAPI returned an unsuccessful response"
                            )
                        rows = payload.get("data")
                        if not isinstance(rows, list):
                            raise ProviderAPIError(
                                "5DollarFootballAPI response is missing its data list"
                            )

                        for row in rows:
                            if not isinstance(row, dict):
                                raise ProviderAPIError(
                                    "5DollarFootballAPI returned a malformed fixture row"
                                )
                            fixtures.append(_normalize_fixture(row, retrieved_at))

                        pagination = payload.get("pagination") or {}
                        if not isinstance(pagination, dict):
                            raise ProviderAPIError(
                                "5DollarFootballAPI returned malformed pagination metadata"
                            )
                        if not pagination.get("has_more", False):
                            break
                        page += 1
                        if page > self._max_pages_per_window:
                            raise ProviderAPIError(
                                "5DollarFootballAPI pagination exceeded the configured safety limit"
                            )
        return fixtures
