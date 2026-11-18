from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.validation.source_provenance import is_valid_retrospective_observation


@pytest.fixture
def captured_observation():
    retrieved = datetime(2026, 11, 18, 14, 9, 34, tzinfo=UTC)
    return {
        "availability_basis": "RETRIEVED_AT_ONLY",
        "point_in_time_certifiable": False,
        "retrieved_at": retrieved,
        "source_published_at": None,
        "available_at": retrieved,
        "system_observed_at": None,
        "provider_response_id": "response-1",
        "http_status": 200,
    }


def test_capture_timestamp_mirrored_in_available_at_is_valid_retrospective_evidence(
    captured_observation,
):
    assert is_valid_retrospective_observation(captured_observation)


def test_missing_available_at_is_allowed_when_basis_is_retrieval_only(captured_observation):
    captured_observation["available_at"] = None
    assert is_valid_retrospective_observation(captured_observation)


@pytest.mark.parametrize(
    "field,value",
    [
        ("point_in_time_certifiable", True),
        ("availability_basis", "UNVERIFIED"),
        ("source_published_at", datetime(2026, 11, 18, 13, tzinfo=UTC)),
        ("available_at", datetime(2026, 11, 18, 14, 9, 33, tzinfo=UTC)),
        ("available_at", datetime(2026, 11, 18, 14, 9, 35, tzinfo=UTC)),
        ("retrieved_at", None),
        ("provider_response_id", None),
        ("http_status", 503),
        ("http_status", None),
    ],
)
def test_invalid_or_ambiguous_provenance_is_rejected(captured_observation, field, value):
    captured_observation[field] = value
    assert not is_valid_retrospective_observation(captured_observation)


def test_boolean_http_status_is_not_accepted(captured_observation):
    captured_observation["http_status"] = True
    assert not is_valid_retrospective_observation(captured_observation)



def test_database_observed_capture_is_valid_retrospective_label_evidence(
    captured_observation,
):
    observed = captured_observation["retrieved_at"].replace(microsecond=100000)
    captured_observation.update(
        availability_basis="SYSTEM_OBSERVED_AT",
        point_in_time_certifiable=True,
        system_observed_at=observed,
        available_at=observed,
    )
    assert is_valid_retrospective_observation(captured_observation)


def test_system_observed_capture_before_retrieval_is_rejected(captured_observation):
    captured_observation.update(
        availability_basis="SYSTEM_OBSERVED_AT",
        point_in_time_certifiable=True,
        system_observed_at=captured_observation["retrieved_at"] - timedelta(microseconds=1),
        available_at=captured_observation["retrieved_at"] - timedelta(microseconds=1),
    )
    assert not is_valid_retrospective_observation(captured_observation)
