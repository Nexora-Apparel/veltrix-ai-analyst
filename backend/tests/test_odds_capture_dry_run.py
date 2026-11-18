from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json

import pytest

from app.providers.approvals import FIVEDOLLAR_COMMUNITY_ODDS_APPROVAL
from app.providers.odds_capture_dry_run import (
    CaptureExpectation,
    validate_manual_capture,
)
from app.providers.odds_capture_manifest import (
    ProspectiveOddsCaptureManifest,
    deterministic_capture_identity,
)

REQUEST = datetime(2026, 11, 18, 11, 55, tzinfo=UTC)
TICK = REQUEST + timedelta(seconds=1)
RETRIEVED = REQUEST + timedelta(minutes=1)
CUTOFF = REQUEST + timedelta(minutes=5)
KICKOFF = CUTOFF + timedelta(hours=2)


def response_bytes():
    payload = {
        "success": 1,
        "data": {
            "fixture_id": "provider-fx-1",
            "bookmakers": [{
                "name": "Bet 365",
                "slug": "bet365",
                "odds": {"1x2": {"opening": {
                    "home": 1.9,
                    "draw": 3.5,
                    "away": 3.9,
                    "opened_at": TICK.isoformat(),
                }}},
            }],
        },
    }
    return json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()


def expected(**overrides):
    values = {
        "provider": "5DollarFootballAPI",
        "provider_event_id": "provider-event-1",
        "provider_fixture_id": "provider-fx-1",
        "canonical_fixture_id": "canonical-fx-1",
        "competition_id": "522514093",
        "bookmaker_slug": "bet365",
        "market_key": "1x2",
        "kickoff_at": KICKOFF,
        "value_bet_decision_cutoff_at": CUTOFF,
    }
    values.update(overrides)
    return CaptureExpectation(**values)


def manifest(raw=None, **overrides):
    raw = raw if raw is not None else response_bytes()
    identity = deterministic_capture_identity(
        provider="5DollarFootballAPI",
        provider_event_id="provider-event-1",
        provider_fixture_id="provider-fx-1",
        canonical_fixture_id="canonical-fx-1",
        competition_id="522514093",
        request_started_at=REQUEST,
    )
    values = {
        "capture_identity": identity,
        "provider": "5DollarFootballAPI",
        "provider_event_id": "provider-event-1",
        "provider_fixture_id": "provider-fx-1",
        "canonical_fixture_id": "canonical-fx-1",
        "competition_id": "522514093",
        "bookmaker_slug": "bet365",
        "market_key": "1x2",
        "request_started_at": REQUEST,
        "retrieved_at": RETRIEVED,
        "provider_response_date": RETRIEVED,
        "source_tick_min_at": TICK,
        "source_tick_max_at": TICK,
        "value_bet_decision_cutoff_at": CUTOFF,
        "fixture_kickoff_at": KICKOFF,
        "http_status": 200,
        "response_bytes": len(raw),
        "response_sha256": sha256(raw).hexdigest(),
        "rights_approval_id": FIVEDOLLAR_COMMUNITY_ODDS_APPROVAL.approval_id,
        "observation_count": 3,
        "admission": "ELIGIBLE",
        "rejection_reason": None,
    }
    values.update(overrides)
    return ProspectiveOddsCaptureManifest(**values)


def test_manual_dry_run_accepts_exact_eligible_capture():
    raw = response_bytes()
    result = validate_manual_capture(raw, manifest(raw), expected())
    assert result.accepted is True
    assert result.reason_codes == ()
    assert result.observation_count == 3
    assert result.response_bytes == len(raw)


@pytest.mark.parametrize(
    ("raw_change", "expected_reason"),
    [
        (b" ", "RESPONSE_BYTE_COUNT_MISMATCH"),
        (b'{"success":1,"success":1}', "RESPONSE_BYTE_COUNT_MISMATCH"),
    ],
)
def test_manual_dry_run_rejects_byte_or_hash_mismatch(raw_change, expected_reason):
    raw = response_bytes()
    result = validate_manual_capture(raw_change, manifest(raw), expected())
    assert result.accepted is False
    assert expected_reason in result.reason_codes
    assert "RESPONSE_SHA256_MISMATCH" in result.reason_codes


def test_manual_dry_run_rejects_duplicate_json_keys():
    raw = b'{"success":1,"data":{"fixture_id":"x"},"data":{}}'
    result = validate_manual_capture(raw, manifest(raw), expected())
    assert result.accepted is False
    assert "JSON_DUPLICATE_OBJECT_KEY" in result.reason_codes


def test_manual_dry_run_rejects_non_finite_json_numbers():
    raw = b'{"success":1,"data":{"fixture_id":"provider-fx-1","x":NaN}}'
    result = validate_manual_capture(raw, manifest(raw), expected())
    assert result.accepted is False
    assert "JSON_NON_FINITE_NUMBER" in result.reason_codes


def test_manual_dry_run_rejects_fixture_identity_mismatch():
    raw = response_bytes()
    altered = raw.replace(b"provider-fx-1", b"provider-fx-2")
    result = validate_manual_capture(altered, manifest(altered), expected())
    assert result.accepted is False
    assert "PROVIDER_FIXTURE_ID_MISMATCH" in result.reason_codes


def test_manual_dry_run_rejects_unapproved_competition_scope():
    raw = response_bytes()
    result = validate_manual_capture(
        raw,
        manifest(raw),
        expected(competition_id="unapproved-competition"),
    )
    assert result.accepted is False
    assert "MANIFEST_CONTEXT_MISMATCH:competition_id" in result.reason_codes
    assert "RIGHTS_NOT_APPROVED" in result.reason_codes


def test_manual_dry_run_rejects_context_mismatch():
    raw = response_bytes()
    result = validate_manual_capture(
        raw, manifest(raw), expected(canonical_fixture_id="other-canonical-id")
    )
    assert result.accepted is False
    assert "MANIFEST_CONTEXT_MISMATCH:canonical_fixture_id" in result.reason_codes


def test_manual_dry_run_rejects_wrong_market_scope():
    raw = response_bytes()
    result = validate_manual_capture(
        raw, manifest(raw), expected(market_key="btts")
    )
    assert result.accepted is False
    assert "MANIFEST_CONTEXT_MISMATCH:market_key" in result.reason_codes


def test_manual_dry_run_rejects_non_eligible_manifest():
    raw = response_bytes()
    rejected = manifest(
        raw,
        admission="REJECTED",
        rejection_reason="MANUAL_REJECTION",
    )
    result = validate_manual_capture(raw, rejected, expected())
    assert result.accepted is False
    assert "MANIFEST_NOT_ELIGIBLE" in result.reason_codes


def test_expectation_rejects_naive_timestamps():
    with pytest.raises(ValueError, match="timezone-aware"):
        expected(kickoff_at=datetime(2026, 11, 18, 14))
