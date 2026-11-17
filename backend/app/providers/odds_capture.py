"""Fail-closed normalization boundary for 5DollarFootballAPI odds payloads."""
from __future__ import annotations
from datetime import datetime
from hashlib import sha256
import json
from typing import Any, Mapping
from app.providers.odds_contracts import OddsObservation

class OddsPayloadError(ValueError):
    """Provider odds response cannot be admitted as a pre-match observation."""

def normalize_5dollar_odds(
    row: Mapping[str, Any], *, provider_fixture_id: str, kickoff_at: datetime,
    retrieved_at: datetime, prediction_cutoff_at: datetime,
    source_observation_id: str, rights_approval_id: str,
    rights_allow_model_training: bool,
) -> tuple[OddsObservation, ...]:
    """Normalize only explicit provider ticks; never infer source time from retrieval."""
    try:
        canonical = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise OddsPayloadError("odds payload must be finite JSON") from None
    digest = sha256(canonical.encode("utf-8")).hexdigest()
    odds = row.get("odds")
    if not isinstance(odds, list):
        raise OddsPayloadError("fixture response has no odds array")
    output: list[OddsObservation] = []
    for bookmaker_row in odds:
        if not isinstance(bookmaker_row, dict):
            raise OddsPayloadError("malformed bookmaker odds row")
        bookmaker = bookmaker_row.get("bookmaker") or bookmaker_row.get("name")
        markets = bookmaker_row.get("markets")
        if not isinstance(markets, list):
            raise OddsPayloadError("bookmaker odds row has no markets array")
        for market_row in markets:
            if not isinstance(market_row, dict):
                raise OddsPayloadError("malformed market row")
            market = str(market_row.get("market") or market_row.get("key") or "").upper()
            if market not in {"1X2", "TOTALS", "BTTS"}:
                continue
            outcomes = market_row.get("outcomes")
            if not isinstance(outcomes, list):
                raise OddsPayloadError("market has no outcomes array")
            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    raise OddsPayloadError("malformed outcome")
                raw_tick = outcome.get("recorded_at") or bookmaker_row.get("recorded_at") or outcome.get("opened_at")
                if not raw_tick:
                    raise OddsPayloadError("odds outcome is missing recorded_at/opened_at")
                try:
                    tick = datetime.fromisoformat(str(raw_tick).replace("Z", "+00:00"))
                    price = float(outcome.get("odds", outcome.get("price")))
                    line = float(outcome["line"]) if outcome.get("line") is not None else None
                except (TypeError, ValueError):
                    raise OddsPayloadError("invalid odds timestamp, price, or line") from None
                if tick.tzinfo is None or tick.utcoffset() is None:
                    raise OddsPayloadError("odds tick timestamp must include timezone")
                output.append(OddsObservation(
                    provider="5DollarFootballAPI", provider_fixture_id=provider_fixture_id,
                    bookmaker=str(bookmaker or ""), market=market,
                    selection=str(outcome.get("name") or outcome.get("selection") or ""),
                    line=line, decimal_odds=price, source_tick_at=tick,
                    retrieved_at=retrieved_at, kickoff_at=kickoff_at,
                    prediction_cutoff_at=prediction_cutoff_at,
                    in_play=in_play_value,
                    source_observation_id=source_observation_id,
                    source_response_sha256=digest, rights_approval_id=rights_approval_id,
                    rights_allow_model_training=rights_allow_model_training,
                ))
    return tuple(output)
