"""Leakage-safe chronological selection for hierarchical Poisson hyperparameters.

Each fold trains strictly before its validation window. Candidate selection uses
held-out Poisson negative log likelihood. Selected settings are development-only
and must be frozen before prospective evaluation.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise, product
from math import lgamma, log

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


def select_hierarchical_hyperparameters(
    results: Iterable[HierarchicalGoalResult],
    folds: Sequence[ChronologicalFold],
    *,
    half_lives: Sequence[float] = (90.0, 180.0, 365.0),
    team_ridges: Sequence[float] = (0.1, 0.5, 2.0, 8.0),
    competition_ridges: Sequence[float] = (0.5, 2.0, 8.0),
    min_training_fixtures: int = 30,
    label_available_at: Mapping[str, datetime] | None = None,
    evaluation_as_of: datetime | None = None,
) -> HyperparameterSelection:
    """Choose settings using chronological windows and optional observed-label times.

    When label_available_at is supplied, a result enters a training fold only
    when both its kickoff and its actual label-availability timestamp are at
    or before that fold's training cutoff. This is the required mode for
    database/import-derived research data; kickoff time alone is not evidence
    that the model knew the result.
    """
    rows = tuple(results)
    if not folds:
        raise ValueError("at least one chronological fold is required")
    if min_training_fixtures < 1:
        raise ValueError("min_training_fixtures must be positive")
    if len({row.fixture_id for row in rows}) != len(rows):
        raise ValueError("duplicate fixture IDs are not allowed")
    if label_available_at is not None:
        if evaluation_as_of is None:
            raise ValueError("availability-aware tuning requires evaluation_as_of")
        if set(label_available_at) != {row.fixture_id for row in rows}:
            raise ValueError("label availability timestamps must cover every result exactly")
        for row in rows:
            available_at = label_available_at[row.fixture_id]
            if (
                available_at.tzinfo is None or available_at.utcoffset() is None
                or available_at <= row.kickoff_at
            ):
                raise ValueError("every label availability timestamp must be aware and post-kickoff")
        if evaluation_as_of is not None and (
            evaluation_as_of.tzinfo is None or evaluation_as_of.utcoffset() is None
        ):
            raise ValueError("evaluation_as_of must be timezone-aware")
    ordered = tuple(sorted(folds, key=lambda fold: fold.train_cutoff))
    for fold in ordered:
        if label_available_at is not None and fold.train_cutoff > evaluation_as_of:
            raise ValueError("fold training cutoff cannot be later than evaluation_as_of")
    for previous, current in pairwise(ordered):
        if current.train_cutoff < previous.validation_end:
            raise ValueError("chronological validation windows overlap")
    candidates = tuple(
        HierarchicalCandidate(*values)
        for values in product(half_lives, team_ridges, competition_ridges)
    )
    if not candidates:
        raise ValueError("candidate grid cannot be empty")

    totals = {candidate: 0.0 for candidate in candidates}
    counts = {candidate: 0 for candidate in candidates}
    fold_counts = {candidate: 0 for candidate in candidates}
    for fold in ordered:
        train = tuple(
            row for row in rows
            if row.kickoff_at <= fold.train_cutoff
            and (
                label_available_at is None
                or label_available_at[row.fixture_id] <= fold.train_cutoff
            )
        )
        validation = tuple(
            row for row in rows
            if fold.train_cutoff < row.kickoff_at <= fold.validation_end
        )
        if label_available_at is not None and evaluation_as_of is not None:
            validation = tuple(
                row for row in validation
                if label_available_at[row.fixture_id] <= evaluation_as_of
            )
        if len(train) < min_training_fixtures or not validation:
            continue
        for candidate in candidates:
            fitted = fit_hierarchical_poisson(
                train,
                as_of=fold.train_cutoff,
                half_life_days=candidate.half_life_days,
                team_ridge=candidate.team_ridge,
                competition_ridge=candidate.competition_ridge,
            )
            for row in validation:
                rates = fitted.predict(
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
            CandidateScore(
                candidate,
                totals[candidate] / (2 * counts[candidate]),
                counts[candidate],
                fold_counts[candidate],
            )
            for candidate in candidates if counts[candidate] > 0
        ),
        key=lambda item: (
            item.mean_validation_nll,
            item.candidate.half_life_days,
            item.candidate.team_ridge,
            item.candidate.competition_ridge,
        ),
    ))
    if not leaderboard:
        raise ValueError("no chronological fold had sufficient training and validation data")
    protocol = (
        "EXPANDING_WINDOW_LABEL_AVAILABILITY_AWARE_PAIRED_POISSON_NLL_V2"
        if label_available_at is not None
        else "EXPANDING_WINDOW_PAIRED_POISSON_NLL_V1"
    )
    return HyperparameterSelection(leaderboard[0].candidate, leaderboard, protocol)
