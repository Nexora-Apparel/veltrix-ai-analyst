"""Unnormalized pseudo-match-regularized hierarchical Poisson candidate.

This module is research-only and is not wired into production inference.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import exp, isfinite, lgamma, log, sqrt

from app.models.hierarchical_poisson import (
    HierarchicalGoalRates,
    HierarchicalGoalResult,
)
from app.models.regularization_contract import regularization_scales


@dataclass(frozen=True, slots=True)
class HierarchicalPoissonV2Model:
    global_intercept: float
    competition_effects: dict[str, float]
    home_advantage_global: float
    home_advantage_deviations: dict[str, float]
    attack: dict[tuple[str, str], float]
    defence: dict[tuple[str, str], float]
    team_match_counts: dict[tuple[str, str], int]
    competition_match_counts: dict[str, int]
    league_mean_goals: dict[str, float]
    pooled_mean_goals: float
    training_fixtures: int
    training_cutoff_at: datetime
    half_life_days: float
    k_team: float
    k_competition: float
    k_home_competition: float
    k_home_global: float
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
        home_key = (competition_id, home_team_id)
        away_key = (competition_id, away_team_id)
        competition_seen = competition_id in self.competition_effects
        shared = self.global_intercept + self.competition_effects.get(competition_id, 0.0)
        home_eta = (
            shared
            + self.home_advantage_global
            + self.home_advantage_deviations.get(competition_id, 0.0)
            + self.attack.get(home_key, 0.0)
            - self.defence.get(away_key, 0.0)
        )
        away_eta = (
            shared
            + self.attack.get(away_key, 0.0)
            - self.defence.get(home_key, 0.0)
        )
        if not (-20.0 < home_eta < 20.0 and -20.0 < away_eta < 20.0):
            raise ArithmeticError("predicted goal-rate linear predictor outside safe range")
        home_history = self.team_match_counts.get(home_key, 0)
        away_history = self.team_match_counts.get(away_key, 0)
        if competition_seen and home_history > 0 and away_history > 0:
            mode = "TEAM_AND_COMPETITION_HISTORY"
        elif competition_seen and (home_history > 0 or away_history > 0):
            mode = "ONE_SIDED_TEAM_HISTORY"
        elif competition_seen:
            mode = "COMPETITION_ONLY"
        elif home_history > 0 or away_history > 0:
            mode = "TEAM_HISTORY_GLOBAL_CONTEXT"
        else:
            mode = "GLOBAL_CONTEXT_ONLY"
        return HierarchicalGoalRates(
            home_lambda=exp(home_eta),
            away_lambda=exp(away_eta),
            competition_seen=competition_seen,
            home_team_history=home_history,
            away_team_history=away_history,
            calculation_mode=mode,
        )


def _time_weight(age_days: float, half_life_days: float) -> float:
    return exp(-log(2.0) * max(0.0, age_days) / half_life_days)


def fit_hierarchical_poisson_v2(
    results: Iterable[HierarchicalGoalResult],
    *,
    as_of: datetime | None = None,
    half_life_days: float,
    k_team: float,
    k_competition: float,
    k_home_competition: float,
    k_home_global: float,
    learning_rate: float = 1.0,
    max_iterations: int = 4000,
    tolerance: float = 1e-6,
) -> HierarchicalPoissonV2Model:
    """Fit the unnormalized likelihood with common pseudo-match prior strengths.

    k values are mandatory inputs: this candidate intentionally has no
    unvalidated production defaults. Team parameters are competition-scoped.
    """
    rows = list(results)
    if not rows:
        raise ValueError("at least one completed result is required")
    if (
        not isfinite(half_life_days) or half_life_days <= 0
        or any(not isfinite(value) or value < 0 for value in (
            k_team, k_competition, k_home_competition, k_home_global
        ))
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

    competitions = tuple(sorted({row.competition_id for row in rows}))
    team_keys = tuple(sorted({
        (row.competition_id, team)
        for row in rows
        for team in (row.home_team_id, row.away_team_id)
    }))
    team_index = {key: index for index, key in enumerate(team_keys)}
    competition_index = {name: index for index, name in enumerate(competitions)}
    weights = [
        _time_weight((latest - row.kickoff_at).total_seconds() / 86400.0, half_life_days)
        for row in rows
    ]
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("training data has no positive recency weight")

    competition_weight = {name: 0.0 for name in competitions}
    competition_goals = {name: 0.0 for name in competitions}
    for row, weight in zip(rows, weights):
        competition_weight[row.competition_id] += weight
        competition_goals[row.competition_id] += weight * (row.home_goals + row.away_goals)
    league_mean_goals = {
        name: competition_goals[name] / (2.0 * competition_weight[name])
        for name in competitions
    }
    if any(not value > 0 for value in league_mean_goals.values()):
        raise ValueError("each competition needs a positive weighted goal rate")
    pooled_mean_goals = sum(competition_goals.values()) / (2.0 * total_weight)

    scales = {
        name: regularization_scales(
            league_mean_goals=league_mean_goals[name],
            pooled_mean_goals=pooled_mean_goals,
            k_team=k_team,
            k_competition=k_competition,
            k_home_competition=k_home_competition,
            k_home_global=k_home_global,
        )
        for name in competitions
    }
    team_tau = {
        key: scales[key[0]].team_attack_tau for key in team_keys
    }
    competition_tau = {
        name: scales[name].competition_tau for name in competitions
    }
    home_tau = {
        name: scales[name].competition_home_tau for name in competitions
    }
    global_home_tau = regularization_scales(
        league_mean_goals=pooled_mean_goals,
        pooled_mean_goals=pooled_mean_goals,
        k_team=k_team,
        k_competition=k_competition,
        k_home_competition=k_home_competition,
        k_home_global=k_home_global,
    ).global_home_tau

    weighted_goals = sum(competition_goals.values())
    if weighted_goals <= 0:
        raise ValueError("training data has no positive weighted goal signal")
    global_intercept = log(weighted_goals / (2.0 * total_weight))
    home_global = 0.0
    competition_effects = [0.0] * len(competitions)
    home_deviations = [0.0] * len(competitions)
    attack = [0.0] * len(team_keys)
    defence = [0.0] * len(team_keys)

    def objective(
        intercept: float,
        home_base: float,
        comp_values: list[float],
        home_values: list[float],
        attack_values: list[float],
        defence_values: list[float],
    ) -> float:
        loss = 0.0
        for row, weight in zip(rows, weights):
            comp = competition_index[row.competition_id]
            home = team_index[(row.competition_id, row.home_team_id)]
            away = team_index[(row.competition_id, row.away_team_id)]
            shared = intercept + comp_values[comp]
            home_eta = (
                shared + home_base + home_values[comp]
                + attack_values[home] - defence_values[away]
            )
            away_eta = shared + attack_values[away] - defence_values[home]
            if not (-20.0 < home_eta < 20.0 and -20.0 < away_eta < 20.0):
                return float("inf")
            home_rate, away_rate = exp(home_eta), exp(away_eta)
            loss += weight * (
                home_rate - row.home_goals * home_eta + lgamma(row.home_goals + 1)
                + away_rate - row.away_goals * away_eta + lgamma(row.away_goals + 1)
            )
        loss += 0.5 * global_home_tau * home_base * home_base
        loss += 0.5 * sum(
            competition_tau[name] * comp_values[index] ** 2
            for index, name in enumerate(competitions)
        )
        loss += 0.5 * sum(
            home_tau[name] * home_values[index] ** 2
            for index, name in enumerate(competitions)
        )
        loss += 0.5 * sum(
            team_tau[key] * (attack_values[index] ** 2 + defence_values[index] ** 2)
            for index, key in enumerate(team_keys)
        )
        return loss

    current_loss = objective(
        global_intercept, home_global, competition_effects, home_deviations, attack, defence
    )
    converged = False
    gradient_norm = float("inf")
    iterations = 0

    for iteration in range(1, max_iterations + 1):
        gi = gh0 = 0.0
        gc = [
            competition_tau[name] * competition_effects[index]
            for index, name in enumerate(competitions)
        ]
        gh = [
            home_tau[name] * home_deviations[index]
            for index, name in enumerate(competitions)
        ]
        ga = [team_tau[key] * attack[index] for index, key in enumerate(team_keys)]
        gd = [team_tau[key] * defence[index] for index, key in enumerate(team_keys)]

        # Diagonal Fisher information provides parameter-specific scaling. The
        # line search still evaluates the full unnormalized objective.
        hi = 0.0
        hh0 = global_home_tau
        hc = [competition_tau[name] for name in competitions]
        hh = [home_tau[name] for name in competitions]
        ha = [team_tau[key] for key in team_keys]
        hd = [team_tau[key] for key in team_keys]

        for row, weight in zip(rows, weights):
            comp = competition_index[row.competition_id]
            home = team_index[(row.competition_id, row.home_team_id)]
            away = team_index[(row.competition_id, row.away_team_id)]
            shared = global_intercept + competition_effects[comp]
            home_eta = (
                shared + home_global + home_deviations[comp]
                + attack[home] - defence[away]
            )
            away_eta = shared + attack[away] - defence[home]
            if not (-20.0 < home_eta < 20.0 and -20.0 < away_eta < 20.0):
                raise ArithmeticError("optimizer linear predictor outside safe range")
            home_rate = exp(home_eta)
            away_rate = exp(away_eta)
            error_home = weight * (home_rate - row.home_goals)
            error_away = weight * (away_rate - row.away_goals)
            gi += error_home + error_away
            gh0 += error_home
            gc[comp] += error_home + error_away
            gh[comp] += error_home
            ga[home] += error_home
            gd[away] -= error_home
            ga[away] += error_away
            gd[home] -= error_away

            home_information = weight * home_rate
            away_information = weight * away_rate
            hi += home_information + away_information
            hh0 += home_information
            hc[comp] += home_information + away_information
            hh[comp] += home_information
            ha[home] += home_information
            hd[away] += home_information
            ha[away] += away_information
            hd[home] += away_information

        gradient_norm = sqrt(
            gi * gi + gh0 * gh0 + sum(value * value for value in gc)
            + sum(value * value for value in gh) + sum(value * value for value in ga)
            + sum(value * value for value in gd)
        ) / total_weight
        if not isfinite(gradient_norm):
            raise ArithmeticError("non-finite optimizer gradient")
        if gradient_norm <= tolerance:
            converged = True
            iterations = iteration
            break

        direction_intercept = gi / max(hi, 1e-12)
        direction_home_global = gh0 / max(hh0, 1e-12)
        direction_comp = [
            grad / max(info, 1e-12) for grad, info in zip(gc, hc)
        ]
        direction_home = [
            grad / max(info, 1e-12) for grad, info in zip(gh, hh)
        ]
        direction_attack = [
            grad / max(info, 1e-12) for grad, info in zip(ga, ha)
        ]
        direction_defence = [
            grad / max(info, 1e-12) for grad, info in zip(gd, hd)
        ]

        step = learning_rate
        accepted = False
        for _ in range(40):
            next_intercept = global_intercept - step * direction_intercept
            next_home_global = home_global - step * direction_home_global
            next_comp = [
                value - step * direction
                for value, direction in zip(competition_effects, direction_comp)
            ]
            next_home = [
                value - step * direction
                for value, direction in zip(home_deviations, direction_home)
            ]
            next_attack = [
                value - step * direction
                for value, direction in zip(attack, direction_attack)
            ]
            next_defence = [
                value - step * direction
                for value, direction in zip(defence, direction_defence)
            ]
            next_loss = objective(
                next_intercept, next_home_global, next_comp, next_home, next_attack, next_defence
            )
            if isfinite(next_loss) and next_loss < current_loss:
                global_intercept = next_intercept
                home_global = next_home_global
                competition_effects = next_comp
                home_deviations = next_home
                attack = next_attack
                defence = next_defence
                current_loss = next_loss
                accepted = True
                break
            step *= 0.5
        if not accepted:
            if gradient_norm <= tolerance * 10:
                converged = True
                iterations = iteration
                break
            raise ArithmeticError(
                "optimizer line search failed before convergence "
                f"(iteration={iteration}, gradient_norm={gradient_norm:.8g})"
            )
        iterations = iteration
    if not converged:
        raise ArithmeticError(
            f"hierarchical Poisson v2 optimizer did not converge after {max_iterations} "
            f"iterations (gradient_norm={gradient_norm:.6g})"
        )

    team_counts = {key: 0 for key in team_keys}
    competition_counts = {name: 0 for name in competitions}
    for row in rows:
        team_counts[(row.competition_id, row.home_team_id)] += 1
        team_counts[(row.competition_id, row.away_team_id)] += 1
        competition_counts[row.competition_id] += 1

    return HierarchicalPoissonV2Model(
        global_intercept=global_intercept,
        competition_effects=dict(zip(competitions, competition_effects)),
        home_advantage_global=home_global,
        home_advantage_deviations=dict(zip(competitions, home_deviations)),
        attack=dict(zip(team_keys, attack)),
        defence=dict(zip(team_keys, defence)),
        team_match_counts=team_counts,
        competition_match_counts=competition_counts,
        league_mean_goals=league_mean_goals,
        pooled_mean_goals=pooled_mean_goals,
        training_fixtures=len(rows),
        training_cutoff_at=latest,
        half_life_days=half_life_days,
        k_team=k_team,
        k_competition=k_competition,
        k_home_competition=k_home_competition,
        k_home_global=k_home_global,
        optimizer_converged=converged,
        optimizer_iterations=iterations,
        optimizer_gradient_norm=gradient_norm,
    )
