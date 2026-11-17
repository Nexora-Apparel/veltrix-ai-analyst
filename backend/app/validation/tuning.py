"""Nested chronological hyperparameter selection for attack/defence Poisson.

All tuning predictions are generated from earlier event-time training rows.
No random folds are used; simultaneous kickoff groups remain intact.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import log

from app.models.attack_defence import GoalResult, fit_attack_defence
from app.models.scoreline import build_scoreline_distribution


@dataclass(frozen=True, slots=True)
class TuningResult:
    half_life_days: float
    ridge: float
    rho: float
    inner_folds: int
    inner_predictions: int
    inner_log_loss_1x2: float
    inner_brier_1x2: float
    inner_scoreline_log_loss: float


def _kickoff_groups(rows: list[GoalResult]) -> list[list[GoalResult]]:
    groups: list[list[GoalResult]] = []
    for row in sorted(rows, key=lambda item: (item.kickoff_at, item.fixture_id)):
        if not groups or groups[-1][0].kickoff_at != row.kickoff_at:
            groups.append([row])
        else:
            groups[-1].append(row)
    return groups


def _inner_oof_rates(
    rows: list[GoalResult],
    *,
    min_train_fixtures: int,
    test_window_fixtures: int,
    half_life_days: float,
    ridge: float,
) -> tuple[list[tuple[GoalResult, float, float]], int]:
    groups = _kickoff_groups(rows)
    train: list[GoalResult] = []
    predictions: list[tuple[GoalResult, float, float]] = []
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
        model = fit_attack_defence(
            train,
            as_of=cutoff,
            half_life_days=half_life_days,
            ridge=ridge,
            max_iterations=1200,
        )
        folds += 1
        for target in batch:
            rates = model.predict(target.home_team, target.away_team)
            predictions.append((target, rates.home_lambda, rates.away_lambda))
        train.extend(batch)
    return predictions, folds


def _outcome_index(row: GoalResult) -> int:
    if row.home_goals > row.away_goals:
        return 0
    if row.home_goals == row.away_goals:
        return 1
    return 2


def tune_attack_defence(
    results: Iterable[GoalResult],
    *,
    min_train_fixtures: int = 35,
    test_window_fixtures: int = 10,
    half_life_candidates: tuple[float, ...] = (90.0, 180.0, 365.0),
    ridge_candidates: tuple[float, ...] = (0.01, 0.08, 0.25),
    rho_candidates: tuple[float, ...] = (-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15),
    max_goals: int = 12,
) -> TuningResult:
    """Select decay/ridge by inner 1X2 log loss, then rho by scoreline log loss."""
    rows = list(results)
    if not rows:
        raise ValueError("no results supplied for tuning")
    if len({row.fixture_id for row in rows}) != len(rows):
        raise ValueError("duplicate fixture IDs in tuning corpus")
    if min_train_fixtures < 2 or test_window_fixtures < 1:
        raise ValueError("invalid inner fold sizes")
    if not half_life_candidates or not ridge_candidates or not rho_candidates:
        raise ValueError("tuning candidate grids cannot be empty")
    if any(value <= 0 for value in half_life_candidates):
        raise ValueError("half-life candidates must be positive")
    if any(value < 0 for value in ridge_candidates):
        raise ValueError("ridge candidates cannot be negative")

    candidate_results: list[
        tuple[float, float, float, float, list[tuple[GoalResult, float, float]], int]
    ] = []
    for half_life in half_life_candidates:
        for ridge in ridge_candidates:
            predictions, folds = _inner_oof_rates(
                rows,
                min_train_fixtures=min_train_fixtures,
                test_window_fixtures=test_window_fixtures,
                half_life_days=half_life,
                ridge=ridge,
            )
            if not predictions:
                continue
            log_losses: list[float] = []
            brier_values: list[float] = []
            for target, home_rate, away_rate in predictions:
                distribution = build_scoreline_distribution(
                    home_rate, away_rate, rho=0.0, max_goals=max_goals
                )
                probabilities = (
                    distribution.home_win,
                    distribution.draw,
                    distribution.away_win,
                )
                actual = _outcome_index(target)
                log_losses.append(-log(max(1e-15, probabilities[actual])))
                brier_values.append(sum(
                    (probability - (1.0 if index == actual else 0.0)) ** 2
                    for index, probability in enumerate(probabilities)
                ))
            candidate_results.append((
                sum(log_losses) / len(log_losses),
                sum(brier_values) / len(brier_values),
                half_life,
                ridge,
                predictions,
                folds,
            ))

    if not candidate_results:
        return TuningResult(
            half_life_days=180.0,
            ridge=0.08,
            rho=0.0,
            inner_folds=0,
            inner_predictions=0,
            inner_log_loss_1x2=float("inf"),
            inner_brier_1x2=float("inf"),
            inner_scoreline_log_loss=float("inf"),
        )

    (
        best_log_loss,
        best_brier,
        best_half_life,
        best_ridge,
        best_predictions,
        best_folds,
    ) = min(candidate_results, key=lambda item: (item[0], item[1], item[2], item[3]))
    rho_scores: list[tuple[float, float]] = []
    for rho in rho_candidates:
        losses: list[float] = []
        for target, home_rate, away_rate in best_predictions:
            distribution = build_scoreline_distribution(
                home_rate, away_rate, rho=rho, max_goals=max_goals
            )
            if target.home_goals > max_goals or target.away_goals > max_goals:
                probability = 0.0
            else:
                probability = distribution.probabilities[target.home_goals][target.away_goals]
            losses.append(-log(max(1e-15, probability)))
        rho_scores.append((sum(losses) / len(losses), rho))
    best_scoreline_loss, best_rho = min(
        rho_scores, key=lambda item: (item[0], abs(item[1]), item[1])
    )

    return TuningResult(
        half_life_days=best_half_life,
        ridge=best_ridge,
        rho=best_rho,
        inner_folds=best_folds,
        inner_predictions=len(best_predictions),
        inner_log_loss_1x2=best_log_loss,
        inner_brier_1x2=best_brier,
        inner_scoreline_log_loss=best_scoreline_loss,
    )
