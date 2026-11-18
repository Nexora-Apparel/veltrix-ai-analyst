"""Typed, non-persistent manifest for one prospective bookmaker-odds request.

This contract records capture provenance only. It performs no network request,
database write, retry, pagination or scheduled collection.
"""
from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.providers.contracts import StrictModel


def deterministic_capture_identity(
    *,
    provider: str,
    provider_event_id: str,
    provider_fixture_id: str,
    canonical_fixture_id: str,
    competition_id: str,
    request_started_at: datetime,
) -> str:
    """Return a stable identity for one provider-fixture request attempt."""
    payload = {
        "provider": provider,
        "provider_event_id": provider_event_id,
        "provider_fixture_id": provider_fixture_id,
        "canonical_fixture_id": canonical_fixture_id,
        "competition_id": competition_id,
        "request_started_at": request_started_at.isoformat(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


class ProspectiveOddsCaptureManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    capture_identity: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    provider: str = Field(min_length=1, max_length=80)
    provider_event_id: str = Field(min_length=1, max_length=160)
    provider_fixture_id: str = Field(min_length=1, max_length=160)
    canonical_fixture_id: str = Field(min_length=1, max_length=160)
    competition_id: str = Field(min_length=1, max_length=100)
    bookmaker_slug: str = Field(min_length=1, max_length=120)
    market_key: str = Field(min_length=1, max_length=80)
    request_started_at: datetime
    retrieved_at: datetime
    provider_response_date: datetime | None = None
    value_bet_decision_cutoff_at: datetime
    fixture_kickoff_at: datetime
    http_status: int = Field(ge=100, le=599)
    response_bytes: int = Field(ge=0)
    response_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    rights_approval_id: str = Field(min_length=1, max_length=200)
    observation_count: int = Field(ge=0)
    admission: Literal["ELIGIBLE", "REJECTED"]
    rejection_reason: str | None = Field(default=None, max_length=300)

    @field_validator(
        "request_started_at", "retrieved_at", "provider_response_date",
        "value_bet_decision_cutoff_at", "fixture_kickoff_at",
    )
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("manifest timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def enforce_capture_and_admission_rules(self) -> ProspectiveOddsCaptureManifest:
        if self.request_started_at > self.retrieved_at:
            raise ValueError("request cannot start after retrieval")
        if self.admission == "ELIGIBLE":
            if self.http_status != 200:
                raise ValueError("eligible capture requires HTTP 200")
            if self.response_bytes <= 0 or self.observation_count <= 0:
                raise ValueError("eligible capture requires a non-empty response and observations")
            if self.retrieved_at > self.value_bet_decision_cutoff_at:
                raise ValueError("eligible capture was retrieved after the decision cutoff")
            if self.value_bet_decision_cutoff_at >= self.fixture_kickoff_at:
                raise ValueError("eligible decision cutoff must precede kickoff")
            if self.rejection_reason is not None:
                raise ValueError("eligible capture cannot have a rejection reason")
        elif not self.rejection_reason:
            raise ValueError("rejected capture requires an explicit rejection reason")
        return self
