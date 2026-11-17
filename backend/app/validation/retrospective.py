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


@dataclass(frozen=True, slots=True)
class RetrospectivePrediction:
    fixture_id: str
    kickoff_at: datetime
    actual_home_goals: int
    actual_away_goals: int
    home_lambda: float
    away_lambda: float
    home_win: float
    draw: float
    away_win: float
    scoreline_probability: float


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
    predictions: tuple[RetrospectivePrediction, ...]
    selected_parameters: tuple[tuple[float, float, float], ...] = ()


def _groups(rows: list[GoalResult]) -> list[list[GoalResult]]:
    groups: list[list[GoalResult]] = []
    for row in sorted(rows, key=lambda item: (item.kickoff_at, item.fixture_id)):
        if not groups or groups[-1][0].kickoff_at != row.kickoff_at:
            groups.append([row])
        else:
            groups[-1].append(row)
    return groups



def _select_inner_parameters(
    training: list[GoalResult],
    *,
    max_goals: int,
) -> tuple[float, float, float]:
    """Select half-life, ridge and Dixon-Coles rho from inner prequential folds."""
    if len(training) < 100:
        return 180.0, 0.08, 0.0
    inner_min_train = max(40, min(80, len(training) // 2))
    best: tuple[float, float, float, float] | None = None
    for half_life in (90.0, 180.0, 365.0):
        for ridge in (0.02, 0.08, 0.2):
            try:
                inner = evaluate_retrospective(
                    training,
                    min_train_fixtures=inner_min_train,
                    test_window_fixtures=20,
                    half_life_days=half_life,
                    ridge=ridge,
                    rho=0.0,
                    max_goals=max_goals,
                    tune=False,
                )
            except ValueError:
                continue
            if not inner.predictions:
                continue
            for rho in (-0.12, -0.08, -0.04, 0.0, 0.04, 0.08, 0.12):
                log_losses: list[float] = []
                scoreline_losses: list[float] = []
                for prediction in inner.predictions:
                    distribution = build_scoreline_distribution(
                        prediction.home_lambda,
                        prediction.away_lambda,
                        rho=rho,
                        max_goals=max_goals,
                    )
                    probabilities = (
                        distribution.home_win,
                        distribution.draw,
                        distribution.away_win,
                    )
                    actual = (
                        0 if prediction.actual_home_goals > prediction.actual_away_goals
                        else 1 if prediction.actual_home_goals == prediction.actual_away_goals
                        else 2
                    )
                    log_losses.append(-log(max(1e-15, probabilities[actual])))
                    if (
                        prediction.actual_home_goals <= max_goals
                        and prediction.actual_away_goals <= max_goals
                    ):
                        score_probability = distribution.probabilities[
                            prediction.actual_home_goals
                        ][prediction.actual_away_goals]
                    else:
                        score_probability = 1e-15
                    scoreline_losses.append(-log(max(1e-15, score_probability)))
                objective = (
                    sum(log_losses) / len(log_losses)
                    + 0.10 * sum(scoreline_losses) / len(scoreline_losses)
                    + 0.002 * abs(log(half_life / 180.0))
                    + 0.002 * abs(log(ridge / 0.08))
                    + 0.001 * abs(rho)
                )
                candidate = (objective, half_life, ridge, rho)
                if best is None or candidate < best:
                    best = candidate
    if best is None:
        return 180.0, 0.08, 0.0
    return best[1], best[2], best[3]


def evaluate_retrospective(
    results: Iterable[GoalResult],
    *,
    min_train_fixtures: int = 60,
    test_window_fixtures: int = 25,
    half_life_days: float = 180.0,
    ridge: float = 0.08,
    rho: float = 0.0,
    max_goals: int = 12,
    tune: bool = False,
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
    selected_parameters: list[tuple[float, float, float]] = []
    folds = 0
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
        fold_half_life, fold_ridge, fold_rho = (
            _select_inner_parameters(train, max_goals=max_goals)
            if tune else (half_life_days, ridge, rho)
        )
        selected_parameters.append((fold_half_life, fold_ridge, fold_rho))
        model = fit_attack_defence(
            train,
            as_of=cutoff,
            half_life_days=fold_half_life,
            ridge=fold_ridge,
            max_iterations=1200,
        )
        folds += 1
        for target in batch:
            rates = model.predict(target.home_team, target.away_team)
            distribution = build_scoreline_distribution(
                rates.home_lambda,
                rates.away_lambda,
                rho=fold_rho,
                max_goals=max_goals,
            )
            score_probability = (
                distribution.probabilities[target.home_goals][target.away_goals]
                if target.home_goals <= max_goals and target.away_goals <= max_goals
                else 0.0
            )
            predictions.append(RetrospectivePrediction(
                fixture_id=target.fixture_id,
                kickoff_at=target.kickoff_at,
                actual_home_goals=target.home_goals,
                actual_away_goals=target.away_goals,
                home_lambda=rates.home_lambda,
                away_lambda=rates.away_lambda,
                home_win=distribution.home_win,
                draw=distribution.draw,
                away_win=distribution.away_win,
                scoreline_probability=score_probability,
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
        scoreline_losses.append(-log(max(1e-15, prediction.scoreline_probability)))

    # Same-fold, recency-weighted league baseline: no team-specific effects.
    train = []
    baseline_predictions: dict[str, tuple[float, float, float]] = {}
    baseline_fold_index = 0
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
        fold_half_life = selected_parameters[baseline_fold_index][0]
        baseline_fold_index += 1
        weights = [
            exp(-0.6931471805599453 * max(0.0, (cutoff-row.kickoff_at).total_seconds()/86400) / fold_half_life)
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
        predictions=tuple(predictions),
        selected_parameters=tuple(selected_parameters),
    )
