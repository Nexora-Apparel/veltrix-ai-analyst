"""Shared pseudo-match regularization scales for the hierarchical goal model."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class RegularizationScales:
    team_attack_tau: float
    team_defence_tau: float
    competition_tau: float
    competition_home_tau: float
    global_home_tau: float


def regularization_scales(
    *,
    league_mean_goals: float,
    pooled_mean_goals: float,
    k_team: float,
    k_competition: float,
    k_home_competition: float,
    k_home_global: float,
) -> RegularizationScales:
    """Convert common pseudo-match strengths into parameter precisions.

    Team attack/defence each affect one goal observation per fixture (mu).
    A competition scoring effect affects both teams' goal observations (2*mu).
    A competition home deviation affects only the home-goal observation (mu).
    The global home effect has its own explicit zero-centred prior.
    """
    values = (
        league_mean_goals,
        pooled_mean_goals,
        k_team,
        k_competition,
        k_home_competition,
        k_home_global,
    )
    if any(not isfinite(value) for value in values):
        raise ValueError("REGULARIZATION_SCALE_INPUTS_MUST_BE_FINITE")
    if league_mean_goals <= 0 or pooled_mean_goals <= 0:
        raise ValueError("GOAL_RATE_MUST_BE_POSITIVE")
    if any(value < 0 for value in values[2:]):
        raise ValueError("PSEUDO_MATCH_STRENGTH_MUST_BE_NON_NEGATIVE")

    team_tau = k_team * league_mean_goals
    return RegularizationScales(
        team_attack_tau=team_tau,
        team_defence_tau=team_tau,
        competition_tau=k_competition * 2.0 * league_mean_goals,
        competition_home_tau=k_home_competition * league_mean_goals,
        global_home_tau=k_home_global * pooled_mean_goals,
    )
