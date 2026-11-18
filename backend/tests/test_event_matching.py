from datetime import UTC, datetime, timedelta

import pytest

from app.providers.event_matching import (
    match_event_to_fixture,
    normalize_team_name,
)


EVENT = {
    "event_id": "odds-event-1",
    "home_team": "São Paulo FC",
    "away_team": "Palmeiras",
    "commence_time": "2026-11-20T19:00:00Z",
}
FIXTURE = {
    "provider_fixture_id": "5dollar-fixture-1",
    "home_team": "Sao Paulo FC",
    "away_team": "Palmeiras",
    "kickoff_at": "2026-11-20T19:03:00+00:00",
}


def test_normalizes_accents_and_punctuation_without_alias_guessing():
    assert normalize_team_name("São Paulo FC") == "sao paulo fc"
    assert normalize_team_name("A.F.C. Example") == "a f c example"
    assert normalize_team_name("Example United") != normalize_team_name("Example Utd")


def test_matches_exact_home_away_and_kickoff_within_tolerance():
    result = match_event_to_fixture(EVENT, [FIXTURE])
    assert result.status == "MATCHED"
    assert result.fixture_id == "5dollar-fixture-1"
    assert result.kickoff_delta_seconds == 180


def test_rejects_reversed_home_and_away():
    reversed_fixture = {
        **FIXTURE,
        "home_team": "Palmeiras",
        "away_team": "Sao Paulo FC",
    }
    result = match_event_to_fixture(EVENT, [reversed_fixture])
    assert result.status == "NO_TEAM_MATCH"
    assert result.fixture_id is None


def test_rejects_kickoff_outside_tolerance():
    late_fixture = {
        **FIXTURE,
        "kickoff_at": "2026-11-20T19:30:00Z",
    }
    result = match_event_to_fixture(EVENT, [late_fixture])
    assert result.status == "KICKOFF_OUTSIDE_TOLERANCE"
    assert result.fixture_id is None
    assert result.kickoff_delta_seconds == 1800


def test_rejects_ambiguous_duplicate_fixture_candidates():
    duplicate = {**FIXTURE, "provider_fixture_id": "5dollar-fixture-2"}
    result = match_event_to_fixture(EVENT, [FIXTURE, duplicate])
    assert result.status == "AMBIGUOUS"
    assert result.fixture_id is None
    assert result.candidate_fixture_ids == (
        "5dollar-fixture-1",
        "5dollar-fixture-2",
    )


def test_rejects_naive_timestamps_and_invalid_tolerance():
    naive_fixture = {**FIXTURE, "kickoff_at": "2026-11-20T19:03:00"}
    with pytest.raises(ValueError, match="TIMEZONE_AWARE"):
        match_event_to_fixture(EVENT, [naive_fixture])
    with pytest.raises(ValueError, match="POSITIVE"):
        match_event_to_fixture(
            EVENT, [FIXTURE], kickoff_tolerance=timedelta(0)
        )
    with pytest.raises(ValueError, match="TIMEZONE_AWARE"):
        match_event_to_fixture(
            {**EVENT, "commence_time": datetime(2026, 11, 20, 19)},
            [FIXTURE],
        )
