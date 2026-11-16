from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.providers.contracts import ProviderFixture, SourceProvenance


def valid_provenance() -> dict[str, object]:
    return {
        "provider": "sample-provider",
        "provider_record_id": "fixture-123",
        "retrieved_at": datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc),
    }


def valid_fixture() -> dict[str, object]:
    return {
        "provenance": valid_provenance(),
        "competition_id": "competition-1",
        "season_id": "2026",
        "home_team_id": "team-home",
        "away_team_id": "team-away",
        "kickoff_at": datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc),
        "status": "scheduled",
    }


def test_source_provenance_requires_timezone_aware_retrieval_time() -> None:
    data = valid_provenance()
    data["retrieved_at"] = datetime(2026, 11, 16, 12, 0)

    with pytest.raises(ValidationError):
        SourceProvenance.model_validate(data)


def test_fixture_accepts_valid_normalized_record() -> None:
    fixture = ProviderFixture.model_validate(valid_fixture())

    assert fixture.home_team_id == "team-home"
    assert fixture.away_team_id == "team-away"
    assert fixture.provenance.provider == "sample-provider"


def test_fixture_rejects_naive_kickoff_timestamp() -> None:
    data = valid_fixture()
    data["kickoff_at"] = datetime(2026, 11, 17, 15, 0)

    with pytest.raises(ValidationError):
        ProviderFixture.model_validate(data)


def test_fixture_rejects_same_home_and_away_team() -> None:
    data = valid_fixture()
    data["away_team_id"] = data["home_team_id"]

    with pytest.raises(ValidationError):
        ProviderFixture.model_validate(data)


def test_fixture_rejects_unexpected_fields() -> None:
    data = valid_fixture()
    data["unverified_prediction"] = 0.91

    with pytest.raises(ValidationError):
        ProviderFixture.model_validate(data)
