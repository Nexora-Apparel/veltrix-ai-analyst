"""Strict application-level admission for point-in-time model features."""
from __future__ import annotations

from datetime import datetime

from app.contracts.prediction import (
    AvailabilityBasis,
    FeatureAdmissionRequest,
    IdentityStatus,
    RightsStatus,
)


class FeatureAdmissionError(ValueError):
    """Raised when source, rights, identity or temporal evidence is insufficient."""


def require_feature_admission(request: FeatureAdmissionRequest) -> None:
    """Fail closed unless the exact observed payload is eligible at its cutoff."""
    evidence = request.evidence
    cutoff = request.prediction_cutoff_at

    if evidence.data_domain == "BOOKMAKER_ODDS":
        raise FeatureAdmissionError("BOOKMAKER_ODDS_FORBIDDEN_IN_CORE_PREDICTION_FEATURES")
    if evidence.data_domain != "FOOTBALL_MATCH_DATA":
        raise FeatureAdmissionError("UNSUPPORTED_PREDICTION_FEATURE_DATA_DOMAIN")
    if not evidence.point_in_time_certifiable:
        raise FeatureAdmissionError("SOURCE_NOT_POINT_IN_TIME_CERTIFIABLE")
    if evidence.availability_basis is not AvailabilityBasis.SOURCE_PUBLISHED_AT:
        raise FeatureAdmissionError("VERIFIED_SOURCE_PUBLICATION_TIME_REQUIRED")
    if evidence.source_published_at is None or evidence.available_at is None:
        raise FeatureAdmissionError("SOURCE_PUBLICATION_AND_AVAILABILITY_TIMES_REQUIRED")
    if evidence.provider_response_id <= 0 or evidence.sighting_id <= 0:
        raise FeatureAdmissionError("EXACT_RESPONSE_AND_SIGHTING_REQUIRED")
    if evidence.source_published_at > evidence.retrieved_at:
        raise FeatureAdmissionError("SOURCE_PUBLICATION_AFTER_RETRIEVAL")
    if evidence.available_at < evidence.source_published_at:
        raise FeatureAdmissionError("AVAILABILITY_PRECEDES_SOURCE_PUBLICATION")
    if evidence.source_published_at > cutoff or evidence.available_at > cutoff:
        raise FeatureAdmissionError("SOURCE_NOT_AVAILABLE_AT_PREDICTION_CUTOFF")
    if evidence.rights_status_at_cutoff is not RightsStatus.APPROVED:
        raise FeatureAdmissionError("SOURCE_RIGHTS_NOT_APPROVED_AT_CUTOFF")
    required_uses = {"FEATURE_ENGINEERING", "MODEL_TRAINING"}
    if not required_uses.issubset(evidence.permitted_uses):
        raise FeatureAdmissionError("SOURCE_RIGHTS_DO_NOT_PERMIT_MODEL_FEATURES")
    if evidence.canonical_identity_status is not IdentityStatus.VERIFIED:
        raise FeatureAdmissionError("CANONICAL_IDENTITY_NOT_VERIFIED")
    if evidence.quarantined:
        raise FeatureAdmissionError("SOURCE_OBSERVATION_QUARANTINED")


def require_prediction_cutoff_before_kickoff(
    *, prediction_cutoff_at: datetime, kickoff_at: datetime
) -> None:
    for name, value in (
        ("prediction_cutoff_at", prediction_cutoff_at),
        ("kickoff_at", kickoff_at),
    ):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name.upper()}_MUST_BE_TIMEZONE_AWARE")
    if prediction_cutoff_at >= kickoff_at:
        raise ValueError("PREDICTION_CUTOFF_MUST_PRECEDE_KICKOFF")
