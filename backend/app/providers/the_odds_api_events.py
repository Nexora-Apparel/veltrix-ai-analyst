"""Fail-closed parser for The Odds API v4 event discovery responses.

Event discovery contains fixture metadata only; this module never parses or
requests bookmaker prices.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


class OddsApiEventPayloadError(ValueError):
    """The Odds API event response is malformed or inconsistent."""


def normalize_event_catalogue(
    payload: Any, *, requested_sport_key: str, as_of: datetime
) -> tuple[dict[str, str], ...]:
    """Return valid future events without mutating or persisting source payloads."""
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise OddsApiEventPayloadError("as_of must be timezone-aware")
    if not isinstance(payload, list):
        raise OddsApiEventPayloadError("event response must be a JSON array")

    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for row in payload:
        if not isinstance(row, dict):
            raise OddsApiEventPayloadError("event row must be an object")
        event_id = row.get("id")
        sport_key = row.get("sport_key")
        home = row.get("home_team")
        away = row.get("away_team")
        commence_time = row.get("commence_time")
        if not all(isinstance(value, str) and value.strip() for value in (
            event_id, sport_key, home, away, commence_time
        )):
            raise OddsApiEventPayloadError("event row is missing a required string field")
        if sport_key != requested_sport_key:
            raise OddsApiEventPayloadError("event sport_key does not match requested sport")
        if event_id in seen_ids:
            raise OddsApiEventPayloadError("duplicate event id in response")
        try:
            kickoff = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        except ValueError:
            raise OddsApiEventPayloadError("invalid event commence_time") from None
        if kickoff.tzinfo is None or kickoff.utcoffset() is None:
            raise OddsApiEventPayloadError("event commence_time must be timezone-aware")
        if kickoff <= as_of:
            continue
        if home.strip().casefold() == away.strip().casefold():
            raise OddsApiEventPayloadError("home and away teams must differ")
        seen_ids.add(event_id)
        normalized.append({
            "event_id": event_id,
            "sport_key": sport_key,
            "home_team": home.strip(),
            "away_team": away.strip(),
            "commence_time": kickoff.isoformat(),
        })
    return tuple(sorted(normalized, key=lambda event: (
        event["commence_time"], event["event_id"]
    )))
