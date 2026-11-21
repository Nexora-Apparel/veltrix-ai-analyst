from datetime import UTC, datetime, timedelta

from app.research.shrinkage_repair_evaluation import _folds


def _row(fixture_id: str, kickoff: datetime, observed_at: datetime) -> dict:
    return {
        "fixture_id": fixture_id,
        "canonical_competition_id": "league",
        "competition_id": "league",
        "canonical_fixture_id": fixture_id,
        "home_team_id": f"home-{fixture_id}",
        "away_team_id": f"away-{fixture_id}",
        "kickoff_at": kickoff.isoformat(),
        "label_observed_at": observed_at.isoformat(),
        "label": {"home_goals": 1, "away_goals": 0},
    }


def test_retrospective_availability_uses_kickoff_plus_three_hours_not_ingestion_time():
    start = datetime(2026, 1, 1, 12, tzinfo=UTC)
    bulk_ingestion = datetime(2026, 11, 16, 22, tzinfo=UTC)
    rows = [
        _row(f"day-{index}", start + timedelta(days=index), bulk_ingestion)
        for index in range(30)
    ]
    # The last result before the fold cutoff has not reached the three-hour
    # full-time proxy and must be excluded, despite its kickoff being earlier.
    near_cutoff = datetime(2026, 1, 18, 23, 30, tzinfo=UTC)
    rows.append(_row("late-prior-day", near_cutoff, bulk_ingestion))
    # Establish an early cutoff on the next day.
    early_test = datetime(2026, 1, 19, 0, 30, tzinfo=UTC)
    rows.append(_row("first-test", early_test, bulk_ingestion))

    folds = _folds(rows)
    fold_one = folds[0]
    cutoff = fold_one["cutoff"]
    training_ids = {row["fixture_id"] for row in fold_one["train"]}

    assert "late-prior-day" not in training_ids
    assert "day-0" in training_ids
    assert all(
        datetime.fromisoformat(row["kickoff_at"]) + timedelta(hours=3) < cutoff
        for row in fold_one["train"]
    )
    # Bulk ingestion timestamps are deliberately after the historical cutoff;
    # they must not be used to reject otherwise eligible historical outcomes.
    assert all(
        datetime.fromisoformat(row["label_observed_at"]) > cutoff
        for row in fold_one["train"]
    )
