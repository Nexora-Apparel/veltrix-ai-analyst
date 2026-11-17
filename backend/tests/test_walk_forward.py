from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.validation.walk_forward import (
    EvaluationFixture,
    multiclass_brier_score,
    multiclass_log_loss,
    walk_forward_splits,
)


def fixture(
    fixture_id: str,
    day: int,
    *,
    minute: int = 0,
    label_delay_minutes: int = 30,
    identity_verified: bool = True,
    duplicate_excluded: bool = True,
    rights_approved: bool = True,
    pit_eligible: bool = True,
    feature_delay_minutes: int = -90,
) -> EvaluationFixture:
    kickoff = datetime(2026, 1, day, 15, minute, tzinfo=UTC)
    cutoff = kickoff - timedelta(hours=1)
    return EvaluationFixture(
        fixture_id=fixture_id,
        kickoff_at=kickoff,
        prediction_cutoff_at=cutoff,
        features_available_at=cutoff + timedelta(minutes=feature_delay_minutes),
        label_available_at=kickoff + timedelta(minutes=label_delay_minutes),
        home_goals=1,
        away_goals=0,
        identity_verified=identity_verified,
        duplicate_excluded=duplicate_excluded,
        rights_approved=rights_approved,
        pit_eligible=pit_eligible,
    )


def test_walk_forward_is_chronological_and_uses_only_available_labels() -> None:
    rows = [fixture(f"f{i}", i + 1) for i in range(8)]
    # One old result is not published until after the second test cutoff.
    rows[1] = fixture("f1", 2, label_delay_minutes=24 * 60)
    folds = walk_forward_splits(rows, min_train_fixtures=2, test_window_fixtures=2)
    assert folds
    for fold in folds:
        assert set(fold.train_fixture_ids).isdisjoint(fold.test_fixture_ids)
        assert len(fold.train_fixture_ids) >= 2
        assert "f1" not in fold.train_fixture_ids
        assert fold.train_label_cutoff_at < fold.test_start_at


def test_simultaneous_fixtures_stay_in_same_test_block() -> None:
    rows = [fixture("a", 1), fixture("b", 1, minute=0), *[fixture(f"f{i}", i) for i in range(2, 8)]]
    folds = walk_forward_splits(rows, min_train_fixtures=2, test_window_fixtures=1)
    assert folds
    assert all(not ({"a", "b"} & set(fold.test_fixture_ids)) for fold in folds)
    assert all(not ({"a", "b"} <= set(fold.train_fixture_ids)) for fold in folds)


def test_unverified_duplicate_or_non_pit_rows_are_excluded() -> None:
    rows = [fixture(f"f{i}", i + 1) for i in range(8)]
    rows.append(fixture("bad-identity", 2, identity_verified=False))
    rows.append(fixture("duplicate", 3, duplicate_excluded=False))
    rows.append(fixture("no-pit", 4, pit_eligible=False))
    folds = walk_forward_splits(rows, min_train_fixtures=2, test_window_fixtures=2)
    for fold in folds:
        assert "bad-identity" not in fold.train_fixture_ids + fold.test_fixture_ids
        assert "duplicate" not in fold.train_fixture_ids + fold.test_fixture_ids
        assert "no-pit" not in fold.train_fixture_ids + fold.test_fixture_ids


def test_embargo_excludes_recently_available_labels() -> None:
    rows = [fixture(f"f{i}", i + 1, label_delay_minutes=120) for i in range(8)]
    folds = walk_forward_splits(rows, min_train_fixtures=2, test_window_fixtures=1, embargo=timedelta(hours=22))
    assert folds
    assert all("f3" not in fold.train_fixture_ids for fold in folds if fold.test_start_at.day == 5)


def test_duplicate_fixture_ids_are_rejected() -> None:
    row = fixture("same", 1)
    with pytest.raises(ValueError, match="duplicate fixture IDs"):
        walk_forward_splits([row, row], min_train_fixtures=1, test_window_fixtures=1)


def test_multiclass_proper_scores() -> None:
    actual = [0, 2]
    predictions = [[0.7, 0.2, 0.1], [0.1, 0.2, 0.7]]
    assert multiclass_brier_score(actual, predictions) == pytest.approx(0.14)
    assert multiclass_log_loss(actual, predictions) == pytest.approx(0.3566749439)


def test_metrics_reject_probabilities_that_do_not_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to one"):
        multiclass_brier_score([0], [[0.5, 0.2]])
