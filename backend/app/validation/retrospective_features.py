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
    home_statistics: dict[str, Any] | None = None
    away_statistics: dict[str, Any] | None = None


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
        for statistics in (row.home_statistics, row.away_statistics):
            if statistics is not None and not isinstance(statistics, dict):
                raise ValueError("team statistics must be dictionaries when present")

    ordered = sorted(fixtures, key=lambda row: (row.kickoff_at, row.fixture_id))
    history: dict[
        tuple[str, str],
        list[tuple[str, float | None, float | None, float | None, float | None, float | None, float | None, dict[str, float | None], dict[str, float | None]]],
    ] = {}
    output: list[dict[str, Any]] = []

    def average(index: int, rows: list[tuple]) -> float | None:
        return _mean([float(item[index]) for item in rows if item[index] is not None])

    # Process equal-kickoff fixtures as one atomic time block. No fixture in
    # the block may become history for another fixture with the same kickoff.
    cursor = 0
    while cursor < len(ordered):
        kickoff_at = ordered[cursor].kickoff_at
        block_end = cursor
        while block_end < len(ordered) and ordered[block_end].kickoff_at == kickoff_at:
            block_end += 1
        kickoff_block = ordered[cursor:block_end]

        for target in kickoff_block:
            home_history = history.get((target.competition_id, target.home_team_id), [])
            away_history = history.get((target.competition_id, target.away_team_id), [])
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
            stat_names = ("attacks", "dangerous_attacks", "shots_on_target", "shots_off_target", "possession")
            for stat_name in stat_names:
                for period in ("", "first_half"):
                    suffix = "_first_half" if period else ""
                    key = f"{period}.{stat_name}" if period else stat_name
                    for team_name, own_history, opponent_history in (
                        ("home", home_history, home_history),
                        ("away", away_history, away_history),
                    ):
                        own_values = [item[7].get(key) for item in own_history]
                        opponent_values = [item[8].get(key) for item in own_history] if team_name == "home" else [item[7].get(key) for item in away_history]
                        features[f"{team_name}_{stat_name}{suffix}_for_mean"] = _mean([float(v) for v in own_values if v is not None])
                        features[f"{team_name}_{stat_name}{suffix}_against_mean"] = _mean([float(v) for v in opponent_values if v is not None])
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

        # Commit the whole kickoff block to history only after every feature
        # vector for that timestamp has been generated.
        for target in kickoff_block:
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
            def flatten_statistics(value: dict[str, Any] | None) -> dict[str, float | None]:
                flattened: dict[str, float | None] = {}
                for metric in ("attacks", "dangerous_attacks", "shots_on_target", "shots_off_target", "possession"):
                    for period in ("", "first_half"):
                        source = value.get(period) if period else value
                        source = source if isinstance(source, dict) else {}
                        pair = source.get(metric)
                        raw_home = pair.get("home") if isinstance(pair, dict) else None
                        raw_away = pair.get("away") if isinstance(pair, dict) else None
                        prefix = f"{period}." if period else ""
                        for side, raw in (("home", raw_home), ("away", raw_away)):
                            flattened[f"{prefix}{metric}.{side}"] = float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) else None
                return flattened

            home_stats = flatten_statistics(target.home_statistics)
            away_stats = flatten_statistics(target.away_statistics)
            history.setdefault((target.competition_id, target.home_team_id), []).append((
                target.fixture_id, float(target.home_goals), float(target.away_goals),
                float(target.home_corners) if target.home_corners is not None else None,
                float(target.away_corners) if target.away_corners is not None else None,
                home_cards, away_cards, home_stats, away_stats,
            ))
            history.setdefault((target.competition_id, target.away_team_id), []).append((
                target.fixture_id, float(target.away_goals), float(target.home_goals),
                float(target.away_corners) if target.away_corners is not None else None,
                float(target.home_corners) if target.home_corners is not None else None,
                away_cards, home_cards, away_stats, home_stats,
            ))
        cursor = block_end

    return tuple(output)
