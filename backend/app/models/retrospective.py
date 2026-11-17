"""Retrospective, provider-local football model training utilities.

This research pipeline intentionally uses historical results to construct lagged
features. It is NOT a point-in-time-certified replay and must never be represented
as evidence that a feature was available at an original historical cutoff.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import exp, isfinite, log
from typing import Iterable, Sequence

from app.models.elo import EloConfig, EloSystem, HistoricalResult
from app.models.scoreline import build_scoreline_distribution


@dataclass(frozen=True, slots=True)
class ResearchFixture:
    fixture_id: str
    kickoff_at: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int

    def __post_init__(self) -> None:
        HistoricalResult(
            self.fixture_id, self.kickoff_at, self.home_team_id,
            self.away_team_id, self.home_goals, self.away_goals,
        )


@dataclass(frozen=True, slots=True)
class TeamRecord:
    team_id: str
    goals_for: int
    goals_against: int
    matches: int


@dataclass(frozen=True, slots=True)
class ResearchPrediction:
    fixture_id: str
    kickoff_at: datetime
    actual_home_goals: int
    actual_away_goals: int
    elo_home: float
    elo_draw: float
    elo_away: float
    poisson_home: float
    poisson_draw: float
    poisson_away: float
    home_lambda: float
    away_lambda: float
    rho: float


class HistoricalRateModel:
    """Smoothed lagged attack/defence rates with optional exponential recency decay."""

    def __init__(self, *, prior_matches: float = 6.0, half_life_days: float = 180.0) -> None:
        if prior_matches <= 0 or half_life_days <= 0:
            raise ValueError("prior_matches and half_life_days must be positive")
        self.prior_matches = prior_matches
        self.half_life_days = half_life_days

    def rates(
        self, history: Sequence[ResearchFixture], fixture: ResearchFixture
    ) -> tuple[float, float]:
        if not history:
            return 1.35, 1.10
        home_for = defaultdict(float)
        home_against = defaultdict(float)
        away_for = defaultdict(float)
        away_against = defaultdict(float)
        home_n = defaultdict(float)
        away_n = defaultdict(float)
        league_home = league_away = total_weight = 0.0
        for row in history:
            if row.kickoff_at >= fixture.kickoff_at:
                raise ValueError("history must be strictly earlier than target kickoff")
            age_days = max(0.0, (fixture.kickoff_at - row.kickoff_at).total_seconds() / 86400)
            weight = 2.0 ** (-age_days / self.half_life_days)
            league_home += row.home_goals * weight
            league_away += row.away_goals * weight
            total_weight += weight
            home_for[row.home_team_id] += row.home_goals * weight
            home_against[row.home_team_id] += row.away_goals * weight
            home_n[row.home_team_id] += weight
            away_for[row.away_team_id] += row.away_goals * weight
            away_against[row.away_team_id] += row.home_goals * weight
            away_n[row.away_team_id] += weight
        if total_weight <= 0:
            return 1.35, 1.10
        avg_home = max(0.2, league_home / total_weight)
        avg_away = max(0.2, league_away / total_weight)
        avg_team = max(0.2, (league_home + league_away) / (2.0 * total_weight))
        prior = self.prior_matches

        def smoothed(total: float, count: float, baseline: float) -> float:
            return (total + prior * baseline) / (count + prior)

        h_att = smoothed(home_for[fixture.home_team_id], home_n[fixture.home_team_id], avg_home) / avg_home
        h_def = smoothed(home_against[fixture.home_team_id], home_n[fixture.home_team_id], avg_away) / avg_away
        a_att = smoothed(away_for[fixture.away_team_id], away_n[fixture.away_team_id], avg_away) / avg_away
        a_def = smoothed(away_against[fixture.away_team_id], away_n[fixture.away_team_id], avg_home) / avg_home
        home_rate = avg_home * h_att * a_def
        away_rate = avg_away * a_att * h_def
        return min(4.5, max(0.15, home_rate)), min(4.5, max(0.15, away_rate))


def fit_dixon_coles_rho(
    fixtures: Sequence[ResearchFixture],
    *,
    prior_matches: float = 6.0,
    half_life_days: float = 180.0,
) -> float:
    """Select rho by training-set scoreline likelihood over a conservative grid."""
    if len(fixtures) < 30:
        return 0.0
    ordered = sorted(fixtures, key=lambda row: (row.kickoff_at, row.fixture_id))
    model = HistoricalRateModel(prior_matches=prior_matches, half_life_days=half_life_days)
    history: list[ResearchFixture] = []
    candidates = tuple(i / 1000 for i in range(-180, 181, 10))
    losses = {rho: 0.0 for rho in candidates}
    count = 0
    for row in ordered:
        if history:
            home_rate, away_rate = model.rates(history, row)
            for rho in candidates:
                matrix = build_scoreline_distribution(home_rate, away_rate, rho=rho, max_goals=10)
                probability = matrix.probabilities[row.home_goals][row.away_goals] if max(row.home_goals, row.away_goals) <= 10 else 1e-15
                losses[rho] -= log(max(1e-15, probability))
            count += 1
        history.append(row)
    if count == 0:
        return 0.0
    return min(candidates, key=lambda rho: (losses[rho], abs(rho)))


def _elo_probabilities(
    system: EloSystem, home: str, away: str, history: Sequence[ResearchFixture]
) -> tuple[float, float, float]:
    expected = system.expected_home_score(home, away)
    # Estimate draw frequency from prior results with Bayesian shrinkage.
    # Convert Elo expected score into coherent H/D/A probabilities.
    draws = sum(row.home_goals == row.away_goals for row in history)
    prior_matches = 8.0
    draw = (draws + prior_matches * 0.26) / (len(history) + prior_matches)
    draw = min(draw, 2.0 * min(expected, 1.0 - expected))
    home_probability = max(0.0, expected - 0.5 * draw)
    away_probability = max(0.0, 1.0 - expected - 0.5 * draw)
    total = home_probability + draw + away_probability
    return home_probability / total, draw / total, away_probability / total


def _actual_index(row: ResearchFixture) -> int:
    return 0 if row.home_goals > row.away_goals else 1 if row.home_goals == row.away_goals else 2


def _log_loss(actual: int, probs: Sequence[float]) -> float:
    return -log(max(1e-15, probs[actual]))


def _brier(actual: int, probs: Sequence[float]) -> float:
    return sum((p - (1.0 if i == actual else 0.0)) ** 2 for i, p in enumerate(probs))


def chronological_research_run(
    fixtures: Iterable[ResearchFixture],
    *,
    elo_config: EloConfig | None = None,
    prior_matches: float = 6.0,
    half_life_days: float = 180.0,
    ensemble_elo_weight: float = 0.35,
) -> dict[str, object]:
    """Generate honest forward-in-time predictions within the available result history."""
    if not 0.0 <= ensemble_elo_weight <= 1.0:
        raise ValueError("ensemble_elo_weight must be between zero and one")
    rows = sorted(tuple(fixtures), key=lambda row: (row.kickoff_at, row.fixture_id))
    ids = [row.fixture_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate fixture IDs")
    if not rows:
        raise ValueError("at least one finished fixture is required")

    elo = EloSystem(elo_config)
    rate_model = HistoricalRateModel(prior_matches=prior_matches, half_life_days=half_life_days)
    history: list[ResearchFixture] = []
    predictions: list[ResearchPrediction] = []
    # Refit Dixon-Coles rho only on results already observed by the current
    # prequential cutoff. Never fit on the target fixture or later outcomes.
    rho = 0.0
    last_rho_fit_count = 0
    scored: dict[str, list[tuple[int, tuple[float, float, float]]]] = {
        "elo": [], "poisson": [], "ensemble": []
    }
    index = 0
    while index < len(rows):
        kickoff = rows[index].kickoff_at
        end = index + 1
        while end < len(rows) and rows[end].kickoff_at == kickoff:
            end += 1
        batch = rows[index:end]
        if len(history) >= 30 and len(history) - last_rho_fit_count >= 25:
            rho = fit_dixon_coles_rho(
                history, prior_matches=prior_matches, half_life_days=half_life_days
            )
            last_rho_fit_count = len(history)
        batch_results = []
        for row in batch:
            if history:
                home_rate, away_rate = rate_model.rates(history, row)
            else:
                home_rate, away_rate = 1.35, 1.10
            poisson = build_scoreline_distribution(home_rate, away_rate, rho=rho, max_goals=10)
            elo_probs = _elo_probabilities(elo, row.home_team_id, row.away_team_id, history)
            p_probs = (poisson.home_win, poisson.draw, poisson.away_win)
            weight = ensemble_elo_weight
            ensemble = tuple(weight * elo_probs[i] + (1.0 - weight) * p_probs[i] for i in range(3))
            total = sum(ensemble)
            ensemble = tuple(value / total for value in ensemble)
            actual = _actual_index(row)
            scored["elo"].append((actual, elo_probs))
            scored["poisson"].append((actual, p_probs))
            scored["ensemble"].append((actual, ensemble))
            predictions.append(ResearchPrediction(
                row.fixture_id, row.kickoff_at, row.home_goals, row.away_goals,
                elo_probs[0], elo_probs[1], elo_probs[2],
                p_probs[0], p_probs[1], p_probs[2],
                home_rate, away_rate, rho,
            ))
            batch_results.append(row)
        # No match at this kickoff can learn from another simultaneous result.
        elo.update_batch(tuple(HistoricalResult(
            r.fixture_id, r.kickoff_at, r.home_team_id, r.away_team_id, r.home_goals, r.away_goals
        ) for r in batch_results))
        history.extend(batch)
        index = end

    def summarize(which: str) -> dict[str, float]:
        values = scored[which]
        return {
            "matches": float(len(values)),
            "brier": sum(_brier(a, p) for a, p in values) / len(values),
            "log_loss": sum(_log_loss(a, p) for a, p in values) / len(values),
        }
    fitted_rho = fit_dixon_coles_rho(rows, prior_matches=prior_matches, half_life_days=half_life_days)

    return {
        "dataset_type": "RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED",
        "fixture_count": len(rows),
        "team_count": len({r.home_team_id for r in rows} | {r.away_team_id for r in rows}),
        "date_start": rows[0].kickoff_at.isoformat(),
        "date_end": rows[-1].kickoff_at.isoformat(),
        "elo": summarize("elo"),
        "poisson": summarize("poisson"),
        "ensemble": summarize("ensemble"),
        "ensemble_elo_weight": ensemble_elo_weight,
        "dixon_coles_rho_full_corpus_diagnostic_only": fitted_rho,
        "scoreline_model": "POISSON_WITH_TRAINING_ONLY_DIXON_COLES_RHO",
        "rho_used_for_prequential_predictions": "updated_from_prior_results_only",
        "predictions": [
            {
                "fixture_id": p.fixture_id, "kickoff_at": p.kickoff_at.isoformat(),
                "actual_home_goals": p.actual_home_goals, "actual_away_goals": p.actual_away_goals,
                "elo_1x2": [p.elo_home, p.elo_draw, p.elo_away],
                "poisson_1x2": [p.poisson_home, p.poisson_draw, p.poisson_away],
                "goal_rates": [p.home_lambda, p.away_lambda], "rho": p.rho,
            } for p in predictions
        ],
    }
