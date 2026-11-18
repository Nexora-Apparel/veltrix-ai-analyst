from datetime import UTC, datetime, timedelta

import pytest

from app.validation.prospective_evidence import (
    FixtureIdentity,
    ProspectiveEvidence,
    hash_raw_payload,
)


KICKOFF = datetime(2026, 11, 20, 18, 0, tzinfo=UTC)


def fixture() -> FixtureIdentity:
    return FixtureIdentity(
        provider="5DollarFootballAPI",
        source_id="5dollarfootballapi",
        provider_competition_id="league-1",
        provider_fixture_id="fixture-9",
        home_team_provider_id="team-home",
        away_team_provider_id="team-away",
        kickoff_at=KICKOFF,
    )


def evidence(observed_at: datetime) -> ProspectiveEvidence:
    return ProspectiveEvidence(
        fixture=fixture(),
        provider_response_id="response-123",
        retrieved_at=observed_at + timedelta(milliseconds=20),
        system_observed_at=observed_at,
        raw_payload_sha256=hash_raw_payload(b'{"fixture":"fixture-9"}'),
    )


def test_database_observation_before_kickoff_is_pit_eligible():
    row = evidence(KICKOFF - timedelta(minutes=1))
    assert row.point_in_time_certifiable is True
    assert row.availability_basis == "SYSTEM_OBSERVED_AT"


def test_observation_at_kickoff_is_not_pre_match():
    row = evidence(KICKOFF)
    assert row.point_in_time_certifiable is False


def test_observation_after_kickoff_is_not_pre_match():
    row = evidence(KICKOFF + timedelta(seconds=1))
    assert row.point_in_time_certifiable is False


def test_retrieval_timestamp_does_not_override_database_observation():
    observed = KICKOFF - timedelta(minutes=2)
    row = evidence(observed)
    assert row.retrieved_at > row.system_observed_at
    assert row.point_in_time_certifiable is True


def test_source_publication_must_be_explicit_and_not_in_future():
    with pytest.raises(ValueError, match="source_published_at"):
        ProspectiveEvidence(
            fixture=fixture(),
            provider_response_id="response-123",
            retrieved_at=KICKOFF - timedelta(minutes=1),
            system_observed_at=KICKOFF - timedelta(minutes=2),
            raw_payload_sha256="a" * 64,
            source_published_at=KICKOFF,
        )


def test_payload_hash_is_exact_sha256_of_raw_bytes():
    assert hash_raw_payload(b"raw") == "d7439bee24773bcbfa2d0a97947ee36227b10d1022b1a55847e928965bb6bfde"
