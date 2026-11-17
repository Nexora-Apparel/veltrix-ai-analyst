from app.validation.calibration import multiclass_calibration_diagnostics
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
    assert len(report.fold_metrics) == report.fold_count
    assert sum(row.fixture_count for row in report.fold_metrics) == report.evaluated_fixtures
    assert all(row.brier_1x2 >= 0 and row.log_loss_1x2 > 0 for row in report.fold_metrics)
    assert all(row.baseline_brier_1x2 >= 0 and row.baseline_log_loss_1x2 > 0 for row in report.fold_metrics)
    assert 0 <= report.brier_1x2 <= 2
    assert report.log_loss_1x2 > 0
    assert 0 <= report.baseline_brier_1x2 <= 2
    assert report.baseline_log_loss_1x2 > 0


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


def test_nested_tuning_selects_only_chronological_inner_fold_parameters():
    report = evaluate_retrospective(
        make_rows(24),
        min_train_fixtures=8,
        test_window_fixtures=4,
        nested_tuning=True,
        inner_min_train_fixtures=5,
        inner_test_window_fixtures=4,
    )
    assert report.nested_tuning is True
    assert len(report.selected_parameters) == report.fold_count
    assert len(report.fold_metrics) == report.fold_count
    assert all(half_life in (90.0, 180.0, 365.0) for half_life, _, _ in report.selected_parameters)
    assert all(ridge in (0.01, 0.08, 0.25) for _, ridge, _ in report.selected_parameters)
    assert all(rho in (-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15)
               for _, _, rho in report.selected_parameters)



def test_calibration_diagnostics_report_classwise_and_top_label_error():
    result = multiclass_calibration_diagnostics(
        [(0.8, 0.2), (0.2, 0.8), (0.8, 0.2), (0.2, 0.8)],
        [0, 1, 0, 1],
        bins=5,
    )
    assert result.classwise_ece == pytest.approx(0.2)
    assert result.top_label_ece == pytest.approx(0.2)


def test_calibration_diagnostics_reject_invalid_probability_rows():
    with pytest.raises(ValueError, match="sum to one"):
        multiclass_calibration_diagnostics([(0.7, 0.4)], [0])
