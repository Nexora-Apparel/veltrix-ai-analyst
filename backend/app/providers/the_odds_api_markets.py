"""Fail-closed normalization for one event-specific The Odds API h2h response."""
from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from app.providers.event_matching import match_event_to_fixture


class OddsApiMarketPayloadError(ValueError):
    """The Odds API event market response is malformed or misidentified."""


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OddsApiMarketPayloadError(f"{field}_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise OddsApiMarketPayloadError(f"{field}_INVALID") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OddsApiMarketPayloadError(f"{field}_MUST_BE_TIMEZONE_AWARE")
    return parsed.astimezone(UTC)


def _team_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    folded = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", folded.casefold()).split())


def normalize_event_h2h_odds_response(
    payload: Any,
    *,
    expected_event: Mapping[str, object],
    canonical_fixture: Mapping[str, object],
    retrieved_at: datetime,
) -> dict[str, Any]:
    """Validate event identity and retain only timestamped, finite h2h prices."""
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise OddsApiMarketPayloadError("RETRIEVED_AT_MUST_BE_TIMEZONE_AWARE")
    retrieved = retrieved_at.astimezone(UTC)
    if not isinstance(payload, dict):
        raise OddsApiMarketPayloadError("RESPONSE_MUST_BE_OBJECT")

    event_id = payload.get("id")
    sport_key = payload.get("sport_key")
    home = payload.get("home_team")
    away = payload.get("away_team")
    commence = payload.get("commence_time")
    if not all(isinstance(value, str) and value.strip() for value in (
        event_id, sport_key, home, away, commence
    )):
        raise OddsApiMarketPayloadError("EVENT_IDENTITY_FIELDS_REQUIRED")

    if event_id != expected_event.get("event_id"):
        raise OddsApiMarketPayloadError("EVENT_ID_MISMATCH")
    if sport_key != expected_event.get("sport_key"):
        raise OddsApiMarketPayloadError("SPORT_KEY_MISMATCH")
    if _team_key(home) != _team_key(str(expected_event.get("home_team", ""))):
        raise OddsApiMarketPayloadError("HOME_TEAM_MISMATCH")
    if _team_key(away) != _team_key(str(expected_event.get("away_team", ""))):
        raise OddsApiMarketPayloadError("AWAY_TEAM_MISMATCH")

    event = {
        "event_id": event_id,
        "home_team": home,
        "away_team": away,
        "commence_time": commence,
    }
    match = match_event_to_fixture(event, [canonical_fixture])
    if match.status != "MATCHED":
        raise OddsApiMarketPayloadError(f"CANONICAL_FIXTURE_{match.status}")
    kickoff = _aware(commence, "COMMENCE_TIME")
    if kickoff <= retrieved:
        raise OddsApiMarketPayloadError("EVENT_ALREADY_STARTED_OR_KICKOFF_PASSED")

    bookmakers = payload.get("bookmakers")
    if not isinstance(bookmakers, list):
        raise OddsApiMarketPayloadError("BOOKMAKERS_MUST_BE_ARRAY")

    quotes: list[dict[str, Any]] = []
    rejected_missing_timestamp = 0
    rejected_invalid_quote = 0
    rejected_incomplete_bookmaker_count = 0
    seen: set[tuple[str, str]] = set()
    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            rejected_invalid_quote += 1
            continue
        bookmaker_key = bookmaker.get("key")
        bookmaker_title = bookmaker.get("title")
        if not isinstance(bookmaker_key, str) or not bookmaker_key.strip():
            rejected_invalid_quote += 1
            continue
        markets = bookmaker.get("markets")
        if not isinstance(markets, list):
            rejected_invalid_quote += 1
            continue
        h2h_markets = [
            market for market in markets
            if isinstance(market, dict) and market.get("key") == "h2h"
        ]
        if len(h2h_markets) != 1:
            rejected_invalid_quote += 1
            continue
        market = h2h_markets[0]
        try:
            source_tick = _aware(market.get("last_update"), "MARKET_LAST_UPDATE")
        except OddsApiMarketPayloadError:
            rejected_missing_timestamp += 1
            continue
        if source_tick > retrieved:
            rejected_invalid_quote += 1
            continue
        outcomes = market.get("outcomes")
        if not isinstance(outcomes, list):
            rejected_invalid_quote += 1
            continue
        bookmaker_quotes: list[dict[str, Any]] = []
        bookmaker_selections: set[str] = set()
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                rejected_invalid_quote += 1
                continue
            name = outcome.get("name")
            price = outcome.get("price")
            if not isinstance(name, str) or not name.strip():
                rejected_invalid_quote += 1
                continue
            try:
                decimal_price = float(price)
            except (TypeError, ValueError):
                rejected_invalid_quote += 1
                continue
            if not math.isfinite(decimal_price) or decimal_price <= 1.0:
                rejected_invalid_quote += 1
                continue
            normalized = _team_key(name)
            if normalized == _team_key(home):
                selection = "HOME"
            elif normalized == _team_key(away):
                selection = "AWAY"
            elif normalized == "draw":
                selection = "DRAW"
            else:
                rejected_invalid_quote += 1
                continue
            if selection in bookmaker_selections:
                raise OddsApiMarketPayloadError("DUPLICATE_BOOKMAKER_SELECTION")
            bookmaker_selections.add(selection)
            bookmaker_quotes.append({
                "bookmaker_key": bookmaker_key,
                "bookmaker_title": bookmaker_title if isinstance(bookmaker_title, str) else bookmaker_key,
                "market": "h2h",
                "selection": selection,
                "decimal_price": decimal_price,
                "source_tick_at": source_tick.isoformat(),
            })
        if bookmaker_selections != {"HOME", "DRAW", "AWAY"}:
            rejected_incomplete_bookmaker_count += 1
            continue
        for quote in bookmaker_quotes:
            key = (bookmaker_key, quote["selection"])
            if key in seen:
                raise OddsApiMarketPayloadError("DUPLICATE_BOOKMAKER_SELECTION")
            seen.add(key)
            quotes.append(quote)

    quotes.sort(key=lambda item: (item["bookmaker_key"], item["selection"]))
    return {
        "event_id": event_id,
        "sport_key": sport_key,
        "home_team": home,
        "away_team": away,
        "commence_time": kickoff.isoformat(),
        "retrieved_at": retrieved.isoformat(),
        "quote_count": len(quotes),
        "bookmaker_count": len({quote["bookmaker_key"] for quote in quotes}),
        "timestamped_quotes": quotes,
        "complete_market": bool(quotes),
        "rejected_missing_timestamp_count": rejected_missing_timestamp,
        "rejected_invalid_quote_count": rejected_invalid_quote,
        "rejected_incomplete_bookmaker_count": rejected_incomplete_bookmaker_count,
    }
