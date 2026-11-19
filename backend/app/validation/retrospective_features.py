"""Event-time-ordered retrospective features for research-only model development.

These features are reconstructed from completed historical fixtures retrieved
after their events. They are useful for research, but are never point-in-time
system observations and must never enter prospective certification.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import fmean
from typing import Any


@dataclass(frozen=True, slots=True)
class HistoricalFixture:
    fixture_id: str
    competition_id: str
    kickoff_at: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int
    home_corners: int | None = None
    away_corners: int | None = None
    home_yellow_cards: int | None = None
    away_yellow_cards: int | None = None
    home_red_cards: int | None = None
    away_red_cards: int | None = None


def _mean(values: list[float]) -> float | None:
    return fmean(values) if values else None


def build_retrospective_lagged_features(
    fixtures: list[HistoricalFixture],
) -> tuple[dict[str, Any], ...]:
    """Build target features using only strictly earlier fixtures in its competition.

    Fixtures with the same kickoff timestamp are treated as simultaneous and
    cannot contribute to one another. Missing corner/card values remain None;
    they are never imputed from the target outcome or global arbitrary priors.
    """
    if len({row.fixture_id for row in fixtures}) != len(fixtures):
        raise ValueError("duplicate fixture IDs are not allowed")
    for row in fixtures:
        if row.kickoff_at.tzinfo is None or row.kickoff_at.utcoffset() is None:
            raise ValueError("all kickoff timestamps must be timezone-aware")
        if not row.fixture_id or not row.competition_id or not row.home_team_id or not row.away_team_id:
            raise ValueError("fixture and identity fields cannot be blank")
        if min(row.home_goals, row.away_goals) < 0:
            raise ValueError("goal counts cannot be negative")

    ordered = sorted(fixtures, key=lambda row: (row.kickoff_at, row.fixture_id))
    history: dict[tuple[str, str], list[tuple[str, float | None, float | None, float | None, float | None, float | None, float | None]]] = {}
    output: list[dict[str, Any]] = []

    for target in ordered:
        home_history = history.get((target.competition_id, target.home_team_id), [])
        away_history = history.get((target.competition_id, target.away_team_id), [])

        def average(index: int, rows: list[tuple]) -> float | None:
            return _mean([float(item[index]) for item in rows if item[index] is not None])

        features = {
            "home_prior_match_count": len(home_history),
            "away_prior_match_count": len(away_history),
            "home_goals_for_mean": average(1, home_history),
            "home_goals_against_mean": average(2, home_history),
            "away_goals_for_mean": average(1, away_history),
            "away_goals_against_mean": average(2, away_history),
            "home_corners_for_mean": average(3, home_history),
            "home_corners_against_mean": average(4, home_history),
            "away_corners_for_mean": average(3, away_history),
            "away_corners_against_mean": average(4, away_history),
            "home_cards_for_mean": average(5, home_history),
            "home_cards_against_mean": average(6, home_history),
            "away_cards_for_mean": average(5, away_history),
            "away_cards_against_mean": average(6, away_history),
        }
        output.append({
            "fixture_id": target.fixture_id,
            "competition_id": target.competition_id,
            "kickoff_at": target.kickoff_at.isoformat(),
            "features": features,
            "validation_eligible": False,
            "feature_provenance": {
                "mode": "RETROSPECTIVE_EVENT_TIME_RECONSTRUCTION",
                "point_in_time_certifiable": False,
                "source_available_before_target_kickoff": False,
                "history_fixture_ids": sorted({
                    item[0] for item in home_history + away_history
                }),
            },
        })

        # Add the target only after its own feature row has been emitted.
        home_cards = (
            float(target.home_yellow_cards + target.home_red_cards)
            if target.home_yellow_cards is not None and target.home_red_cards is not None
            else None
        )
        away_cards = (
            float(target.away_yellow_cards + target.away_red_cards)
            if target.away_yellow_cards is not None and target.away_red_cards is not None
            else None
        )
        history.setdefault((target.competition_id, target.home_team_id), []).append((
            target.fixture_id, float(target.home_goals), float(target.away_goals),
            float(target.home_corners) if target.home_corners is not None else None,
            float(target.away_corners) if target.away_corners is not None else None,
            home_cards, away_cards,
        ))
        history.setdefault((target.competition_id, target.away_team_id), []).append((
            target.fixture_id, float(target.away_goals), float(target.home_goals),
            float(target.away_corners) if target.away_corners is not None else None,
            float(target.home_corners) if target.home_corners is not None else None,
            away_cards, home_cards,
        ))

    return tuple(output)
