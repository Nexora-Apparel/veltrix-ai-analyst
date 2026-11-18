"""Immutable point-in-time evidence envelope for prospective football research.

The database must supply system_observed_at (DEFAULT clock_timestamp()) and
return it from INSERT ... RETURNING. Application retrieval time is not a
substitute. A row is PIT eligible only when the database-observed instant is
strictly earlier than the fixture kickoff.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from datetime import datetime


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class FixtureIdentity:
    provider: str
    source_id: str
    provider_competition_id: str
    provider_fixture_id: str
    home_team_provider_id: str
    away_team_provider_id: str
    kickoff_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "provider", "source_id", "provider_competition_id",
            "provider_fixture_id", "home_team_provider_id", "away_team_provider_id",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.home_team_provider_id == self.away_team_provider_id:
            raise ValueError("home and away provider team IDs must differ")
        _aware(self.kickoff_at, "kickoff_at")

    @property
    def stable_key(self) -> str:
        return (
            f"{self.provider}:{self.source_id}:"
            f"{self.provider_competition_id}:{self.provider_fixture_id}"
        )


@dataclass(frozen=True, slots=True)
class ProspectiveEvidence:
    """One immutable raw source response observed against one fixture.

    system_observed_at must be the value returned by the database clock, not
    an application-generated timestamp. source_published_at and source_available_at
    are nullable and may be populated only from explicit source metadata.
    """

    fixture: FixtureIdentity
    provider_response_id: str
    retrieved_at: datetime
    system_observed_at: datetime
    raw_payload_sha256: str
    source_published_at: datetime | None = None
    source_available_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.provider_response_id.strip():
            raise ValueError("provider_response_id is required")
        _aware(self.retrieved_at, "retrieved_at")
        _aware(self.system_observed_at, "system_observed_at")
        if self.source_published_at is not None:
            _aware(self.source_published_at, "source_published_at")
            if self.source_published_at > self.system_observed_at:
                raise ValueError("source_published_at cannot follow system_observed_at")
        if self.source_available_at is not None:
            _aware(self.source_available_at, "source_available_at")
            if self.source_available_at > self.system_observed_at:
                raise ValueError("source_available_at cannot follow system_observed_at")
        if self.retrieved_at < self.system_observed_at:
            raise ValueError("retrieved_at cannot precede database observation time")
        if not _SHA256.fullmatch(self.raw_payload_sha256):
            raise ValueError("raw_payload_sha256 must be a lowercase SHA-256 digest")

    @property
    def point_in_time_certifiable(self) -> bool:
        """True only for evidence captured by the DB strictly before kickoff."""
        return self.system_observed_at < self.fixture.kickoff_at

    @property
    def availability_basis(self) -> str:
        return "SYSTEM_OBSERVED_AT"


def hash_raw_payload(raw_payload: bytes) -> str:
    """Hash exact response bytes; do not hash normalized/re-serialized JSON."""
    if not isinstance(raw_payload, bytes) or not raw_payload:
        raise ValueError("raw_payload must be non-empty response bytes")
    return hashlib.sha256(raw_payload).hexdigest()
