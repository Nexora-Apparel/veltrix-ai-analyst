from datetime import UTC, datetime, timedelta

import pytest

from app.models.attack_defence import GoalResult
from app.validation.retrospective import evaluate_retrospective

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def make_rows(count=24):
    teams = ("A", "B", "C", "D")
    rows = []
    for day in range(count):
        home = teams[day % 4]
        away = teams[(day + 1) % 4]
        rows.append(GoalResult(
            fixture_id=f"fx-{day}",
            kickoff_at=BASE + timedelta(days=day),
            home_team=home,
            away_team=away,
            home_goals=2 if day % 3 else 0,
            away_goals=0 if day % 3 else 1,
        ))
    return rows


def test_retrospective_evaluation_uses_only_prior_event_time_results():
    report = evaluate_retrospective(
        make_rows(), min_train_fixtures=8, test_window_fixtures=4
    )
    assert report.evaluation_type == "RETROSPECTIVE_EVENT_TIME_NOT_PIT_CERTIFIED"
    assert report.evaluated_fixtures > 0
    assert report.fold_count > 0
    assert 0 <= report.brier_1x2 <= 2
    assert report.log_loss_1x2 > 0


def test_simultaneous_kickoff_batch_never_splits_between_train_and_test():
    rows = make_rows(12)
    rows[1] = GoalResult(
        fixture_id="fx-same-time",
        kickoff_at=rows[0].kickoff_at,
        home_team="C",
        away_team="D",
        home_goals=1,
        away_goals=0,
    )
    report = evaluate_retrospective(rows, min_train_fixtures=4, test_window_fixtures=2)
    assert report.evaluated_fixtures + report.excluded_initial_fixtures == len(rows)


def test_rejects_duplicate_fixture_ids():
    rows = make_rows(12)
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_retrospective(rows + [rows[0]], min_train_fixtures=4)
