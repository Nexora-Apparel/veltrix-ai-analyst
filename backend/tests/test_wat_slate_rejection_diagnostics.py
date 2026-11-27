from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from scripts.validate_stage7_wat_daily_slate import rejection_diagnostics


def _row(**overrides):
    generated = datetime(2026, 11, 27, 10, 0, tzinfo=UTC)
    values = {
        "validation_eligible": True,
        "label": None,
        "prediction_cutoff_at": generated - timedelta(minutes=30),
        "canonical_fixture_id": "canonical-fixture",
        "canonical_competition_id": "canonical-competition",
        "kickoff_at": generated + timedelta(hours=2),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_rejection_diagnostics_counts_first_failure_without_double_counting():
    generated = datetime(2026, 11, 27, 10, 0, tzinfo=UTC)
    rows = (
        _row(validation_eligible=False),
        _row(label={"home_goals": 1, "away_goals": 0}),
        _row(prediction_cutoff_at=None),
        _row(canonical_fixture_id=None),
        _row(prediction_cutoff_at=generated + timedelta(minutes=1)),
        _row(prediction_cutoff_at=generated + timedelta(hours=3)),
        _row(kickoff_at=generated - timedelta(minutes=1)),
        _row(kickoff_at=datetime(2026, 11, 27, 22, 30, tzinfo=UTC)),
        _row(prediction_cutoff_at=generated - timedelta(hours=7)),
        _row(),
    )
    result = rejection_diagnostics(
        rows, generated=generated, max_snapshot_age_hours=6.0
    )
    counts = result["mutually_exclusive_first_failure_counts"]
    assert result["rows_considered"] == 10
    assert sum(counts.values()) == 10
    assert counts == {
        "not_validation_eligible": 1,
        "already_labelled": 1,
        "missing_prediction_cutoff": 1,
        "missing_canonical_identity": 1,
        "cutoff_in_future": 1,
        "cutoff_not_before_kickoff": 1,
        "kickoff_not_upcoming": 1,
        "outside_current_wat_day": 1,
        "snapshot_stale_over_limit": 1,
        "eligible_before_daily_cap": 1,
    }


def test_rejection_diagnostics_distinguishes_stale_from_non_today_rows():
    generated = datetime(2026, 11, 27, 10, 0, tzinfo=UTC)
    stale = _row(prediction_cutoff_at=generated - timedelta(hours=6, minutes=1))
    tomorrow = _row(kickoff_at=datetime(2026, 11, 27, 23, 30, tzinfo=UTC))
    result = rejection_diagnostics(
        (stale, tomorrow), generated=generated, max_snapshot_age_hours=6.0
    )
    counts = result["mutually_exclusive_first_failure_counts"]
    assert counts["snapshot_stale_over_limit"] == 1
    assert counts["outside_current_wat_day"] == 1
    assert result["eligible_before_daily_cap"] == 0
