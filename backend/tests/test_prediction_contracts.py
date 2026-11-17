from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.contracts.prediction import (
    AvailabilityBasis,
    EligibleObservationEvidence,
    FeatureAdmissionRequest,
    FixturePredictionRequest,
    IdentityStatus,
    RightsStatus,
)
from app.features.admission import FeatureAdmissionError, require_feature_admission

CUTOFF = datetime(2026, 11, 17, 12, 0, tzinfo=UTC)
PUBLISHED = CUTOFF - timedelta(hours=2)
RETRIEVED = CUTOFF - timedelta(hours=1)


def make_evidence(**changes: object) -> EligibleObservationEvidence:
    values: dict[str, object] = {
        "source_id": "qualified-source",
        "provider": "provider-x",
        "provider_record_id": "fixture-123",
        "source_observation_id": 12,
        "sighting_id": 21,
        "provider_response_id": 31,
        "payload_sha256": "a" * 64,
        "event_time": CUTOFF + timedelta(days=1),
        "source_published_at": PUBLISHED,
        "available_at": PUBLISHED,
        "retrieved_at": RETRIEVED,
        "availability_basis": AvailabilityBasis.SOURCE_PUBLISHED_AT,
        "point_in_time_certifiable": True,
        "rights_approval_id": "approval-7",
        "rights_status_at_cutoff": RightsStatus.APPROVED,
        "permitted_uses": frozenset({"FEATURE_ENGINEERING", "MODEL_TRAINING"}),
        "canonical_identity_status": IdentityStatus.VERIFIED,
        "quarantined": False,
    }
    values.update(changes)
    return EligibleObservationEvidence(**values)


def make_request(**changes: object) -> FeatureAdmissionRequest:
    values: dict[str, object] = {
        "evidence": make_evidence(),
        "prediction_cutoff_at": CUTOFF,
        "feature_name": "team_attack_strength",
        "feature_schema_version": "1.0.0",
        "transformation_id": "rolling-goals",
        "transformation_version": "1.0.0",
    }
    values.update(changes)
    return FeatureAdmissionRequest(**values)


def test_complete_verified_evidence_is_admitted() -> None:
    require_feature_admission(make_request())


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"point_in_time_certifiable": False}, "SOURCE_NOT_POINT_IN_TIME_CERTIFIABLE"),
        ({"availability_basis": AvailabilityBasis.RETRIEVED_AT_ONLY}, "VERIFIED_SOURCE_PUBLICATION_TIME_REQUIRED"),
        ({"source_published_at": None}, "SOURCE_PUBLICATION_AND_AVAILABILITY_TIMES_REQUIRED"),
        ({"available_at": CUTOFF + timedelta(seconds=1)}, "SOURCE_NOT_AVAILABLE_AT_PREDICTION_CUTOFF"),
        ({"rights_status_at_cutoff": RightsStatus.REVOKED}, "SOURCE_RIGHTS_NOT_APPROVED_AT_CUTOFF"),
        ({"permitted_uses": frozenset({"FEATURE_ENGINEERING"})}, "SOURCE_RIGHTS_DO_NOT_PERMIT_MODEL_FEATURES"),
        ({"canonical_identity_status": IdentityStatus.CONFLICT}, "CANONICAL_IDENTITY_NOT_VERIFIED"),
        ({"canonical_identity_status": IdentityStatus.SOURCE_ROW_ONLY}, "CANONICAL_IDENTITY_NOT_VERIFIED"),
        ({"quarantined": True}, "SOURCE_OBSERVATION_QUARANTINED"),
    ],
)
def test_ineligible_evidence_is_rejected(changes: dict[str, object], reason: str) -> None:
    with pytest.raises(FeatureAdmissionError, match=reason):
        require_feature_admission(make_request(evidence=make_evidence(**changes)))


def test_event_time_does_not_replace_publication_time() -> None:
    with pytest.raises(FeatureAdmissionError, match="VERIFIED_SOURCE_PUBLICATION_TIME_REQUIRED"):
        require_feature_admission(
            make_request(evidence=make_evidence(availability_basis=AvailabilityBasis.SOURCE_EVENT_TIME))
        )


def test_naive_evidence_timestamp_is_rejected_by_contract() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        make_evidence(source_published_at=datetime(2026, 11, 17, 10, 0))


def test_prediction_request_rejects_cutoff_at_or_after_kickoff() -> None:
    with pytest.raises(ValidationError, match="strictly before kickoff"):
        FixturePredictionRequest(
            request_id="r1",
            canonical_fixture_id=UUID("00000000-0000-0000-0000-000000000001"),
            canonical_competition_id=UUID("00000000-0000-0000-0000-000000000002"),
            home_team_id=UUID("00000000-0000-0000-0000-000000000010"),
            away_team_id=UUID("00000000-0000-0000-0000-000000000011"),
            kickoff_at=CUTOFF,
            prediction_cutoff_at=CUTOFF,
            feature_snapshot_id="snap-1",
            feature_snapshot_sha256="b" * 64,
            feature_schema_version="1.0.0",
            requested_markets=("1X2",),
            data_quality_tier="PIT_VERIFIED",
        )


def test_prediction_request_rejects_same_team_on_both_sides() -> None:
    with pytest.raises(ValidationError, match="must differ"):
        FixturePredictionRequest(
            request_id="r1",
            canonical_fixture_id=UUID("00000000-0000-0000-0000-000000000001"),
            canonical_competition_id=UUID("00000000-0000-0000-0000-000000000002"),
            home_team_id=UUID("00000000-0000-0000-0000-000000000010"),
            away_team_id=UUID("00000000-0000-0000-0000-000000000010"),
            kickoff_at=CUTOFF + timedelta(hours=1),
            prediction_cutoff_at=CUTOFF,
            feature_snapshot_id="snap-1",
            feature_snapshot_sha256="b" * 64,
            feature_schema_version="1.0.0",
            requested_markets=("1X2",),
            data_quality_tier="PIT_VERIFIED",
        )
