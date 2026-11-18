"""Fail-closed adapters for documented 5DollarFootballAPI odds payloads."""
from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from hashlib import sha256
from typing import Any

from app.providers.odds_contracts import OddsObservation


class OddsPayloadError(ValueError):
    """Provider odds response cannot be admitted as a pre-match observation."""


def _response_hash(payload: Mapping[str, Any]) -> str:
    try:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise OddsPayloadError("odds payload must be finite JSON") from None
    return sha256(canonical.encode("utf-8")).hexdigest()


def _response_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if payload.get("success") != 1:
        raise OddsPayloadError("provider response success flag is not 1")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise OddsPayloadError("provider response data must be an object")
    return data


def _aware_tick(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise OddsPayloadError("odds tick timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise OddsPayloadError("invalid odds tick timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OddsPayloadError("odds tick timestamp must include timezone")
    return parsed


def _observation(
    *, provider_fixture_id: str, bookmaker: str, market: str, selection: str,
    line: float | None, price: Any, tick_at: datetime, retrieved_at: datetime,
    kickoff_at: datetime, prediction_cutoff_at: datetime, source_observation_id: str,
    digest: str, rights_approval_id: str, rights_allow_value_betting: bool,
    request_started_at: datetime, provider_response_date: datetime | None,
) -> OddsObservation:
    try:
        decimal_odds = float(price)
    except (TypeError, ValueError):
        raise OddsPayloadError("odds price must be numeric") from None
    try:
        return OddsObservation(
            provider="5DollarFootballAPI",
            provider_fixture_id=provider_fixture_id,
            bookmaker=bookmaker,
            market=market,
            selection=selection,
            line=line,
            decimal_odds=decimal_odds,
            source_tick_at=tick_at,
            request_started_at=request_started_at,
            retrieved_at=retrieved_at,
            provider_response_date=provider_response_date,
            kickoff_at=kickoff_at,
            prediction_cutoff_at=prediction_cutoff_at,
            in_play=False,
            source_observation_id=source_observation_id,
            source_response_sha256=digest,
            rights_approval_id=rights_approval_id,
            use_purpose="VALUE_BETTING_ONLY",
            rights_allow_value_betting=rights_allow_value_betting,
        )
    except ValueError as exc:
        raise OddsPayloadError(str(exc)) from None


def normalize_5dollar_fixture_odds(
    response: Mapping[str, Any], *, provider_fixture_id: str, kickoff_at: datetime,
    request_started_at: datetime, retrieved_at: datetime,
    provider_response_date: datetime | None = None,
    prediction_cutoff_at: datetime,
    source_observation_id: str, rights_approval_id: str,
    rights_allow_value_betting: bool,
) -> tuple[OddsObservation, ...]:
    """Normalize only timestamped 1X2 opening prices from /fixtures/{id}/odds.

    The documented endpoint gives opened_at for Bet365 1X2 opening prices.
    Other market snapshots and closing/in-play prices do not carry an individual
    source tick timestamp in this response, so they are deliberately not admitted.
    """
    data = _response_data(response)
    returned_fixture_id = data.get("fixture_id")
    if returned_fixture_id is not None and str(returned_fixture_id) != provider_fixture_id:
        raise OddsPayloadError("odds response fixture_id does not match requested fixture")
    bookmakers = data.get("bookmakers")
    if not isinstance(bookmakers, list):
        raise OddsPayloadError("fixture odds data has no bookmakers array")
    digest = _response_hash(response)
    output: list[OddsObservation] = []
    for bookmaker_row in bookmakers:
        if not isinstance(bookmaker_row, Mapping):
            raise OddsPayloadError("malformed bookmaker row")
        bookmaker_slug = str(bookmaker_row.get("slug") or "").strip().casefold()
        if bookmaker_slug != "bet365":
            continue
        bookmaker = str(bookmaker_row.get("name") or bookmaker_slug).strip()
        odds = bookmaker_row.get("odds")
        if not isinstance(odds, Mapping):
            raise OddsPayloadError("bookmaker row has no odds object")
        market = odds.get("1x2")
        if market is None:
            continue
        if not isinstance(market, Mapping):
            raise OddsPayloadError("1x2 market must be an object")
        opening = market.get("opening")
        if opening is None:
            continue
        if not isinstance(opening, Mapping):
            raise OddsPayloadError("1x2 opening must be an object")
        # The public contract documents opened_at for Bet365 1X2 only.
        # Other bookmakers without an explicit timestamp are not PIT-admissible.
        if not opening.get("opened_at"):
            continue
        tick_at = _aware_tick(opening.get("opened_at"))
        for selection in ("home", "draw", "away"):
            if opening.get(selection) is None:
                raise OddsPayloadError("1x2 opening is missing a price")
            output.append(_observation(
                provider_fixture_id=provider_fixture_id, bookmaker=bookmaker,
                market="1X2", selection=selection, line=None, price=opening[selection],
                tick_at=tick_at, request_started_at=request_started_at,
                retrieved_at=retrieved_at, provider_response_date=provider_response_date,
                kickoff_at=kickoff_at,
                prediction_cutoff_at=prediction_cutoff_at,
                source_observation_id=source_observation_id, digest=digest,
                rights_approval_id=rights_approval_id,
                rights_allow_value_betting=rights_allow_value_betting,
            ))
    return tuple(output)


def normalize_5dollar_odds_history(
    response: Mapping[str, Any], *, provider_fixture_id: str, kickoff_at: datetime,
    request_started_at: datetime, retrieved_at: datetime,
    provider_response_date: datetime | None = None,
    prediction_cutoff_at: datetime,
    source_observation_id: str, rights_approval_id: str,
    rights_allow_value_betting: bool,
) -> tuple[OddsObservation, ...]:
    """Normalize pre-match ticks from /fixtures/{id}/odds/history.

    In-play and suspended ticks are intentionally excluded. Retrieval time is
    always supplied by the caller and remains distinct from provider recorded_at.
    """
    data = _response_data(response)
    returned_fixture_id = data.get("fixture_id")
    if returned_fixture_id is not None and str(returned_fixture_id) != provider_fixture_id:
        raise OddsPayloadError("odds history fixture_id does not match requested fixture")
    bookmaker_data = data.get("bookmaker")
    if not isinstance(bookmaker_data, Mapping):
        raise OddsPayloadError("odds history has no bookmaker object")
    bookmaker = str(bookmaker_data.get("slug") or bookmaker_data.get("name") or "").strip()
    market_name = str(data.get("market") or "").lower()
    market_map = {"1x2": ("1X2", ("home", "draw", "away")),
                  "goalline": ("TOTALS", ("over", "under")),
                  "goalline_fixed": ("TOTALS", ("over", "under")),
                  "btts": ("BTTS", ("yes", "no"))}
    if market_name not in market_map:
        return ()
    normalized_market, selections = market_map[market_name]
    if market_name == "goalline_fixed":
        lines = data.get("lines")
        if not isinstance(lines, list):
            raise OddsPayloadError("fixed goal-line history has no lines array")
        tick_rows: list[tuple[Mapping[str, Any], float | None]] = []
        for line_group in lines:
            if not isinstance(line_group, Mapping) or not isinstance(line_group.get("ticks"), list):
                raise OddsPayloadError("malformed fixed goal-line group")
            try:
                fixed_line = float(line_group.get("line"))
            except (TypeError, ValueError):
                raise OddsPayloadError("fixed goal-line group has invalid line") from None
            tick_rows.extend((tick, fixed_line) for tick in line_group["ticks"] if isinstance(tick, Mapping))
            if any(not isinstance(tick, Mapping) for tick in line_group["ticks"]):
                raise OddsPayloadError("malformed fixed goal-line tick")
    else:
        ticks = data.get("ticks")
        if not isinstance(ticks, list):
            raise OddsPayloadError("odds history has no ticks array")
        tick_rows = [(tick, None) for tick in ticks if isinstance(tick, Mapping)]
        if any(not isinstance(tick, Mapping) for tick in ticks):
            raise OddsPayloadError("malformed odds history tick")
    digest = _response_hash(response)
    output: list[OddsObservation] = []
    for tick, fixed_line in tick_rows:
        if not isinstance(tick, Mapping):
            raise OddsPayloadError("malformed odds history tick")
        if tick.get("suspended") is True:
            continue
        minute = tick.get("minute")
        score = tick.get("score")
        if score is not None and not isinstance(score, Mapping):
            raise OddsPayloadError("odds history score must be an object or null")
        score_values = tuple(score.get(side) for side in ("home", "away")) if isinstance(score, Mapping) else (None, None)
        # Provider examples define pre-match ticks with minute=null and null score.
        # Minute 0 is already in-play and must not be admitted as pre-match.
        if minute is not None or any(value is not None for value in score_values) or tick.get("half_time") is True:
            continue
        tick_at = _aware_tick(tick.get("recorded_at"))
        raw_line = fixed_line if fixed_line is not None else tick.get("line")
        try:
            line = float(raw_line) if raw_line is not None else None
        except (TypeError, ValueError):
            raise OddsPayloadError("invalid odds line") from None
        prices = tuple(tick.get(selection) for selection in selections)
        if all(price is None for price in prices):
            # Provider docs define all-null prices as a withdrawn market/line.
            continue
        if any(price is None for price in prices):
            raise OddsPayloadError("pre-match odds tick has a partially missing price set")
        for selection, price in zip(selections, prices, strict=True):
            output.append(_observation(
                provider_fixture_id=provider_fixture_id, bookmaker=bookmaker,
                market=normalized_market, selection=selection, line=line,
                price=price, tick_at=tick_at, request_started_at=request_started_at,
                retrieved_at=retrieved_at, provider_response_date=provider_response_date,
                kickoff_at=kickoff_at, prediction_cutoff_at=prediction_cutoff_at,
                source_observation_id=source_observation_id, digest=digest,
                rights_approval_id=rights_approval_id,
                rights_allow_value_betting=rights_allow_value_betting,
            ))
    return tuple(output)


def normalize_5dollar_odds(
    response: Mapping[str, Any], *, provider_fixture_id: str, kickoff_at: datetime,
    request_started_at: datetime, retrieved_at: datetime,
    provider_response_date: datetime | None = None,
    prediction_cutoff_at: datetime,
    source_observation_id: str, rights_approval_id: str,
    rights_allow_value_betting: bool,
) -> tuple[OddsObservation, ...]:
    """Dispatch documented fixture-odds and odds-history response envelopes."""
    data = _response_data(response)
    if "bookmakers" in data:
        return normalize_5dollar_fixture_odds(
            response, provider_fixture_id=provider_fixture_id, kickoff_at=kickoff_at,
            request_started_at=request_started_at, retrieved_at=retrieved_at,
            provider_response_date=provider_response_date,
            prediction_cutoff_at=prediction_cutoff_at,
            source_observation_id=source_observation_id,
            rights_approval_id=rights_approval_id,
            rights_allow_value_betting=rights_allow_value_betting,
        )
    if "bookmaker" in data and ("ticks" in data or "lines" in data):
        return normalize_5dollar_odds_history(
            response, provider_fixture_id=provider_fixture_id, kickoff_at=kickoff_at,
            retrieved_at=retrieved_at, prediction_cutoff_at=prediction_cutoff_at,
            source_observation_id=source_observation_id,
            rights_approval_id=rights_approval_id,
            rights_allow_model_training=rights_allow_model_training,
        )
    raise OddsPayloadError("unrecognized documented 5Dollar odds response envelope")
