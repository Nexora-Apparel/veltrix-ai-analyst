from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.features.eligibility import (
    FeatureEligibilityError,
    PublicationEvidence,
    require_pre_match_eligibility,
)

CUTOFF = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
PUBLISHED = CUTOFF - timedelta(hours=2)
RETRIEVED = CUTOFF - timedelta(hours=1)
HASH = "a" * 64


def evidence(**overrides: object) -> PublicationEvidence:
    values: dict[str, object] = {
        "source_published_at": PUBLISHED,
        "available_at": PUBLISHED,
        "retrieved_at": RETRIEVED,
        "availability_basis": "SOURCE_PUBLISHED_AT",
        "point_in_time_certifiable": True,
        "provider_response_id": 101,
        "payload_sha256": HASH,
    }
    values.update(overrides)
    return PublicationEvidence(**values)  # type: ignore[arg-type]


def test_verified_publication_before_cutoff_is_eligible() -> None:
    require_pre_match_eligibility(evidence(), prediction_cutoff_at=CUTOFF)


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"point_in_time_certifiable": False}, "SOURCE_NOT_POINT_IN_TIME_CERTIFIABLE"),
        ({"availability_basis": "RETRIEVED_AT_ONLY"}, "VERIFIED_SOURCE_PUBLICATION_TIME_REQUIRED"),
        ({"source_published_at": None}, "SOURCE_PUBLICATION_AND_AVAILABILITY_TIMES_REQUIRED"),
        ({"available_at": None}, "SOURCE_PUBLICATION_AND_AVAILABILITY_TIMES_REQUIRED"),
        ({"provider_response_id": None}, "CAPTURED_PROVIDER_RESPONSE_REQUIRED"),
        ({"source_published_at": CUTOFF + timedelta(seconds=1)}, "SOURCE_PUBLICATION_AFTER_RETRIEVAL"),
        ({"available_at": CUTOFF + timedelta(seconds=1)}, "SOURCE_AVAILABLE_AFTER_PREDICTION_CUTOFF"),
        ({"available_at": PUBLISHED - timedelta(seconds=1)}, "AVAILABILITY_PRECEDES_SOURCE_PUBLICATION"),
        ({"payload_sha256": "not-a-hash"}, "VALID_PAYLOAD_SHA256_REQUIRED"),
    ],
)
def test_unverifiable_or_future_evidence_fails_closed(
    changes: dict[str, object], error: str
) -> None:
    with pytest.raises(FeatureEligibilityError, match=error):
        require_pre_match_eligibility(evidence(**changes), prediction_cutoff_at=CUTOFF)


def test_naive_cutoff_is_rejected() -> None:
    with pytest.raises(FeatureEligibilityError, match="PREDICTION_CUTOFF_AT_MUST_BE_TIMEZONE_AWARE"):
        require_pre_match_eligibility(
            evidence(), prediction_cutoff_at=datetime(2026, 11, 16, 12, 0)
        )


def test_event_time_or_kickoff_cannot_replace_publication_evidence() -> None:
    with pytest.raises(FeatureEligibilityError, match="VERIFIED_SOURCE_PUBLICATION_TIME_REQUIRED"):
        require_pre_match_eligibility(
            evidence(availability_basis="SOURCE_EVENT_TIME"),
            prediction_cutoff_at=CUTOFF,
        )
