"""Regularized, recency-weighted attack/defence Poisson goal model.

This is a retrospective research component. It estimates team attack and
concession strengths from completed results only; callers must construct each
training window chronologically and must never pass post-cutoff fixtures.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import exp, isfinite, log


@dataclass(frozen=True, slots=True)
class GoalResult:
    fixture_id: str
    kickoff_at: datetime
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int

    def __post_init__(self) -> None:
        if not self.fixture_id or not self.home_team or not self.away_team:
            raise ValueError("fixture and team identifiers are required")
        if self.home_team == self.away_team:
            raise ValueError("home and away teams must differ")
        if self.kickoff_at.tzinfo is None or self.kickoff_at.utcoffset() is None:
            raise ValueError("kickoff_at must be timezone-aware")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("goals cannot be negative")


@dataclass(frozen=True, slots=True)
class GoalRates:
    home_lambda: float
    away_lambda: float


@dataclass(frozen=True, slots=True)
class AttackDefenceModel:
    intercept: float
    home_advantage: float
    attack: dict[str, float]
    defence: dict[str, float]
    teams: tuple[str, ...]
    training_fixtures: int
    half_life_days: float
    ridge: float

    def predict(self, home_team: str, away_team: str) -> GoalRates:
        if not home_team or not away_team or home_team == away_team:
            raise ValueError("distinct home and away team identifiers are required")
        # An unseen team contributes a neutral, zero-centered effect. This
        # retains the fitted scoring environment and home advantage without
        # fabricating a team-strength estimate or rejecting sparse fixtures.
        home_eta = (
            self.intercept + self.home_advantage
            + self.attack.get(home_team, 0.0) - self.defence.get(away_team, 0.0)
        )
        away_eta = (
            self.intercept
            + self.attack.get(away_team, 0.0) - self.defence.get(home_team, 0.0)
        )
        return GoalRates(
            exp(max(-4.0, min(4.0, home_eta))),
            exp(max(-4.0, min(4.0, away_eta))),
        )


def _weight(age_days: float, half_life_days: float) -> float:
    return exp(-log(2.0) * max(0.0, age_days) / half_life_days)


def fit_attack_defence(
    results: Iterable[GoalResult],
    *,
    as_of: datetime | None = None,
    half_life_days: float = 180.0,
    ridge: float = 0.08,
    learning_rate: float = 0.025,
    max_iterations: int = 3000,
    tolerance: float = 1e-8,
) -> AttackDefenceModel:
    """Fit weighted Poisson attack/defence strengths with ridge shrinkage.

    Exponential time decay gives recent matches more influence. Team effects
    are centered after each update to make the parameterization identifiable.
    """
    rows = list(results)
    if not rows:
        raise ValueError("at least one completed result is required")
    if half_life_days <= 0 or ridge < 0 or learning_rate <= 0 or max_iterations < 1:
        raise ValueError("invalid optimizer configuration")
    if len({row.fixture_id for row in rows}) != len(rows):
        raise ValueError("duplicate fixture IDs are not allowed")
    latest = as_of or max(row.kickoff_at for row in rows)
    if latest.tzinfo is None or latest.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if any(row.kickoff_at > latest for row in rows):
        raise ValueError("training result occurs after as_of")
    rows.sort(key=lambda row: (row.kickoff_at, row.fixture_id))
    teams = tuple(sorted({r.home_team for r in rows} | {r.away_team for r in rows}))
    index = {team: i for i, team in enumerate(teams)}
    n = len(teams)
    attack = [0.0] * n
    defence = [0.0] * n
    weighted_goals = sum(
        _weight((latest - row.kickoff_at).total_seconds() / 86400, half_life_days)
        * (row.home_goals + row.away_goals)
        for row in rows
    )
    total_weight = sum(
        _weight((latest - row.kickoff_at).total_seconds() / 86400, half_life_days)
        for row in rows
    )
    mean_rate = max(0.05, weighted_goals / max(1.0, 2.0 * total_weight))
    intercept = log(mean_rate)
    home_advantage = 0.12

    for _ in range(max_iterations):
        grad_a = [ridge * value for value in attack]
        grad_d = [ridge * value for value in defence]
        grad_mu = 0.0
        grad_home = 0.0
        for row in rows:
            age = (latest - row.kickoff_at).total_seconds() / 86400
            weight = _weight(age, half_life_days)
            h, a = index[row.home_team], index[row.away_team]
            eta_h = max(-4.0, min(4.0, intercept + home_advantage + attack[h] - defence[a]))
            eta_a = max(-4.0, min(4.0, intercept + attack[a] - defence[h]))
            err_h = weight * (exp(eta_h) - row.home_goals)
            err_a = weight * (exp(eta_a) - row.away_goals)
            grad_mu += err_h + err_a
            grad_home += err_h
            grad_a[h] += err_h
            grad_d[a] -= err_h
            grad_a[a] += err_a
            grad_d[h] -= err_a
        scale = 1.0 / max(1.0, total_weight)
        gradients = [g * scale for g in (grad_mu, grad_home)]
        gradients.extend(
            g * scale + ridge * value for g, value in zip(grad_a, attack)
        )
        gradients.extend(
            g * scale + ridge * value for g, value in zip(grad_d, defence)
        )
        if not all(isfinite(g) for g in gradients):
            raise ArithmeticError("non-finite optimizer gradient")
        if max(abs(g) for g in gradients) < tolerance:
            break
        intercept -= learning_rate * gradients[0]
        home_advantage -= learning_rate * gradients[1]
        attack = [v - learning_rate * g for v, g in zip(attack, gradients[2:2+n])]
        defence = [v - learning_rate * g for v, g in zip(defence, gradients[2+n:])]
        mean_attack = sum(attack) / n
        mean_defence = sum(defence) / n
        attack = [v - mean_attack for v in attack]
        defence = [v - mean_defence for v in defence]

    return AttackDefenceModel(
        intercept=intercept,
        home_advantage=home_advantage,
        attack=dict(zip(teams, attack)),
        defence=dict(zip(teams, defence)),
        teams=teams,
        training_fixtures=len(rows),
        half_life_days=half_life_days,
        ridge=ridge,
    )
