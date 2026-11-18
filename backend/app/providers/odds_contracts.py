"""Strict point-in-time contracts for prospective bookmaker odds capture."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.providers.contracts import StrictModel


class OddsObservation(StrictModel):
    provider: str = Field(min_length=1, max_length=80)
    provider_fixture_id: str = Field(min_length=1, max_length=160)
    bookmaker: str = Field(min_length=1, max_length=120)
    market: Literal["1X2", "TOTALS", "BTTS"]
    selection: str = Field(min_length=1, max_length=80)
    line: float | None = None
    decimal_odds: float = Field(gt=1.0, le=1000.0)
    source_tick_at: datetime
    request_started_at: datetime
    retrieved_at: datetime
    provider_response_date: datetime | None = None
    kickoff_at: datetime
    value_bet_decision_cutoff_at: datetime
    in_play: bool
    source_observation_id: str = Field(min_length=1, max_length=200)
    source_response_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    rights_approval_id: str = Field(min_length=1, max_length=200)
    use_purpose: Literal["VALUE_BETTING_ONLY"]

    @field_validator("source_tick_at", "request_started_at", "retrieved_at", "provider_response_date", "kickoff_at", "value_bet_decision_cutoff_at")
    @classmethod
    def require_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("all odds timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def enforce_point_in_time(self) -> OddsObservation:
        if self.request_started_at > self.retrieved_at:
            raise ValueError("request cannot start after retrieval")
        if self.source_tick_at > self.retrieved_at:
            raise ValueError("source tick cannot be later than retrieval")
        if self.retrieved_at > self.value_bet_decision_cutoff_at:
            raise ValueError("odds were retrieved after the value-bet decision cutoff")
        if self.source_tick_at > self.value_bet_decision_cutoff_at:
            raise ValueError("source odds tick is after the value-bet decision cutoff")
        if self.value_bet_decision_cutoff_at >= self.kickoff_at:
            raise ValueError("value-bet decision cutoff must be strictly before kickoff")
        if self.in_play:
            raise ValueError("in-play odds cannot enter pre-match value-betting decisions")
        return self

class OddsCaptureEnvelope(StrictModel):
    captured_at: datetime
    request_id: str = Field(min_length=1, max_length=200)
    observations: tuple[OddsObservation, ...]

    @field_validator("captured_at")
    @classmethod
    def captured_at_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def capture_not_before_retrieval(self) -> OddsCaptureEnvelope:
        if any(item.retrieved_at > self.captured_at for item in self.observations):
            raise ValueError("envelope capture cannot precede observation retrieval")
        return self
