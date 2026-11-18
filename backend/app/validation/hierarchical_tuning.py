"""Leakage-safe chronological selection for hierarchical Poisson hyperparameters.

Each fold trains strictly before its validation window. Candidate selection uses
held-out Poisson negative log likelihood; no bookmaker odds or future outcomes
enter a fitted fold. The selected settings are development-only and must be
frozen before prospective evaluation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from itertools import product
from math import exp, lgamma, log
from collections.abc import Iterable, Sequence

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)


@dataclass(frozen=True, slots=True)
class HierarchicalCandidate:
    half_life_days: float
    team_ridge: float
    competition_ridge: float

    def __post_init__(self) -> None:
        if self.half_life_days <= 0 or self.team_ridge < 0 or self.competition_ridge < 0:
            raise ValueError("invalid candidate hyperparameters")


@dataclass(frozen=True, slots=True)
class ChronologicalFold:
    train_cutoff: datetime
    validation_end: datetime

    def __post_init__(self) -> None:
        if self.train_cutoff.tzinfo is None or self.train_cutoff.utcoffset() is None:
            raise ValueError("fold cutoff must be timezone-aware")
        if self.validation_end.tzinfo is None or self.validation_end.utcoffset() is None:
            raise ValueError("validation end must be timezone-aware")
        if self.validation_end <= self.train_cutoff:
            raise ValueError("validation end must follow training cutoff")


@dataclass(frozen=True, slots=True)
class CandidateScore:
    candidate: HierarchicalCandidate
    mean_validation_nll: float
    scored_matches: int
    folds_scored: int


@dataclass(frozen=True, slots=True)
class HyperparameterSelection:
    selected: HierarchicalCandidate
    leaderboard: tuple[CandidateScore, ...]
    protocol: str = "EXPANDING_WINDOW_PAIRED_POISSON_NLL_V1"


def _poisson_nll(observed: int, rate: float) -> float:
    if rate <= 0:
        raise ValueError("predicted rate must be positive")
    return rate - observed * log(rate) + lgamma(observed + 1)


def _candidate_grid(
    half_lives: Sequence[float],
    team_ridges: Sequence[float],
    competition_ridges: Sequence[float],
) -> tuple[HierarchicalCandidate, ...]:
    return tuple(
        HierarchicalCandidate(*values)
        for values in product(half_lives, team_ridges, competition_ridges)
    )


def select_hierarchical_hyperparameters(
    results: Iterable[HierarchicalGoalResult],
    folds: Sequence[ChronologicalFold],
    *,
    half_lives: Sequence[float] = (90.0, 180.0, 365.0),
    team_ridges: Sequence[float] = (0.1, 0.5, 2.0, 8.0),
    competition_ridges: Sequence[float] = (0.5, 2.0, 8.0),
    min_training_fixtures: int = 30,
) -> HyperparameterSelection:
    """Choose hyperparameters on expanding-window validation folds.

    The fold definitions are explicit and immutable. Every validation fixture
    must occur after its training cutoff. A fixture may be scored in more than
    one fold only when the caller intentionally defines non-overlapping or
    rolling validation windows; overlapping windows are rejected here.
    """
    rows = tuple(results)
    if not folds:
        raise ValueError("at least one chronological fold is required")
    if min_training_fixtures < 1:
        raise ValueError("min_training_fixtures must be positive")
    if len({row.fixture_id for row in rows}) != len(rows):
        raise ValueError("duplicate fixture IDs are not allowed")
    ordered_folds = tuple(sorted(folds, key=lambda f: f.train_cutoff))
    for previous, current in zip(ordered_folds, ordered_folds[1:]):
        if current.train_cutoff < previous.validation_end:
            raise ValueError("chronological validation windows overlap")

    candidates = _candidate_grid(half_lives, team_ridges, competition_ridges)
    if not candidates:
        raise ValueError("candidate grid cannot be empty")

    totals = {candidate: 0.0 for candidate in candidates}
    counts = {candidate: 0 for candidate in candidates}
    fold_counts = {candidate: 0 for candidate in candidates}

    for fold in ordered_folds:
        train = tuple(row for row in rows if row.kickoff_at <= fold.train_cutoff)
        validation = tuple(
            row for row in rows
            if fold.train_cutoff < row.kickoff_at <= fold.validation_end
        )
        if len(train) < min_training_fixtures:
            continue
        if not validation:
            continue
        for candidate in candidates:
            model = fit_hierarchical_poisson(
                train,
                as_of=fold.train_cutoff,
                half_life_days=candidate.half_life_days,
                team_ridge=candidate.team_ridge,
                competition_ridge=candidate.competition_ridge,
            )
            for row in validation:
                rates = model.predict(
                    row.home_team_id, row.away_team_id, row.competition_id
                )
                totals[candidate] += (
                    _poisson_nll(row.home_goals, rates.home_lambda)
                    + _poisson_nll(row.away_goals, rates.away_lambda)
                )
                counts[candidate] += 1
            fold_counts[candidate] += 1

    leaderboard = tuple(sorted(
        (
            CandidateScore(candidate, totals[candidate] / (2 * counts[candidate]),
                           counts[candidate], fold_counts[candidate])
            for candidate in candidates if counts[candidate] > 0
        ),
        key=lambda item: (item.mean_validation_nll, item.candidate.half_life_days,
                          item.candidate.team_ridge, item.candidate.competition_ridge),
    ))
    if not leaderboard:
        raise ValueError("no chronological fold had sufficient training and validation data")
    return HyperparameterSelection(leaderboard[0].candidate, leaderboard)
