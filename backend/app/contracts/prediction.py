"""Versioned, immutable contracts for PIT-qualified prediction inputs/outputs."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ContractModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AvailabilityBasis(StrEnum):
    SOURCE_PUBLISHED_AT = "SOURCE_PUBLISHED_AT"
    RETRIEVED_AT_ONLY = "RETRIEVED_AT_ONLY"
    SOURCE_EVENT_TIME = "SOURCE_EVENT_TIME"
    PROVIDER_UPDATED_AT = "PROVIDER_UPDATED_AT"
    ESTIMATED = "ESTIMATED"


class RightsStatus(StrEnum):
    APPROVED = "APPROVED"
    REVOKED = "REVOKED"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"


class IdentityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    IDENTITY_REVIEW_REQUIRED = "IDENTITY_REVIEW_REQUIRED"
    CONFLICT = "CONFLICT"
    SOURCE_ROW_ONLY = "SOURCE_ROW_ONLY"


class EligibleObservationEvidence(ContractModel):
    """Evidence for one exact source payload and one exact retrieval sighting."""

    source_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    provider_record_id: str = Field(min_length=1)
    source_observation_id: int = Field(gt=0)
    sighting_id: int = Field(gt=0)
    provider_response_id: int = Field(gt=0)
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_time: datetime | None = None
    source_published_at: datetime | None
    available_at: datetime | None
    retrieved_at: datetime
    availability_basis: AvailabilityBasis
    point_in_time_certifiable: bool
    rights_approval_id: int = Field(gt=0)
    rights_status_at_cutoff: RightsStatus
    permitted_uses: frozenset[str]
    canonical_identity_status: IdentityStatus
    quarantined: bool = False

    @field_validator(
        "event_time", "source_published_at", "available_at", "retrieved_at"
    )
    @classmethod
    def require_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must be timezone-aware")
        return value


class FeatureAdmissionRequest(ContractModel):
    evidence: EligibleObservationEvidence
    prediction_cutoff_at: datetime
    feature_name: str = Field(min_length=1, max_length=160)
    feature_schema_version: str = Field(min_length=1)
    transformation_id: str = Field(min_length=1)
    transformation_version: str = Field(min_length=1)

    @field_validator("prediction_cutoff_at")
    @classmethod
    def require_aware_cutoff(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("prediction cutoff must be timezone-aware")
        return value


class FixturePredictionRequest(ContractModel):
    request_id: str = Field(min_length=1)
    canonical_fixture_id: int = Field(gt=0)
    canonical_competition_id: int = Field(gt=0)
    home_team_id: int = Field(gt=0)
    away_team_id: int = Field(gt=0)
    kickoff_at: datetime
    prediction_cutoff_at: datetime
    feature_snapshot_id: str = Field(min_length=1)
    feature_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_schema_version: str = Field(min_length=1)
    requested_markets: tuple[str, ...] = Field(min_length=1)
    data_quality_tier: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_fixture_cutoff(self) -> FixturePredictionRequest:
        for name in ("kickoff_at", "prediction_cutoff_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.home_team_id == self.away_team_id:
            raise ValueError("home and away team IDs must differ")
        if self.prediction_cutoff_at >= self.kickoff_at:
            raise ValueError("prediction cutoff must be strictly before kickoff")
        return self


class ModelPredictionOutput(ContractModel):
    prediction_id: str
    request_id: str
    model_id: str
    model_version: str
    algorithm: str
    config_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    code_commit: str
    training_dataset_manifest_id: str
    training_cutoff_at: datetime
    feature_snapshot_id: str
    feature_schema_version: str
    generated_at: datetime
    prediction_cutoff_at: datetime
    market_probabilities: dict[str, dict[str, float]]
    expected_home_goals: float | None = Field(default=None, ge=0)
    expected_away_goals: float | None = Field(default=None, ge=0)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    constituent_disagreement: dict[str, float] = Field(default_factory=dict)
    coverage: dict[str, float] = Field(default_factory=dict)
    eligibility_status: str
    publication_status: str
    abstention_reason_codes: tuple[str, ...] = ()

    @field_validator("training_cutoff_at", "generated_at", "prediction_cutoff_at")
    @classmethod
    def require_aware_output_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("output timestamps must be timezone-aware")
        return value

    @field_validator("market_probabilities")
    @classmethod
    def validate_probability_values(
        cls, value: dict[str, dict[str, float]]
    ) -> dict[str, dict[str, float]]:
        for market, outcomes in value.items():
            if not outcomes:
                raise ValueError(f"{market} must contain at least one outcome")
            for outcome, probability in outcomes.items():
                if not isfinite(probability) or not 0.0 <= probability <= 1.0:
                    raise ValueError(f"invalid probability: {market}.{outcome}")
            if len(outcomes) > 1 and abs(sum(outcomes.values()) - 1.0) > 1e-8:
                raise ValueError(f"mutually exclusive outcomes must sum to one: {market}")
        return value
