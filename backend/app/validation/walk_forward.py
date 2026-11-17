"""Leakage-resistant chronological walk-forward folds and proper scoring rules."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite, log


@dataclass(frozen=True, slots=True)
class EvaluationFixture:
    fixture_id: str
    kickoff_at: datetime
    prediction_cutoff_at: datetime
    features_available_at: datetime
    label_available_at: datetime
    home_goals: int
    away_goals: int
    identity_verified: bool
    duplicate_excluded: bool
    rights_approved: bool
    pit_eligible: bool
    competition_identity_verified: bool = False

    def __post_init__(self) -> None:
        if not self.fixture_id:
            raise ValueError("fixture_id is required")
        for name in ("kickoff_at", "prediction_cutoff_at", "features_available_at", "label_available_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("goals cannot be negative")

    @property
    def ineligibility_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.identity_verified:
            reasons.append("TEAM_OR_FIXTURE_IDENTITY_UNVERIFIED")
        if not self.competition_identity_verified:
            reasons.append("COMPETITION_IDENTITY_UNVERIFIED")
        if not self.duplicate_excluded:
            reasons.append("DUPLICATE_STATUS_UNRESOLVED")
        if not self.rights_approved:
            reasons.append("SOURCE_RIGHTS_NOT_APPROVED")
        if not self.pit_eligible:
            reasons.append("SOURCE_NOT_POINT_IN_TIME_ELIGIBLE")
        if self.features_available_at > self.prediction_cutoff_at:
            reasons.append("FEATURES_NOT_AVAILABLE_AT_PREDICTION_CUTOFF")
        if self.prediction_cutoff_at >= self.kickoff_at:
            reasons.append("PREDICTION_CUTOFF_NOT_BEFORE_KICKOFF")
        return tuple(reasons)

    @property
    def eligible(self) -> bool:
        return not self.ineligibility_reasons


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    fold_index: int
    train_fixture_ids: tuple[str, ...]
    test_fixture_ids: tuple[str, ...]
    train_label_cutoff_at: datetime
    test_start_at: datetime
    test_end_at: datetime


def walk_forward_splits(
    fixtures: Iterable[EvaluationFixture],
    *,
    min_train_fixtures: int,
    test_window_fixtures: int,
    embargo: timedelta = timedelta(0),
) -> tuple[WalkForwardFold, ...]:
    """Create expanding-window folds; simultaneous kickoffs stay in one test block.

    Training labels must have become available by the earliest test prediction cutoff
    minus embargo. Fixture kickoff alone is never treated as proof that its final score
    was already available. Ineligible fixtures are excluded from both train and test.
    """
    if min_train_fixtures < 1 or test_window_fixtures < 1:
        raise ValueError("train and test window sizes must be positive")
    if embargo < timedelta(0):
        raise ValueError("embargo cannot be negative")
    rows = tuple(fixtures)
    ids = [row.fixture_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate fixture IDs in validation input")
    eligible = sorted((row for row in rows if row.eligible), key=lambda row: (row.kickoff_at, row.fixture_id))
    if not eligible:
        return ()

    kickoff_groups: list[list[EvaluationFixture]] = []
    for row in eligible:
        if not kickoff_groups or kickoff_groups[-1][0].kickoff_at != row.kickoff_at:
            kickoff_groups.append([row])
        else:
            kickoff_groups[-1].append(row)

    folds: list[WalkForwardFold] = []
    group_index = 0
    while group_index < len(kickoff_groups):
        test_groups: list[list[EvaluationFixture]] = []
        test_count = 0
        while group_index < len(kickoff_groups) and test_count < test_window_fixtures:
            group = kickoff_groups[group_index]
            test_groups.append(group)
            test_count += len(group)
            group_index += 1

        test_rows = [row for group in test_groups for row in group]
        test_start = test_rows[0].kickoff_at
        test_cutoff = min(row.prediction_cutoff_at for row in test_rows) - embargo
        train_rows = [row for row in eligible if row.kickoff_at < test_start and row.label_available_at <= test_cutoff]
        if len(train_rows) < min_train_fixtures:
            continue
        folds.append(
            WalkForwardFold(
                fold_index=len(folds) + 1,
                train_fixture_ids=tuple(row.fixture_id for row in train_rows),
                test_fixture_ids=tuple(row.fixture_id for row in test_rows),
                train_label_cutoff_at=test_cutoff,
                test_start_at=test_start,
                test_end_at=max(row.kickoff_at for row in test_rows),
            )
        )
    return tuple(folds)


def multiclass_brier_score(
    actual_indices: Sequence[int], predicted_probabilities: Sequence[Sequence[float]]
) -> float:
    """Mean multiclass Brier score; lower is better."""
    if not actual_indices or len(actual_indices) != len(predicted_probabilities):
        raise ValueError("actuals and predictions must be non-empty and equally sized")
    scores: list[float] = []
    expected_classes = len(predicted_probabilities[0])
    if expected_classes < 2:
        raise ValueError("at least two classes are required")
    for actual, probabilities in zip(actual_indices, predicted_probabilities, strict=True):
        if len(probabilities) != expected_classes or not 0 <= actual < expected_classes:
            raise ValueError("inconsistent class dimensions or invalid actual index")
        if any(not isfinite(value) or value < 0 or value > 1 for value in probabilities):
            raise ValueError("probabilities must be finite and between zero and one")
        if abs(sum(probabilities) - 1.0) > 1e-8:
            raise ValueError("class probabilities must sum to one")
        scores.append(sum((probability - (1.0 if index == actual else 0.0)) ** 2 for index, probability in enumerate(probabilities)))
    return sum(scores) / len(scores)


def multiclass_log_loss(
    actual_indices: Sequence[int], predicted_probabilities: Sequence[Sequence[float]], *, epsilon: float = 1e-15
) -> float:
    """Mean multiclass negative log likelihood; lower is better."""
    if not 0 < epsilon < 0.5:
        raise ValueError("epsilon must be between zero and one half")
    if not actual_indices or len(actual_indices) != len(predicted_probabilities):
        raise ValueError("actuals and predictions must be non-empty and equally sized")
    losses: list[float] = []
    for actual, probabilities in zip(actual_indices, predicted_probabilities, strict=True):
        if not 0 <= actual < len(probabilities) or len(probabilities) < 2:
            raise ValueError("invalid actual index or class dimensions")
        if any(not isfinite(value) or value < 0 or value > 1 for value in probabilities):
            raise ValueError("probabilities must be finite and between zero and one")
        if abs(sum(probabilities) - 1.0) > 1e-8:
            raise ValueError("class probabilities must sum to one")
        losses.append(-log(max(epsilon, probabilities[actual])))
    return sum(losses) / len(losses)
