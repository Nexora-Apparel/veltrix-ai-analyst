"""Strict identity matching between external event catalogues and 5Dollar fixtures."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, Mapping


MatchStatus = Literal[
    "MATCHED",
    "NO_TEAM_MATCH",
    "KICKOFF_OUTSIDE_TOLERANCE",
    "AMBIGUOUS",
]


@dataclass(frozen=True, slots=True)
class EventMatchResult:
    status: MatchStatus
    event_id: str
    fixture_id: str | None
    candidate_fixture_ids: tuple[str, ...]
    kickoff_delta_seconds: float | None


def normalize_team_name(value: str) -> str:
    """Normalize Unicode and punctuation only; deliberately apply no alias guessing."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("TEAM_NAME_REQUIRED")
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_folded = "".join(char for char in decomposed if not unicodedata.combining(char))
    tokens = re.sub(r"[^a-z0-9]+", " ", ascii_folded.casefold()).split()
    if not tokens:
        raise ValueError("TEAM_NAME_HAS_NO_MATCHABLE_TOKENS")
    return " ".join(tokens)


def _parse_aware_datetime(value: object, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError(f"{field_name}_INVALID") from None
    else:
        raise ValueError(f"{field_name}_REQUIRED")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name}_MUST_BE_TIMEZONE_AWARE")
    return parsed.astimezone(UTC)


def match_event_to_fixture(
    event: Mapping[str, object],
    fixtures: tuple[Mapping[str, object], ...] | list[Mapping[str, object]],
    *,
    kickoff_tolerance: timedelta = timedelta(minutes=5),
) -> EventMatchResult:
    """Match one Odds API event to exactly one 5Dollar fixture, failing closed."""
    if kickoff_tolerance <= timedelta(0):
        raise ValueError("KICKOFF_TOLERANCE_MUST_BE_POSITIVE")

    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("EVENT_ID_REQUIRED")
    home = normalize_team_name(event.get("home_team"))  # type: ignore[arg-type]
    away = normalize_team_name(event.get("away_team"))  # type: ignore[arg-type]
    kickoff = _parse_aware_datetime(event.get("commence_time"), "EVENT_KICKOFF")

    team_candidates: list[tuple[str, float]] = []
    for fixture in fixtures:
        fixture_id = fixture.get("provider_fixture_id")
        if not isinstance(fixture_id, str) or not fixture_id.strip():
            raise ValueError("FIXTURE_ID_REQUIRED")
        fixture_home = normalize_team_name(fixture.get("home_team"))  # type: ignore[arg-type]
        fixture_away = normalize_team_name(fixture.get("away_team"))  # type: ignore[arg-type]
        if fixture_home != home or fixture_away != away:
            continue
        fixture_kickoff = _parse_aware_datetime(
            fixture.get("kickoff_at"), "FIXTURE_KICKOFF"
        )
        delta = abs((fixture_kickoff - kickoff).total_seconds())
        team_candidates.append((fixture_id, delta))

    if not team_candidates:
        return EventMatchResult("NO_TEAM_MATCH", event_id, None, (), None)

    eligible = [
        (fixture_id, delta)
        for fixture_id, delta in team_candidates
        if delta <= kickoff_tolerance.total_seconds()
    ]
    if len(eligible) == 1:
        fixture_id, delta = eligible[0]
        return EventMatchResult(
            "MATCHED", event_id, fixture_id, (fixture_id,), delta
        )
    if len(eligible) > 1:
        return EventMatchResult(
            "AMBIGUOUS",
            event_id,
            None,
            tuple(sorted(fixture_id for fixture_id, _ in eligible)),
            None,
        )

    _, nearest_delta = min(team_candidates, key=lambda item: item[1])
    return EventMatchResult(
        "KICKOFF_OUTSIDE_TOLERANCE",
        event_id,
        None,
        tuple(sorted(fixture_id for fixture_id, _ in team_candidates)),
        nearest_delta,
    )
