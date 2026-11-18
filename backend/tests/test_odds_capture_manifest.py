from datetime import UTC, datetime, timedelta

import pytest

from app.providers.odds_capture_manifest import (
    ProspectiveOddsCaptureManifest,
    deterministic_capture_identity,
)

START = datetime(2026, 11, 18, 12, tzinfo=UTC)
RETRIEVED = START + timedelta(seconds=2)
CUTOFF = START + timedelta(minutes=1)
KICKOFF = CUTOFF + timedelta(hours=2)
DIGEST = "a" * 64


def identity(**overrides):
    values = {
        "provider": "5DollarFootballAPI",
        "provider_event_id": "event-1",
        "provider_fixture_id": "provider-fx-1",
        "canonical_fixture_id": "canonical-fx-1",
        "competition_id": "522514093",
        "request_started_at": START,
    }
    values.update(overrides)
    return deterministic_capture_identity(**values)


def manifest(**overrides):
    values = {
        "capture_identity": identity(),
        "provider": "5DollarFootballAPI",
        "provider_event_id": "event-1",
        "provider_fixture_id": "provider-fx-1",
        "canonical_fixture_id": "canonical-fx-1",
        "competition_id": "522514093",
        "bookmaker_slug": "bet365",
        "market_key": "1x2",
        "request_started_at": START,
        "retrieved_at": RETRIEVED,
        "provider_response_date": RETRIEVED,
        "value_bet_decision_cutoff_at": CUTOFF,
        "fixture_kickoff_at": KICKOFF,
        "http_status": 200,
        "response_bytes": 2282,
        "response_sha256": DIGEST,
        "rights_approval_id": "approval-odds-1",
        "observation_count": 3,
        "admission": "ELIGIBLE",
        "rejection_reason": None,
    }
    values.update(overrides)
    return ProspectiveOddsCaptureManifest(**values)


def test_manifest_accepts_one_eligible_prospective_capture():
    result = manifest()
    assert result.admission == "ELIGIBLE"
    assert result.observation_count == 3
    assert result.provider_response_date == RETRIEVED


def test_capture_identity_is_deterministic_and_fixture_scoped():
    assert identity() == identity()
    assert identity() != identity(provider_fixture_id="another-fixture")
    assert identity() != identity(request_started_at=START + timedelta(seconds=1))


def test_manifest_rejects_retrieval_after_value_bet_cutoff():
    with pytest.raises(ValueError, match="after the decision cutoff"):
        manifest(retrieved_at=CUTOFF + timedelta(seconds=1))


def test_manifest_rejects_non_200_as_eligible():
    with pytest.raises(ValueError, match="requires HTTP 200"):
        manifest(http_status=206)


def test_manifest_rejects_empty_capture_as_eligible():
    with pytest.raises(ValueError, match="non-empty response and observations"):
        manifest(response_bytes=0, observation_count=0)


def test_manifest_rejects_decision_cutoff_at_or_after_kickoff():
    with pytest.raises(ValueError, match="must precede kickoff"):
        manifest(value_bet_decision_cutoff_at=KICKOFF)


def test_rejected_manifest_requires_explicit_reason():
    with pytest.raises(ValueError, match="explicit rejection reason"):
        manifest(admission="REJECTED", rejection_reason=None)


def test_rejected_manifest_can_record_provider_failure_without_observations():
    result = manifest(
        http_status=429,
        response_bytes=0,
        observation_count=0,
        admission="REJECTED",
        rejection_reason="PROVIDER_RATE_LIMIT",
    )
    assert result.admission == "REJECTED"
    assert result.rejection_reason == "PROVIDER_RATE_LIMIT"


def test_manifest_rejects_naive_timestamps():
    with pytest.raises(ValueError, match="timezone-aware"):
        manifest(request_started_at=datetime(2026, 11, 18, 12))
