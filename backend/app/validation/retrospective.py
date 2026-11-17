"""Event-time-ordered retrospective research evaluation.

This evaluator is intentionally distinct from PIT-certified walk-forward
validation: the legacy corpus lacks verified historical publication and
availability timestamps. It prevents future-event leakage, but its results
must never be labelled historically PIT-certified.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import exp, log

from app.models.attack_defence import GoalResult, fit_attack_defence
from app.models.scoreline import build_scoreline_distribution
from app.validation.bootstrap import PairedFoldBootstrap, paired_fold_block_bootstrap
from app.validation.calibration import multiclass_calibration_diagnostics
from app.validation.temperature_scaling import apply_temperature, fit_temperature
from app.validation.tuning import tune_attack_defence


@dataclass(frozen=True, slots=True)
class RetrospectiveFoldMetrics:
    fold_index: int
    fixture_count: int
    test_start_at: datetime
    test_end_at: datetime
    brier_1x2: float
    log_loss_1x2: float
    baseline_brier_1x2: float
    baseline_log_loss_1x2: float
    mean_scoreline_log_loss: float
    half_life_days: float
    ridge: float
    rho: float
    classwise_ece: float
    top_label_ece: float
    calibrated_brier_1x2: float
    calibrated_log_loss_1x2: float
    calibrated_classwise_ece: float
    calibrated_top_label_ece: float
    temperature: float
    calibration_samples: int


@dataclass(frozen=True, slots=True)
class RetrospectivePrediction:
    fixture_id: str
    fold_index: int
    kickoff_at: datetime
    actual_home_goals: int
    actual_away_goals: int
    home_lambda: float
    away_lambda: float
    home_win: float
    draw: float
    away_win: float
    calibrated_home_win: float
    calibrated_draw: float
    calibrated_away_win: float
    temperature: float
    calibration_samples: int
    scoreline_probability: float
    half_life_days: float
    ridge: float
    rho: float


@dataclass(frozen=True, slots=True)
class RetrospectiveReport:
    evaluation_type: str
    training_fixtures: int
    evaluated_fixtures: int
    excluded_initial_fixtures: int
    fold_count: int
    brier_1x2: float
    log_loss_1x2: float
    mean_scoreline_log_loss: float
    baseline_brier_1x2: float
    baseline_log_loss_1x2: float
    classwise_ece: float
    top_label_ece: float
    calibrated_brier_1x2: float
    calibrated_log_loss_1x2: float
    calibrated_classwise_ece: float
    calibrated_top_label_ece: float
    nested_tuning: bool
    selected_parameters: tuple[tuple[float, float, float], ...]
    fold_metrics: tuple[RetrospectiveFoldMetrics, ...]
    paired_bootstrap: PairedFoldBootstrap
    predictions: tuple[RetrospectivePrediction, ...]


def _groups(rows: list[GoalResult]) -> list[list[GoalResult]]:
    groups: list[list[GoalResult]] = []
    for row in sorted(rows, key=lambda item: (item.kickoff_at, item.fixture_id)):
        if not groups or groups[-1][0].kickoff_at != row.kickoff_at:
            groups.append([row])
        else:
            groups[-1].append(row)
    return groups


def _inner_calibration_data(
    rows: list[GoalResult],
    *,
    half_life_days: float,
    ridge: float,
    rho: float,
    min_train_fixtures: int = 35,
    test_window_fixtures: int = 10,
) -> tuple[list[tuple[float, float, float]], list[int]]:
    """Build chronological inner-OOF probabilities strictly inside outer training."""
    groups = _groups(rows)
    train: list[GoalResult] = []
    probabilities: list[tuple[float, float, float]] = []
    outcomes: list[int] = []
    index = 0
    while index < len(groups):
        batch: list[GoalResult] = []
        while index < len(groups) and len(batch) < test_window_fixtures:
            batch.extend(groups[index])
            index += 1
        if len(train) < min_train_fixtures:
            train.extend(batch)
            continue
        cutoff = batch[0].kickoff_at
        calibration_probabilities, calibration_outcomes = _inner_calibration_data(
            train, half_life_days=selected_half_life, ridge=selected_ridge, rho=selected_rho
        )
        temperature = 1.0
        calibration_samples = len(calibration_probabilities)
        if calibration_samples >= 30:
            temperature = fit_temperature(
                calibration_probabilities, calibration_outcomes, min_samples=30
            ).temperature
        model = fit_attack_defence(
            train,
            as_of=cutoff,
            half_life_days=half_life_days,
            ridge=ridge,
            max_iterations=1200,
        )
        for target in batch:
            rates = model.predict(target.home_team, target.away_team)
            distribution = build_scoreline_distribution(
                rates.home_lambda, rates.away_lambda, rho=rho, max_goals=12
            )
            probabilities.append((
                distribution.home_win, distribution.draw, distribution.away_win
            ))
            outcomes.append(
                0 if target.home_goals > target.away_goals
                else 1 if target.home_goals == target.away_goals else 2
            )
        train.extend(batch)
    return probabilities, outcomes


def evaluate_retrospective(
    results: Iterable[GoalResult],
    *,
    min_train_fixtures: int = 60,
    test_window_fixtures: int = 25,
    half_life_days: float = 180.0,
    ridge: float = 0.08,
    rho: float = 0.0,
    max_goals: int = 12,
    nested_tuning: bool = False,
    inner_min_train_fixtures: int = 35,
    inner_test_window_fixtures: int = 10,
) -> RetrospectiveReport:
    """Expanding event-time evaluation with simultaneous-kickoff isolation."""
    rows = list(results)
    if not rows:
        raise ValueError("no completed results supplied")
    ids = [row.fixture_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate fixture IDs in retrospective corpus")
    if min_train_fixtures < 2 or test_window_fixtures < 1:
        raise ValueError("invalid retrospective fold sizes")
    groups = _groups(rows)
    train: list[GoalResult] = []
    predictions: list[RetrospectivePrediction] = []
    folds = 0
    selected_parameters: list[tuple[float, float, float]] = []
    index = 0
    while index < len(groups):
        batch: list[GoalResult] = []
        while index < len(groups) and len(batch) < test_window_fixtures:
            batch.extend(groups[index])
            index += 1
        if len(train) < min_train_fixtures:
            train.extend(batch)
            continue
        cutoff = batch[0].kickoff_at
        selected_half_life = half_life_days
        selected_ridge = ridge
        selected_rho = rho
        if nested_tuning:
            tuning = tune_attack_defence(
                train,
                min_train_fixtures=inner_min_train_fixtures,
                test_window_fixtures=inner_test_window_fixtures,
            )
            if tuning.inner_folds:
                selected_half_life = tuning.half_life_days
                selected_ridge = tuning.ridge
                selected_rho = tuning.rho
        selected_parameters.append((selected_half_life, selected_ridge, selected_rho))
        model = fit_attack_defence(
            train,
            as_of=cutoff,
            half_life_days=selected_half_life,
            ridge=selected_ridge,
            max_iterations=1200,
        )
        folds += 1
        for target in batch:
            rates = model.predict(target.home_team, target.away_team)
            distribution = build_scoreline_distribution(
                rates.home_lambda,
                rates.away_lambda,
                rho=selected_rho,
                max_goals=max_goals,
            )
            score_probability = (
                distribution.probabilities[target.home_goals][target.away_goals]
                if target.home_goals <= max_goals and target.away_goals <= max_goals
                else 0.0
            )
            calibrated = apply_temperature(
                [(distribution.home_win, distribution.draw, distribution.away_win)],
                temperature,
            )[0]
            predictions.append(RetrospectivePrediction(
                fixture_id=target.fixture_id,
                fold_index=folds,
                kickoff_at=target.kickoff_at,
                actual_home_goals=target.home_goals,
                actual_away_goals=target.away_goals,
                home_lambda=rates.home_lambda,
                away_lambda=rates.away_lambda,
                home_win=distribution.home_win,
                draw=distribution.draw,
                away_win=distribution.away_win,
                calibrated_home_win=calibrated[0],
                calibrated_draw=calibrated[1],
                calibrated_away_win=calibrated[2],
                temperature=temperature,
                calibration_samples=calibration_samples,
                scoreline_probability=score_probability,
                half_life_days=selected_half_life,
                ridge=selected_ridge,
                rho=selected_rho,
            ))
        train.extend(batch)

    if not predictions:
        raise ValueError("insufficient chronological history to form an evaluation fold")
    brier_values: list[float] = []
    log_losses: list[float] = []
    scoreline_losses: list[float] = []
    baseline_brier_values: list[float] = []
    baseline_log_losses: list[float] = []
    for prediction in predictions:
        probabilities = (prediction.home_win, prediction.draw, prediction.away_win)
        actual = 0 if prediction.actual_home_goals > prediction.actual_away_goals else (
            1 if prediction.actual_home_goals == prediction.actual_away_goals else 2
        )
        brier_values.append(sum(
            (probability - (1.0 if i == actual else 0.0)) ** 2
            for i, probability in enumerate(probabilities)
        ))
        log_losses.append(-log(max(1e-15, probabilities[actual])))
        if prediction.scoreline_probability > 0:
            scoreline_losses.append(-log(prediction.scoreline_probability))

    # Same-fold, recency-weighted league baseline: no team-specific effects.
    train = []
    baseline_predictions: dict[str, tuple[float, float, float]] = {}
    index = 0
    while index < len(groups):
        batch: list[GoalResult] = []
        while index < len(groups) and len(batch) < test_window_fixtures:
            batch.extend(groups[index])
            index += 1
        if len(train) < min_train_fixtures:
            train.extend(batch)
            continue
        cutoff = batch[0].kickoff_at
        weights = [
            exp(-0.6931471805599453 * max(0.0, (cutoff-row.kickoff_at).total_seconds()/86400) / half_life_days)
            for row in train
        ]
        weight_sum = max(1e-12, sum(weights))
        home_rate = max(0.05, sum(w*r.home_goals for w, r in zip(weights, train)) / weight_sum)
        away_rate = max(0.05, sum(w*r.away_goals for w, r in zip(weights, train)) / weight_sum)
        baseline_distribution = build_scoreline_distribution(
            home_rate, away_rate, rho=0.0, max_goals=max_goals
        )
        for target in batch:
            baseline_predictions[target.fixture_id] = (
                baseline_distribution.home_win,
                baseline_distribution.draw,
                baseline_distribution.away_win,
            )
        train.extend(batch)

    for prediction in predictions:
        probabilities = baseline_predictions[prediction.fixture_id]
        actual = 0 if prediction.actual_home_goals > prediction.actual_away_goals else (
            1 if prediction.actual_home_goals == prediction.actual_away_goals else 2
        )
        baseline_brier_values.append(sum(
            (probability - (1.0 if i == actual else 0.0)) ** 2
            for i, probability in enumerate(probabilities)
        ))
        baseline_log_losses.append(-log(max(1e-15, probabilities[actual])))

    calibrated_probabilities = [
        (row.calibrated_home_win, row.calibrated_draw, row.calibrated_away_win)
        for row in predictions
    ]
    calibrated_brier_values = []
    calibrated_log_losses = []
    for row, probs in zip(predictions, calibrated_probabilities):
        actual = 0 if row.actual_home_goals > row.actual_away_goals else (
            1 if row.actual_home_goals == row.actual_away_goals else 2
        )
        calibrated_brier_values.append(sum(
            (probability - (1.0 if i == actual else 0.0)) ** 2
            for i, probability in enumerate(probs)
        ))
        calibrated_log_losses.append(-log(max(1e-15, probs[actual])))
    calibrated_overall = multiclass_calibration_diagnostics(
        calibrated_probabilities,
        [0 if row.actual_home_goals > row.actual_away_goals else (
            1 if row.actual_home_goals == row.actual_away_goals else 2
        ) for row in predictions],
    )
    overall_calibration = multiclass_calibration_diagnostics(
        [(row.home_win, row.draw, row.away_win) for row in predictions],
        [0 if row.actual_home_goals > row.actual_away_goals else (
            1 if row.actual_home_goals == row.actual_away_goals else 2
        ) for row in predictions],
    )
    fold_metrics: list[RetrospectiveFoldMetrics] = []
    for fold_index in range(1, folds + 1):
        fold_rows = [row for row in predictions if row.fold_index == fold_index]
        fold_brier: list[float] = []
        fold_log_loss: list[float] = []
        fold_baseline_brier: list[float] = []
        fold_baseline_log_loss: list[float] = []
        fold_scoreline_loss: list[float] = []
        fold_calibrated_brier: list[float] = []
        fold_calibrated_log_loss: list[float] = []
        for row in fold_rows:
            probs = (row.home_win, row.draw, row.away_win)
            actual = 0 if row.actual_home_goals > row.actual_away_goals else (
                1 if row.actual_home_goals == row.actual_away_goals else 2
            )
            fold_brier.append(sum(
                (probability - (1.0 if i == actual else 0.0)) ** 2
                for i, probability in enumerate(probs)
            ))
            fold_log_loss.append(-log(max(1e-15, probs[actual])))
            calibrated_probs = (
                row.calibrated_home_win, row.calibrated_draw, row.calibrated_away_win
            )
            fold_calibrated_brier.append(sum(
                (probability - (1.0 if i == actual else 0.0)) ** 2
                for i, probability in enumerate(calibrated_probs)
            ))
            fold_calibrated_log_loss.append(-log(max(1e-15, calibrated_probs[actual])))
            base_probs = baseline_predictions[row.fixture_id]
            fold_baseline_brier.append(sum(
                (probability - (1.0 if i == actual else 0.0)) ** 2
                for i, probability in enumerate(base_probs)
            ))
            fold_baseline_log_loss.append(-log(max(1e-15, base_probs[actual])))
            if row.scoreline_probability > 0:
                fold_scoreline_loss.append(-log(row.scoreline_probability))
        if not fold_rows:
            continue
        first, last = fold_rows[0], fold_rows[-1]
        fold_calibrated_calibration = multiclass_calibration_diagnostics(
            [(row.calibrated_home_win, row.calibrated_draw, row.calibrated_away_win)
             for row in fold_rows],
            [0 if row.actual_home_goals > row.actual_away_goals else (
                1 if row.actual_home_goals == row.actual_away_goals else 2
            ) for row in fold_rows],
        )
        fold_calibration = multiclass_calibration_diagnostics(
            [(row.home_win, row.draw, row.away_win) for row in fold_rows],
            [0 if row.actual_home_goals > row.actual_away_goals else (
                1 if row.actual_home_goals == row.actual_away_goals else 2
            ) for row in fold_rows],
        )
        fold_metrics.append(RetrospectiveFoldMetrics(
            fold_index=fold_index,
            fixture_count=len(fold_rows),
            test_start_at=first.kickoff_at,
            test_end_at=last.kickoff_at,
            brier_1x2=sum(fold_brier) / len(fold_brier),
            log_loss_1x2=sum(fold_log_loss) / len(fold_log_loss),
            baseline_brier_1x2=sum(fold_baseline_brier) / len(fold_baseline_brier),
            baseline_log_loss_1x2=sum(fold_baseline_log_loss) / len(fold_baseline_log_loss),
            mean_scoreline_log_loss=(
                sum(fold_scoreline_loss) / len(fold_scoreline_loss)
                if fold_scoreline_loss else float("inf")
            ),
            half_life_days=first.half_life_days,
            ridge=first.ridge,
            rho=first.rho,
            classwise_ece=fold_calibration.classwise_ece,
            top_label_ece=fold_calibration.top_label_ece,
            calibrated_brier_1x2=sum(fold_calibrated_brier) / len(fold_calibrated_brier),
            calibrated_log_loss_1x2=sum(fold_calibrated_log_loss) / len(fold_calibrated_log_loss),
            calibrated_classwise_ece=fold_calibrated_calibration.classwise_ece,
            calibrated_top_label_ece=fold_calibrated_calibration.top_label_ece,
            temperature=first.temperature,
            calibration_samples=first.calibration_samples,
        ))

    return RetrospectiveReport(
        evaluation_type="RETROSPECTIVE_EVENT_TIME_NOT_PIT_CERTIFIED",
        training_fixtures=len(rows) - len(predictions),
        evaluated_fixtures=len(predictions),
        excluded_initial_fixtures=len(rows) - len(predictions),
        fold_count=folds,
        brier_1x2=sum(brier_values) / len(brier_values),
        log_loss_1x2=sum(log_losses) / len(log_losses),
        mean_scoreline_log_loss=(
            sum(scoreline_losses) / len(scoreline_losses) if scoreline_losses else float("inf")
        ),
        baseline_brier_1x2=sum(baseline_brier_values) / len(baseline_brier_values),
        baseline_log_loss_1x2=sum(baseline_log_losses) / len(baseline_log_losses),
        classwise_ece=overall_calibration.classwise_ece,
        top_label_ece=overall_calibration.top_label_ece,
        calibrated_brier_1x2=sum(calibrated_brier_values) / len(calibrated_brier_values),
        calibrated_log_loss_1x2=sum(calibrated_log_losses) / len(calibrated_log_losses),
        calibrated_classwise_ece=calibrated_overall.classwise_ece,
        calibrated_top_label_ece=calibrated_overall.top_label_ece,
        nested_tuning=nested_tuning,
        selected_parameters=tuple(selected_parameters),
        fold_metrics=tuple(fold_metrics),
        paired_bootstrap=paired_fold_block_bootstrap(fold_metrics),
        predictions=tuple(predictions),
    )
