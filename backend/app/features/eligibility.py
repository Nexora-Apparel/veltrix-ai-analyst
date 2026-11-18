"""Fail-closed point-in-time eligibility for pre-match feature inputs.

A payload is eligible only when its exact source publication time is verified,
or its exact immutable provider response was captured by the system before the
prediction cutoff. Kickoff, event time and post-event proxies never establish
system availability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class FeatureEligibilityError(ValueError):
    """Raised when source evidence cannot prove availability before the cutoff."""


@dataclass(frozen=True, slots=True)
class PublicationEvidence:
    source_published_at: datetime | None
    available_at: datetime | None
    retrieved_at: datetime
    availability_basis: str
    point_in_time_certifiable: bool
    provider_response_id: int | None
    payload_sha256: str


def require_pre_match_eligibility(
    evidence: PublicationEvidence,
    *,
    prediction_cutoff_at: datetime,
) -> None:
    """Raise unless this exact observed payload was published and available by cutoff."""
    timestamps = {
        "prediction_cutoff_at": prediction_cutoff_at,
        "retrieved_at": evidence.retrieved_at,
        "source_published_at": evidence.source_published_at,
        "available_at": evidence.available_at,
    }
    for field_name, value in timestamps.items():
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise FeatureEligibilityError(f"{field_name.upper()}_MUST_BE_TIMEZONE_AWARE")

    if evidence.point_in_time_certifiable is not True:
        raise FeatureEligibilityError("SOURCE_NOT_POINT_IN_TIME_CERTIFIABLE")
    if evidence.available_at is None:
        raise FeatureEligibilityError("SOURCE_AVAILABILITY_TIME_REQUIRED")
    if evidence.provider_response_id is None:
        raise FeatureEligibilityError("CAPTURED_PROVIDER_RESPONSE_REQUIRED")
    if len(evidence.payload_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in evidence.payload_sha256
    ):
        raise FeatureEligibilityError("VALID_PAYLOAD_SHA256_REQUIRED")

    if evidence.availability_basis == "SOURCE_PUBLISHED_AT":
        if evidence.source_published_at is None:
            raise FeatureEligibilityError("SOURCE_PUBLICATION_TIME_REQUIRED")
        if evidence.source_published_at > evidence.retrieved_at:
            raise FeatureEligibilityError("SOURCE_PUBLICATION_AFTER_RETRIEVAL")
        if evidence.available_at < evidence.source_published_at:
            raise FeatureEligibilityError("AVAILABILITY_PRECEDES_SOURCE_PUBLICATION")
        if evidence.available_at > evidence.retrieved_at:
            raise FeatureEligibilityError("AVAILABILITY_AFTER_RETRIEVAL")
        if evidence.source_published_at > prediction_cutoff_at:
            raise FeatureEligibilityError("SOURCE_PUBLISHED_AFTER_PREDICTION_CUTOFF")
        if evidence.available_at > prediction_cutoff_at:
            raise FeatureEligibilityError("SOURCE_AVAILABLE_AFTER_PREDICTION_CUTOFF")
    elif evidence.availability_basis == "SYSTEM_OBSERVED_AT":
        if evidence.source_published_at is not None or evidence.available_at != evidence.retrieved_at:
            raise FeatureEligibilityError("SYSTEM_OBSERVED_AVAILABILITY_TIMESTAMP_REQUIRED")
        if evidence.retrieved_at > prediction_cutoff_at:
            raise FeatureEligibilityError("SOURCE_NOT_OBSERVED_BY_PREDICTION_CUTOFF")
    else:
        raise FeatureEligibilityError("VERIFIED_AVAILABILITY_BASIS_REQUIRED")
