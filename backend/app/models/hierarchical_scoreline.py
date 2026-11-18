"""Connect hierarchical sparse-team goal rates to the Dixon-Coles score engine."""
from __future__ import annotations

from dataclasses import dataclass

from app.models.hierarchical_poisson import (
    HierarchicalGoalRates,
    HierarchicalPoissonModel,
)
from app.models.scoreline import ScorelineDistribution, build_scoreline_distribution


@dataclass(frozen=True, slots=True)
class HierarchicalFixtureForecast:
    rates: HierarchicalGoalRates
    scoreline: ScorelineDistribution

    @property
    def markets(self) -> dict[str, dict[str, float]]:
        return self.scoreline.market_probabilities()


def forecast_hierarchical_fixture(
    model: HierarchicalPoissonModel,
    home_team_id: str,
    away_team_id: str,
    competition_id: str,
    *,
    rho: float,
    max_goals: int = 12,
) -> HierarchicalFixtureForecast:
    """Generate market probabilities only from fitted expected-goal rates.

    rho must be estimated/frozen using chronological development data. It is
    deliberately explicit here; this adapter does not invent a Dixon-Coles
    dependence parameter for sparse fixtures.
    """
    rates = model.predict(home_team_id, away_team_id, competition_id)
    distribution = build_scoreline_distribution(
        rates.home_lambda,
        rates.away_lambda,
        rho=rho,
        max_goals=max_goals,
    )
    return HierarchicalFixtureForecast(rates=rates, scoreline=distribution)
