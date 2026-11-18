"""Competition-aware, partially pooled Poisson goal-rate model.

Parameters are fitted by minimizing recency-weighted Poisson negative
log-likelihood plus ridge penalties. Weighted-zero-sum competition effects and
separately centered team attack/defence effects remove additive parameter
non-identifiability. Unseen teams receive zero team effects while retaining
learned competition/global context.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import exp, isfinite, lgamma, log, sqrt


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
        if any(not value.strip() for value in (
            self.fixture_id, self.competition_id, self.home_team_id, self.away_team_id
        )):
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
    optimizer_converged: bool
    optimizer_iterations: int
    optimizer_gradient_norm: float

    def predict(
        self, home_team_id: str, away_team_id: str, competition_id: str
    ) -> HierarchicalGoalRates:
        if not home_team_id or not away_team_id or not competition_id:
            raise ValueError("fixture identifiers are required")
        if home_team_id == away_team_id:
            raise ValueError("home and away teams must differ")
        competition_seen = competition_id in self.competition_effects
        shared = self.global_intercept + self.competition_effects.get(competition_id, 0.0)
        home_eta = (
            shared + self.home_advantage
            + self.attack.get(home_team_id, 0.0) - self.defence.get(away_team_id, 0.0)
        )
        away_eta = (
            shared + self.attack.get(away_team_id, 0.0)
            - self.defence.get(home_team_id, 0.0)
        )
        if not (-20.0 < home_eta < 20.0 and -20.0 < away_eta < 20.0):
            raise ArithmeticError("predicted goal-rate linear predictor outside safe range")
        return HierarchicalGoalRates(
            home_lambda=exp(home_eta),
            away_lambda=exp(away_eta),
            competition_seen=competition_seen,
            home_team_history=self.team_match_counts.get(home_team_id, 0),
            away_team_history=self.team_match_counts.get(away_team_id, 0),
        )


def _time_weight(age_days: float, half_life_days: float) -> float:
    return exp(-log(2.0) * max(0.0, age_days) / half_life_days)


def _objective(
    rows: list[HierarchicalGoalResult],
    weights: list[float],
    total_weight: float,
    team_index: dict[str, int],
    competition_index: dict[str, int],
    global_intercept: float,
    home_advantage: float,
    competition_effects: list[float],
    attack: list[float],
    defence: list[float],
    team_ridge: float,
    competition_ridge: float,
) -> float:
    loss = 0.0
    for row, weight in zip(rows, weights):
        home = team_index[row.home_team_id]
        away = team_index[row.away_team_id]
        comp = competition_index[row.competition_id]
        shared = global_intercept + competition_effects[comp]
        home_eta = shared + home_advantage + attack[home] - defence[away]
        away_eta = shared + attack[away] - defence[home]
        if not (-20.0 < home_eta < 20.0 and -20.0 < away_eta < 20.0):
            return float("inf")
        home_rate, away_rate = exp(home_eta), exp(away_eta)
        loss += weight * (
            home_rate - row.home_goals * home_eta + lgamma(row.home_goals + 1)
            + away_rate - row.away_goals * away_eta + lgamma(row.away_goals + 1)
        )
    penalty = 0.5 * competition_ridge * sum(value * value for value in competition_effects)
    penalty += 0.5 * team_ridge * (
        sum(value * value for value in attack) + sum(value * value for value in defence)
    )
    return loss / total_weight + penalty


def fit_hierarchical_poisson(
    results: Iterable[HierarchicalGoalResult],
    *,
    as_of: datetime | None = None,
    half_life_days: float = 180.0,
    team_ridge: float = 0.5,
    competition_ridge: float = 2.0,
    learning_rate: float = 1.0,
    max_iterations: int = 4000,
    tolerance: float = 1e-7,
) -> HierarchicalPoissonModel:
    """Fit the penalized likelihood with projected backtracking gradient descent.

    Hyperparameters are not production defaults; select them on chronological
    development folds and freeze them before prospective evaluation.
    """
    rows = list(results)
    if not rows:
        raise ValueError("at least one completed result is required")
    if (
        not isfinite(half_life_days) or half_life_days <= 0
        or not isfinite(team_ridge) or team_ridge < 0
        or not isfinite(competition_ridge) or competition_ridge < 0
        or not isfinite(learning_rate) or learning_rate <= 0
        or max_iterations < 1 or not isfinite(tolerance) or tolerance <= 0
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

    teams = tuple(sorted({team for row in rows for team in (row.home_team_id, row.away_team_id)}))
    competitions = tuple(sorted({row.competition_id for row in rows}))
    team_index = {team: index for index, team in enumerate(teams)}
    competition_index = {name: index for index, name in enumerate(competitions)}
    team_count, competition_count = len(teams), len(competitions)
    weights = [
        _time_weight((latest - row.kickoff_at).total_seconds() / 86400, half_life_days)
        for row in rows
    ]
    total_weight = sum(weights)
    weighted_goals = sum(
        weight * (row.home_goals + row.away_goals) for row, weight in zip(rows, weights)
    )
    if total_weight <= 0 or weighted_goals <= 0:
        raise ValueError("training data has no positive weighted goal signal")

    global_intercept = log(weighted_goals / (2.0 * total_weight))
    home_advantage = 0.0
    competition_effects = [0.0] * competition_count
    attack = [0.0] * team_count
    defence = [0.0] * team_count
    current_loss = _objective(
        rows, weights, total_weight, team_index, competition_index,
        global_intercept, home_advantage, competition_effects, attack, defence,
        team_ridge, competition_ridge,
    )
    converged = False
    gradient_norm = float("inf")
    iterations = 0

    for iteration in range(1, max_iterations + 1):
        gi = gh = 0.0
        gc = [competition_ridge * value for value in competition_effects]
        ga = [team_ridge * value for value in attack]
        gd = [team_ridge * value for value in defence]
        for row, weight in zip(rows, weights):
            h, a = team_index[row.home_team_id], team_index[row.away_team_id]
            c = competition_index[row.competition_id]
            shared = global_intercept + competition_effects[c]
            eh = shared + home_advantage + attack[h] - defence[a]
            ea = shared + attack[a] - defence[h]
            if not (-20.0 < eh < 20.0 and -20.0 < ea < 20.0):
                raise ArithmeticError("optimizer linear predictor outside safe range")
            error_h = weight * (exp(eh) - row.home_goals) / total_weight
            error_a = weight * (exp(ea) - row.away_goals) / total_weight
            gi += error_h + error_a
            gh += error_h
            gc[c] += error_h + error_a
            ga[h] += error_h
            gd[a] -= error_h
            ga[a] += error_a
            gd[h] -= error_a
        gradient_norm = sqrt(
            gi * gi + gh * gh + sum(x*x for x in gc)
            + sum(x*x for x in ga) + sum(x*x for x in gd)
        )
        if not isfinite(gradient_norm):
            raise ArithmeticError("non-finite optimizer gradient")
        if gradient_norm <= tolerance:
            converged = True
            iterations = iteration
            break

        step = learning_rate
        accepted = False
        for _ in range(40):
            next_intercept = global_intercept - step * gi
            next_home = home_advantage - step * gh
            next_comp = [v - step * g for v, g in zip(competition_effects, gc)]
            next_attack = [v - step * g for v, g in zip(attack, ga)]
            next_defence = [v - step * g for v, g in zip(defence, gd)]

            comp_weights = [
                sum(w for row, w in zip(rows, weights) if row.competition_id == name)
                for name in competitions
            ]
            comp_mean = sum(v * w for v, w in zip(next_comp, comp_weights)) / total_weight
            next_comp = [v - comp_mean for v in next_comp]
            next_intercept += comp_mean
            attack_mean = sum(next_attack) / team_count
            defence_mean = sum(next_defence) / team_count
            next_attack = [v - attack_mean for v in next_attack]
            next_defence = [v - defence_mean for v in next_defence]

            next_loss = _objective(
                rows, weights, total_weight, team_index, competition_index,
                next_intercept, next_home, next_comp, next_attack, next_defence,
                team_ridge, competition_ridge,
            )
            if isfinite(next_loss) and next_loss < current_loss:
                global_intercept, home_advantage = next_intercept, next_home
                competition_effects, attack, defence = next_comp, next_attack, next_defence
                current_loss = next_loss
                accepted = True
                break
            step *= 0.5
        if not accepted:
            if gradient_norm <= tolerance * 10:
                converged = True
                iterations = iteration
                break
            raise ArithmeticError("optimizer line search failed before convergence")
        iterations = iteration

    if not converged:
        raise ArithmeticError(
            f"hierarchical Poisson optimizer did not converge after {max_iterations} iterations "
            f"(gradient_norm={gradient_norm:.6g})"
        )

    team_counts = {team: 0 for team in teams}
    competition_counts = {name: 0 for name in competitions}
    for row in rows:
        team_counts[row.home_team_id] += 1
        team_counts[row.away_team_id] += 1
        competition_counts[row.competition_id] += 1
    return HierarchicalPoissonModel(
        global_intercept=global_intercept,
        competition_effects=dict(zip(competitions, competition_effects)),
        home_advantage=home_advantage,
        attack=dict(zip(teams, attack)),
        defence=dict(zip(teams, defence)),
        team_match_counts=team_counts,
        competition_match_counts=competition_counts,
        training_fixtures=len(rows),
        training_cutoff_at=latest,
        half_life_days=half_life_days,
        team_ridge=team_ridge,
        competition_ridge=competition_ridge,
        optimizer_converged=converged,
        optimizer_iterations=iterations,
        optimizer_gradient_norm=gradient_norm,
    )
