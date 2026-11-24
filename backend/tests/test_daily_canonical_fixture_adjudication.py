from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.canonical_fixture_adjudication import (
    COLLISION_WINDOW_SECONDS,
    POLICY_VERSION,
    REVIEWED_MAPPING_STATUSES,
    REVIEWER_ID,
    evidence_sha256,
    exact_fixture_link_decision,
    find_fixture_link_collisions,
)


def _row(
    link_id: int,
    *,
    competition: str = "competition-a",
    home: str = "team-home",
    away: str = "team-away",
    kickoff: datetime | None = None,
) -> dict:
    return {
        "link_id": link_id,
        "canonical_competition_id": competition,
        "home_canonical_team_id": home,
        "away_canonical_team_id": away,
        "kickoff_at": kickoff or datetime(2026, 11, 24, 12, tzinfo=UTC),
    }


def test_exact_canonical_pair_within_two_minutes_is_flagged_as_collision() -> None:
    first = _row(1)
    second = _row(
        2,
        kickoff=first["kickoff_at"] + timedelta(seconds=COLLISION_WINDOW_SECONDS),
    )
    assert find_fixture_link_collisions([first, second]) == {1: (2,), 2: (1,)}


@pytest.mark.parametrize(
    "second",
    [
        _row(2, competition="competition-b"),
        _row(2, home="different-home"),
        _row(2, away="different-away"),
        _row(2, home="team-away", away="team-home"),
        _row(2, kickoff=datetime(2026, 11, 24, 12, 2, 1, tzinfo=UTC)),
    ],
)
def test_different_identity_or_kickoff_outside_window_is_not_a_collision(second) -> None:
    assert find_fixture_link_collisions([_row(1), second]) == {}


def test_collision_detection_is_order_independent_and_does_not_merge_rows() -> None:
    first = _row(10)
    second = _row(11, kickoff=first["kickoff_at"] + timedelta(seconds=45))
    assert find_fixture_link_collisions([second, first]) == {10: (11,), 11: (10,)}


def test_duplicate_link_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate fixture source link IDs"):
        find_fixture_link_collisions([_row(1), _row(1)])


def test_naive_kickoff_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        find_fixture_link_collisions([
            _row(1, kickoff=datetime(2026, 11, 24, 12))
        ])


def test_evidence_hash_is_stable_and_changes_when_source_identity_changes() -> None:
    evidence = {
        "policy_version": POLICY_VERSION,
        "provider_fixture_id": "fixture-1",
        "source_observation_id": 101,
        "kickoff_at": datetime(2026, 11, 24, 12, tzinfo=UTC),
    }
    first = evidence_sha256(evidence)
    assert first == evidence_sha256(dict(reversed(list(evidence.items()))))
    assert len(first) == 64
    assert first != evidence_sha256({**evidence, "source_observation_id": 102})


def test_policy_uses_explicit_non_human_reviewer_and_only_reviewed_identity_states() -> None:
    assert REVIEWER_ID == "VELTRIX_EXACT_PROVIDER_FIXTURE_LINK_ADJUDICATION_V1"
    assert REVIEWED_MAPPING_STATUSES == {
        "SOURCE_IDENTITY_REVIEWED",
        "REAL_WORLD_IDENTITY_VERIFIED",
    }


def test_evidence_hash_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        evidence_sha256({"kickoff_at": datetime(2026, 11, 24, 12)})



@pytest.mark.parametrize(
    ("identity_status", "collision_ids", "mappings_reviewed", "expected"),
    [
        ("IDENTITY_REVIEW_REQUIRED", (), True, "SOURCE_FIXTURE_LINK_REVIEWED"),
        ("IDENTITY_REVIEW_REQUIRED", (99,), True, "CONFLICT"),
        ("IDENTITY_REVIEW_REQUIRED", (), False, None),
        ("IDENTITY_REVIEW_REQUIRED", (99,), False, None),
        ("CONFLICT", (), False, "CONFLICT"),
        ("CONFLICT", (99,), True, "CONFLICT"),
    ],
)
def test_exact_fixture_link_decision_is_fail_closed(
    identity_status, collision_ids, mappings_reviewed, expected
) -> None:
    assert exact_fixture_link_decision(
        identity_status=identity_status,
        collision_link_ids=collision_ids,
        mappings_reviewed=mappings_reviewed,
    ) == expected
