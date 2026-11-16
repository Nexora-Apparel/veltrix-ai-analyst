"""Provider-neutral contracts for source data ingestion.

Concrete providers must translate their API responses into these models. This
module intentionally contains no HTTP client, credentials, persistence, or
prediction logic.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceProvenance(StrictModel):
    """Traceable origin and timing metadata for a provider-sourced record."""

    provider: str = Field(min_length=1, max_length=80)
    provider_record_id: str = Field(min_length=1, max_length=160)
    retrieved_at: datetime
    source_updated_at: datetime | None = None

    @field_validator("retrieved_at", "source_updated_at")
    @classmethod
    def timestamps_must_be_timezone_aware(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone offset")
        return value


FixtureStatus = Literal[
    "scheduled",
    "live",
    "finished",
    "postponed",
    "cancelled",
    "abandoned",
    "unknown",
]


class ProviderFixture(StrictModel):
    """Normalized fixture data retaining provider identity and provenance."""

    provenance: SourceProvenance
    competition_id: str = Field(min_length=1, max_length=160)
    competition_name: str | None = Field(default=None, max_length=200)
    season_id: str | None = Field(default=None, max_length=100)
    home_team_id: str = Field(min_length=1, max_length=160)
    home_team_name: str | None = Field(default=None, max_length=200)
    away_team_id: str = Field(min_length=1, max_length=160)
    away_team_name: str | None = Field(default=None, max_length=200)
    kickoff_at: datetime
    status: FixtureStatus = "unknown"
    home_goals: int | None = Field(default=None, ge=0)
    away_goals: int | None = Field(default=None, ge=0)
    home_corners: int | None = Field(default=None, ge=0)
    away_corners: int | None = Field(default=None, ge=0)
    home_yellow_cards: int | None = Field(default=None, ge=0)
    away_yellow_cards: int | None = Field(default=None, ge=0)
    home_red_cards: int | None = Field(default=None, ge=0)
    away_red_cards: int | None = Field(default=None, ge=0)

    @field_validator("kickoff_at")
    @classmethod
    def kickoff_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("kickoff_at must include a timezone offset")
        return value

    @model_validator(mode="after")
    def teams_must_be_distinct(self) -> ProviderFixture:
        if self.home_team_id == self.away_team_id:
            raise ValueError("home_team_id and away_team_id must be different")
        return self


class ProviderAccountStatus(StrictModel):
    """Non-secret account plan and quota metadata returned by a provider."""

    provider: str
    plan: str
    request_limit: int = Field(ge=1)
    rate_window_seconds: int = Field(ge=1)
    burst_per_minute: int | None = Field(default=None, ge=1)
    requests_today: int = Field(default=0, ge=0)


class ProviderCompetition(StrictModel):
    """Normalized competition metadata with provider-local identity."""

    provenance: SourceProvenance
    competition_id: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=200)
    country_code: str | None = Field(default=None, max_length=32)
    country_name: str | None = Field(default=None, max_length=120)
    is_popular: bool | None = None
    has_standings: bool | None = None
    last_fixture_at: datetime | None = None
    seasons: tuple[str, ...] = ()

    @field_validator("last_fixture_at")
    @classmethod
    def last_fixture_must_be_timezone_aware(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("last_fixture_at must include a timezone offset")
        return value


class FootballDataProvider(Protocol):
    """Minimal async contract implemented by each football data provider."""

    provider_name: str

    async def fetch_account_status(self) -> ProviderAccountStatus:
        """Return plan and quota metadata without exposing credentials."""
        ...

    async def fetch_competitions(
        self,
        country_code: str | None = None,
        active_since: datetime | None = None,
    ) -> Sequence[ProviderCompetition]:
        """Return normalized competitions visible to this provider account."""
        ...

    async def fetch_fixtures(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_ids: Sequence[str] | None = None,
    ) -> Sequence[ProviderFixture]:
        """Return normalized fixtures in the requested time window."""
        ...
