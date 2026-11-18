from datetime import UTC, datetime

import pytest

from app.providers.fixture_catalogue import (
    FixtureCatalogueError,
    normalize_scheduled_fixture_catalogue,
)

AS_OF = datetime(2026, 11, 18, tzinfo=UTC)


def fixture(**overrides):
    row = {
        "id": 12345,
        "league": {"id": 4160026622, "name": "Premier League"},
        "teams": {
            "home": {"id": 1, "name": "Arsenal"},
            "away": {"id": 2, "name": "Chelsea"},
        },
        "kickoff_utc": "2026-11-20T19:00:00+00:00",
        "status": "scheduled",
    }
    row.update(overrides)
    return row


def payload(rows=None, has_more=False):
    return {
        "success": 1,
        "data": [fixture()] if rows is None else rows,
        "pagination": {"page": 1, "per_page": 100, "has_more": has_more},
    }


def test_normalizes_future_scheduled_fixture():
    fixtures, has_more, excluded = normalize_scheduled_fixture_catalogue(
        payload(), competition_id="4160026622", as_of=AS_OF
    )
    assert len(fixtures) == 1
    assert fixtures[0]["provider_fixture_id"] == "12345"
    assert fixtures[0]["home_team"] == "Arsenal"
    assert fixtures[0]["away_team"] == "Chelsea"
    assert has_more is False
    assert excluded == 0


def test_excludes_nonfuture_kickoff_and_preserves_truncation_flag():
    fixtures, has_more, excluded = normalize_scheduled_fixture_catalogue(
        payload([fixture(kickoff_utc="2026-11-17T19:00:00Z")], has_more=True),
        competition_id="4160026622",
        as_of=AS_OF,
    )
    assert fixtures == ()
    assert has_more is True
    assert excluded == 1


def test_rejects_competition_mismatch_and_unexpected_status():
    with pytest.raises(FixtureCatalogueError, match="COMPETITION_MISMATCH"):
        normalize_scheduled_fixture_catalogue(
            payload([fixture(league={"id": 522514093, "name": "Serie B"})]),
            competition_id="4160026622",
            as_of=AS_OF,
        )
    with pytest.raises(FixtureCatalogueError, match="UNEXPECTED_FIXTURE_STATUS"):
        normalize_scheduled_fixture_catalogue(
            payload([fixture(status="finished")]),
            competition_id="4160026622",
            as_of=AS_OF,
        )


def test_rejects_duplicate_ids_missing_pagination_and_naive_timestamps():
    with pytest.raises(FixtureCatalogueError, match="DUPLICATE"):
        normalize_scheduled_fixture_catalogue(
            payload([fixture(), fixture()]),
            competition_id="4160026622",
            as_of=AS_OF,
        )
    with pytest.raises(FixtureCatalogueError, match="PAGINATION"):
        normalize_scheduled_fixture_catalogue(
            {"success": 1, "data": []},
            competition_id="4160026622",
            as_of=AS_OF,
        )
    with pytest.raises(FixtureCatalogueError, match="TIMEZONE_AWARE"):
        normalize_scheduled_fixture_catalogue(
            payload([fixture(kickoff_utc="2026-11-20T19:00:00")]),
            competition_id="4160026622",
            as_of=AS_OF,
        )


def test_rejects_naive_as_of_and_unsuccessful_payload():
    with pytest.raises(FixtureCatalogueError, match="AS_OF"):
        normalize_scheduled_fixture_catalogue(
            payload(),
            competition_id="4160026622",
            as_of=datetime(2026, 11, 18),
        )
    with pytest.raises(FixtureCatalogueError, match="UNSUCCESSFUL"):
        normalize_scheduled_fixture_catalogue(
            {"success": 0, "data": []},
            competition_id="4160026622",
            as_of=AS_OF,
        )
