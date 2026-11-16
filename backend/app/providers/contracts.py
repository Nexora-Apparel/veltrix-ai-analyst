"""Provider-neutral contracts for source data ingestion.

Concrete providers must translate their API responses into these models. This
module intentionally contains no HTTP client, credentials, persistence, or
prediction logic.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol, Sequence

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
    season_id: str | None = Field(default=None, max_length=100)
    home_team_id: str = Field(min_length=1, max_length=160)
    away_team_id: str = Field(min_length=1, max_length=160)
    kickoff_at: datetime
    status: FixtureStatus = "unknown"

    @field_validator("kickoff_at")
    @classmethod
    def kickoff_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("kickoff_at must include a timezone offset")
        return value

    @model_validator(mode="after")
    def teams_must_be_distinct(self) -> "ProviderFixture":
        if self.home_team_id == self.away_team_id:
            raise ValueError("home_team_id and away_team_id must be different")
        return self


class FootballDataProvider(Protocol):
    """Minimal async contract implemented by each football data provider."""

    provider_name: str

    async def fetch_fixtures(
        self,
        start_at: datetime,
        end_at: datetime,
        competition_ids: Sequence[str] | None = None,
    ) -> Sequence[ProviderFixture]:
        """Return normalized fixtures in the requested time window."""
        ...
