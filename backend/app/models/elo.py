"""Chronological Elo ratings with simultaneous-kickoff isolation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite, log10
from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class EloConfig:
    initial_rating: float = 1500.0
    k_factor: float = 20.0
    home_advantage: float = 55.0
    rating_scale: float = 400.0
    margin_multiplier_cap: float = 2.5

    def __post_init__(self) -> None:
        for name in ("initial_rating", "k_factor", "home_advantage", "rating_scale", "margin_multiplier_cap"):
            value = getattr(self, name)
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.k_factor <= 0 or self.rating_scale <= 0 or self.margin_multiplier_cap < 1:
            raise ValueError("invalid Elo configuration")
        if self.home_advantage < 0:
            raise ValueError("home_advantage cannot be negative")


@dataclass(frozen=True, slots=True)
class HistoricalResult:
    fixture_id: str
    kickoff_at: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int

    def __post_init__(self) -> None:
        if not self.fixture_id or not self.home_team_id or not self.away_team_id:
            raise ValueError("fixture and team identifiers are required")
        if self.home_team_id == self.away_team_id:
            raise ValueError("home and away teams must differ")
        if self.kickoff_at.tzinfo is None or self.kickoff_at.utcoffset() is None:
            raise ValueError("kickoff_at must be timezone-aware")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("goals cannot be negative")


@dataclass(frozen=True, slots=True)
class EloRating:
    team_id: str
    rating: float
    matches_played: int


class EloSystem:
    """Elo state updated only after every result at the same kickoff is scored."""

    def __init__(self, config: EloConfig | None = None) -> None:
        self.config = config or EloConfig()
        self._ratings: dict[str, float] = {}
        self._matches: dict[str, int] = {}

    def rating(self, team_id: str) -> EloRating:
        return EloRating(
            team_id=team_id,
            rating=self._ratings.get(team_id, self.config.initial_rating),
            matches_played=self._matches.get(team_id, 0),
        )

    def expected_home_score(self, home_team_id: str, away_team_id: str) -> float:
        if home_team_id == away_team_id:
            raise ValueError("home and away teams must differ")
        difference = (
            self.rating(home_team_id).rating
            + self.config.home_advantage
            - self.rating(away_team_id).rating
        )
        return 1.0 / (1.0 + 10.0 ** (-difference / self.config.rating_scale))

    def update(self, result: HistoricalResult) -> None:
        """Apply one result; use update_batch for simultaneous fixtures."""
        self.update_batch((result,))

    def update_batch(self, results: Iterable[HistoricalResult]) -> None:
        batch = tuple(results)
        if not batch:
            return
        kickoff_values = {item.kickoff_at for item in batch}
        if len(kickoff_values) != 1:
            raise ValueError("update_batch requires one shared kickoff timestamp")
        fixture_ids = [item.fixture_id for item in batch]
        if len(fixture_ids) != len(set(fixture_ids)):
            raise ValueError("duplicate fixture IDs in Elo batch")
        touched: set[str] = set()
        for item in batch:
            if item.home_team_id in touched or item.away_team_id in touched:
                raise ValueError("a team cannot appear in multiple simultaneous fixtures")
            touched.update((item.home_team_id, item.away_team_id))

        deltas: dict[str, float] = {}
        for item in batch:
            home_before = self.rating(item.home_team_id).rating
            away_before = self.rating(item.away_team_id).rating
            expected = self.expected_home_score(item.home_team_id, item.away_team_id)
            actual = 1.0 if item.home_goals > item.away_goals else 0.5 if item.home_goals == item.away_goals else 0.0
            margin = abs(item.home_goals - item.away_goals)
            if margin == 0:
                margin_multiplier = 1.0
            else:
                denominator = 2.2 + 0.001 * abs(home_before - away_before)
                margin_multiplier = min(
                    self.config.margin_multiplier_cap,
                    log10(margin + 1.0) * 2.2 / denominator,
                )
                delta = self.config.k_factor * margin_multiplier * (actual - expected)
            deltas[item.home_team_id] = delta
            deltas[item.away_team_id] = -delta

        for team_id, delta in deltas.items():
            self._ratings[team_id] = self.rating(team_id).rating + delta
            self._matches[team_id] = self._matches.get(team_id, 0) + 1

    @classmethod
    def fit_chronologically(
        cls,
        results: Iterable[HistoricalResult],
        config: EloConfig | None = None,
    ) -> EloSystem:
        system = cls(config)
        rows = tuple(results)
        fixture_ids = [item.fixture_id for item in rows]
        if len(fixture_ids) != len(set(fixture_ids)):
            raise ValueError("duplicate fixture IDs in Elo history")
        ordered = sorted(rows, key=lambda item: (item.kickoff_at, item.fixture_id))
        index = 0
        while index < len(ordered):
            kickoff = ordered[index].kickoff_at
            end = index + 1
            while end < len(ordered) and ordered[end].kickoff_at == kickoff:
                end += 1
            system.update_batch(ordered[index:end])
            index = end
        return system
