"""Competition-aware, partially pooled Poisson goal-rate model.

The competition intercept is learned from observed training results. Team attack
and defence effects are regularized toward that competition baseline. Teams with
no history receive a zero team effect while retaining the observed competition
context; no fixed outcome probabilities are supplied.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import exp, isfinite, log


@dataclass(frozen=True, slots=True)
class HierarchicalGoalResult:
    fixture_id: str
    kickoff_at: datetime
    competition_id: str
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (
                self.fixture_id,
                self.competition_id,
                self.home_team_id,
                self.away_team_id,
            )
        ):
            raise ValueError("fixture, competition and team identifiers are required")
        if self.home_team_id == self.away_team_id:
            raise ValueError("home and away teams must differ")
        if self.kickoff_at.tzinfo is None or self.kickoff_at.utcoffset() is None:
            raise ValueError("kickoff_at must be timezone-aware")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("goals cannot be negative")


@dataclass(frozen=True, slots=True)
class HierarchicalGoalRates:
    home_lambda: float
    away_lambda: float
    competition_seen: bool
    home_team_history: int
    away_team_history: int


@dataclass(frozen=True, slots=True)
class HierarchicalPoissonModel:
    global_intercept: float
    competition_effects: dict[str, float]
    home_advantage: float
    attack: dict[str, float]
    defence: dict[str, float]
    team_match_counts: dict[str, int]
    competition_match_counts: dict[str, int]
    training_fixtures: int
    training_cutoff_at: datetime
    half_life_days: float
    team_ridge: float
    competition_ridge: float

    def predict(
        self, home_team_id: str, away_team_id: str, competition_id: str
    ) -> HierarchicalGoalRates:
        if not home_team_id or not away_team_id or not competition_id:
            raise ValueError("fixture identifiers are required")
        if home_team_id == away_team_id:
            raise ValueError("home and away teams must differ")
        competition_seen = competition_id in self.competition_effects
        competition_effect = self.competition_effects.get(competition_id, 0.0)
        home_attack = self.attack.get(home_team_id, 0.0)
        away_attack = self.attack.get(away_team_id, 0.0)
        home_defence = self.defence.get(home_team_id, 0.0)
        away_defence = self.defence.get(away_team_id, 0.0)
        shared = self.global_intercept + competition_effect
        home_eta = shared + self.home_advantage + home_attack - away_defence
        away_eta = shared + away_attack - home_defence
        return HierarchicalGoalRates(
            home_lambda=exp(max(-10.0, min(10.0, home_eta))),
            away_lambda=exp(max(-10.0, min(10.0, away_eta))),
            competition_seen=competition_seen,
            home_team_history=self.team_match_counts.get(home_team_id, 0),
            away_team_history=self.team_match_counts.get(away_team_id, 0),
        )


def _time_weight(age_days: float, half_life_days: float) -> float:
    return exp(-log(2.0) * max(0.0, age_days) / half_life_days)


def fit_hierarchical_poisson(
    results: Iterable[HierarchicalGoalResult],
    *,
    as_of: datetime | None = None,
    half_life_days: float = 180.0,
    team_ridge: float = 0.5,
    competition_ridge: float = 2.0,
    learning_rate: float = 0.02,
    max_iterations: int = 4000,
    tolerance: float = 1e-8,
) -> HierarchicalPoissonModel:
    """Fit global, competition and team effects using chronological results.

    Ridge penalties partially pool sparse team effects toward their competition
    baseline. Hyperparameters must be selected on chronological development
    folds and frozen before prospective evaluation.
    """
    rows = list(results)
    if not rows:
        raise ValueError("at least one completed result is required")
    if (
        half_life_days <= 0
        or team_ridge < 0
        or competition_ridge < 0
        or learning_rate <= 0
        or max_iterations < 1
        or tolerance <= 0
    ):
        raise ValueError("invalid optimizer configuration")
    if len({row.fixture_id for row in rows}) != len(rows):
        raise ValueError("duplicate fixture IDs are not allowed")

    latest = as_of or max(row.kickoff_at for row in rows)
    if latest.tzinfo is None or latest.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if any(row.kickoff_at > latest for row in rows):
        raise ValueError("training result occurs after as_of")
    rows.sort(key=lambda row: (row.kickoff_at, row.fixture_id))

    teams = tuple(sorted({
        team
        for row in rows
        for team in (row.home_team_id, row.away_team_id)
    }))
    competitions = tuple(sorted({row.competition_id for row in rows}))
    team_index = {team: index for index, team in enumerate(teams)}
    competition_index = {
        competition: index for index, competition in enumerate(competitions)
    }
    team_count = len(teams)
    competition_count = len(competitions)

    weights = [
        _time_weight(
            (latest - row.kickoff_at).total_seconds() / 86400,
            half_life_days,
        )
        for row in rows
    ]
    total_weight = sum(weights)
    weighted_goals = sum(
        weight * (row.home_goals + row.away_goals)
        for row, weight in zip(rows, weights)
    )
    if total_weight <= 0 or weighted_goals <= 0:
        raise ValueError("training data has no positive weighted goal signal")

    global_intercept = log(weighted_goals / (2.0 * total_weight))
    home_advantage = 0.0
    competition_effects = [0.0] * competition_count
    attack = [0.0] * team_count
    defence = [0.0] * team_count

    for _ in range(max_iterations):
        grad_intercept = 0.0
        grad_home = 0.0
        grad_competition = [
            competition_ridge * value for value in competition_effects
        ]
        grad_attack = [team_ridge * value for value in attack]
        grad_defence = [team_ridge * value for value in defence]

        for row, weight in zip(rows, weights):
            home = team_index[row.home_team_id]
            away = team_index[row.away_team_id]
            competition = competition_index[row.competition_id]
            shared = global_intercept + competition_effects[competition]
            home_eta = max(
                -10.0,
                min(
                    10.0,
                    shared + home_advantage + attack[home] - defence[away],
                ),
            )
            away_eta = max(
                -10.0,
                min(10.0, shared + attack[away] - defence[home]),
            )
            home_error = weight * (exp(home_eta) - row.home_goals)
            away_error = weight * (exp(away_eta) - row.away_goals)

            grad_intercept += home_error + away_error
            grad_home += home_error
            grad_competition[competition] += home_error + away_error
            grad_attack[home] += home_error
            grad_defence[away] -= home_error
            grad_attack[away] += away_error
            grad_defence[home] -= away_error

        scale = 1.0 / total_weight
        gradients = [
            grad_intercept * scale,
            grad_home * scale,
            *[value * scale for value in grad_competition],
            *[value * scale for value in grad_attack],
            *[value * scale for value in grad_defence],
        ]
        if not all(isfinite(value) for value in gradients):
            raise ArithmeticError("non-finite optimizer gradient")
        if max(abs(value) for value in gradients) < tolerance:
            break

        global_intercept -= learning_rate * gradients[0]
        home_advantage -= learning_rate * gradients[1]
        offset = 2
        competition_effects = [
            value - learning_rate * gradient
            for value, gradient in zip(
                competition_effects,
                gradients[offset : offset + competition_count],
            )
        ]
        offset += competition_count
        attack = [
            value - learning_rate * gradient
            for value, gradient in zip(attack, gradients[offset : offset + team_count])
        ]
        offset += team_count
        defence = [
            value - learning_rate * gradient
            for value, gradient in zip(defence, gradients[offset:])
        ]

        weighted_competition_mean = sum(
            competition_effects[index]
            * sum(
                weight
                for row, weight in zip(rows, weights)
                if row.competition_id == competition
            )
            for index, competition in enumerate(competitions)
        ) / total_weight
        competition_effects = [
            value - weighted_competition_mean for value in competition_effects
        ]
        global_intercept += weighted_competition_mean

        attack_mean = sum(attack) / team_count
        defence_mean = sum(defence) / team_count
        attack = [value - attack_mean for value in attack]
        defence = [value - defence_mean for value in defence]

    team_match_counts = {team: 0 for team in teams}
    competition_match_counts = {competition: 0 for competition in competitions}
    for row in rows:
        team_match_counts[row.home_team_id] += 1
        team_match_counts[row.away_team_id] += 1
        competition_match_counts[row.competition_id] += 1

    return HierarchicalPoissonModel(
        global_intercept=global_intercept,
        competition_effects=dict(zip(competitions, competition_effects)),
        home_advantage=home_advantage,
        attack=dict(zip(teams, attack)),
        defence=dict(zip(teams, defence)),
        team_match_counts=team_match_counts,
        competition_match_counts=competition_match_counts,
        training_fixtures=len(rows),
        training_cutoff_at=latest,
        half_life_days=half_life_days,
        team_ridge=team_ridge,
        competition_ridge=competition_ridge,
    )
