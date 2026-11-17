"""Poisson scoreline probabilities and Dixon-Coles low-score dependence."""
from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite


@dataclass(frozen=True, slots=True)
class ScorelineDistribution:
    home_lambda: float
    away_lambda: float
    rho: float
    probabilities: tuple[tuple[float, ...], ...]
    normalization_mass_before: float

    @property
    def home_win(self) -> float:
        return sum(self.probabilities[h][a] for h in range(len(self.probabilities)) for a in range(len(self.probabilities[h])) if h > a)

    @property
    def draw(self) -> float:
        return sum(self.probabilities[g][g] for g in range(min(len(self.probabilities), len(self.probabilities[0]))))

    @property
    def away_win(self) -> float:
        return sum(self.probabilities[h][a] for h in range(len(self.probabilities)) for a in range(len(self.probabilities[h])) if h < a)

    @property
    def btts_yes(self) -> float:
        return sum(self.probabilities[h][a] for h in range(1, len(self.probabilities)) for a in range(1, len(self.probabilities[h])))

    def over(self, line: float) -> float:
        if not isfinite(line):
            raise ValueError("line must be finite")
        return sum(
            self.probabilities[h][a]
            for h in range(len(self.probabilities))
            for a in range(len(self.probabilities[h]))
            if h + a > line
        )

    def under(self, line: float) -> float:
        return 1.0 - self.over(line)

    def market_probabilities(self) -> dict[str, dict[str, float]]:
        return {
            "1X2": {"HOME": self.home_win, "DRAW": self.draw, "AWAY": self.away_win},
            "BTTS": {"YES": self.btts_yes, "NO": 1.0 - self.btts_yes},
            "TOTALS_1_5": {"OVER": self.over(1.5), "UNDER": self.under(1.5)},
            "TOTALS_2_5": {"OVER": self.over(2.5), "UNDER": self.under(2.5)},
            "TOTALS_3_5": {"OVER": self.over(3.5), "UNDER": self.under(3.5)},
        }


def _poisson_pmf(rate: float, maximum: int) -> list[float]:
    probabilities = [exp(-rate)]
    for goals in range(1, maximum + 1):
        probabilities.append(probabilities[-1] * rate / goals)
    return probabilities


def _safe_rho(home_lambda: float, away_lambda: float, requested_rho: float) -> float:
    """Clamp rho to keep all four Dixon-Coles correction factors nonnegative."""
    lower = max(-1.0 / home_lambda, -1.0 / away_lambda, -1.0)
    upper = 1.0 / (home_lambda * away_lambda)
    return min(upper, max(lower, requested_rho))


def build_scoreline_distribution(
    home_lambda: float,
    away_lambda: float,
    *,
    rho: float = 0.0,
    max_goals: int = 12,
) -> ScorelineDistribution:
    """Build a normalized score matrix; rho=0 is independent Poisson.

    The finite goal grid is explicitly truncated and renormalized. Callers should
    inspect normalization_mass_before when selecting a cap for unusually high rates.
    """
    for name, value in (("home_lambda", home_lambda), ("away_lambda", away_lambda), ("rho", rho)):
        if not isfinite(value):
            raise ValueError(f"{name} must be finite")
    if home_lambda <= 0 or away_lambda <= 0:
        raise ValueError("goal rates must be strictly positive")
    if max_goals < 2:
        raise ValueError("max_goals must be at least 2 for Dixon-Coles correction")

    home = _poisson_pmf(home_lambda, max_goals)
    away = _poisson_pmf(away_lambda, max_goals)
    matrix = [[home[h] * away[a] for a in range(max_goals + 1)] for h in range(max_goals + 1)]
    mass_before = sum(sum(row) for row in matrix)
    adjusted_rho = _safe_rho(home_lambda, away_lambda, rho)

    corrections = {
        (0, 0): 1.0 - home_lambda * away_lambda * adjusted_rho,
        (0, 1): 1.0 + home_lambda * adjusted_rho,
        (1, 0): 1.0 + away_lambda * adjusted_rho,
        (1, 1): 1.0 - adjusted_rho,
    }
    for (h, a), factor in corrections.items():
        matrix[h][a] *= max(0.0, factor)

    total = sum(sum(row) for row in matrix)
    if not isfinite(total) or total <= 0:
        raise ArithmeticError("scoreline matrix has no positive finite probability mass")
    normalized = tuple(tuple(value / total for value in row) for row in matrix)
    return ScorelineDistribution(
        home_lambda=home_lambda,
        away_lambda=away_lambda,
        rho=adjusted_rho,
        probabilities=normalized,
        normalization_mass_before=mass_before,
    )
