"""Manual, pure dry-run validation for one already-retrieved 5Dollar odds response.

This module performs no provider I/O, retries, pagination, persistence or scheduling.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any

from pydantic import Field, field_validator

from app.providers.approvals import FIVEDOLLAR_COMMUNITY_ODDS_APPROVAL
from app.providers.contracts import StrictModel
from app.providers.odds_capture import OddsPayloadError, normalize_5dollar_odds
from app.providers.odds_capture_manifest import ProspectiveOddsCaptureManifest
from app.providers.rights import DataUsePurpose, evaluate_record_scope, evaluate_source_use


class CaptureExpectation(StrictModel):
    """Independently supplied request context; never inferred from the manifest."""

    provider: str = Field(min_length=1, max_length=80)
    provider_event_id: str = Field(min_length=1, max_length=160)
    provider_fixture_id: str = Field(min_length=1, max_length=160)
    canonical_fixture_id: str = Field(min_length=1, max_length=160)
    competition_id: str = Field(min_length=1, max_length=100)
    bookmaker_slug: str = Field(min_length=1, max_length=120)
    market_key: str = Field(min_length=1, max_length=80)
    kickoff_at: datetime
    value_bet_decision_cutoff_at: datetime

    @field_validator("kickoff_at", "value_bet_decision_cutoff_at")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expectation timestamps must be timezone-aware")
        return value


@dataclass(frozen=True, slots=True)
class CaptureDryRunResult:
    accepted: bool
    reason_codes: tuple[str, ...]
    observation_count: int
    response_sha256: str
    response_bytes: int


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON_DUPLICATE_OBJECT_KEY")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise ValueError("JSON_NON_FINITE_NUMBER")


def _decode_strict(raw_response: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(
            raw_response.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        reason = str(exc) if str(exc).startswith("JSON_") else "JSON_MALFORMED_OR_NOT_UTF8"
        raise ValueError(reason) from None
    if not isinstance(parsed, dict):
        raise ValueError("JSON_ROOT_MUST_BE_OBJECT")
    return parsed


def _rights_approval_id(competition_id: str, at_utc: datetime) -> str:
    approval = FIVEDOLLAR_COMMUNITY_ODDS_APPROVAL
    record = evaluate_record_scope(
        approval,
        provider="5DollarFootballAPI",
        source_id="5dollarfootballapi",
        scope_type="competition_id",
        scope_value=competition_id,
        data_type="bookmaker_odds",
        at_utc=at_utc,
    )
    use = evaluate_source_use(
        approval,
        DataUsePurpose.VALUE_BETTING,
        scope_value=competition_id,
        at_utc=at_utc,
        commercial=False,
        public_facing=False,
    )
    if not record.allowed or not use.allowed:
        raise ValueError("RIGHTS_NOT_APPROVED")
    return approval.approval_id


def validate_manual_capture(
    raw_response: bytes,
    manifest: ProspectiveOddsCaptureManifest,
    expected: CaptureExpectation,
) -> CaptureDryRunResult:
    """Validate one response byte-for-byte and return a fail-closed dry-run result."""
    digest = sha256(raw_response).hexdigest()
    reasons: list[str] = []
    if len(raw_response) != manifest.response_bytes:
        reasons.append("RESPONSE_BYTE_COUNT_MISMATCH")
    if digest.casefold() != manifest.response_sha256.casefold():
        reasons.append("RESPONSE_SHA256_MISMATCH")

    manifest_expected = {
        "provider": expected.provider,
        "provider_event_id": expected.provider_event_id,
        "provider_fixture_id": expected.provider_fixture_id,
        "canonical_fixture_id": expected.canonical_fixture_id,
        "competition_id": expected.competition_id,
        "bookmaker_slug": expected.bookmaker_slug,
        "market_key": expected.market_key,
        "fixture_kickoff_at": expected.kickoff_at,
        "value_bet_decision_cutoff_at": expected.value_bet_decision_cutoff_at,
    }
    for field, value in manifest_expected.items():
        if getattr(manifest, field) != value:
            reasons.append("MANIFEST_CONTEXT_MISMATCH:" + field)

    if expected.provider != "5DollarFootballAPI":
        reasons.append("PROVIDER_NOT_SUPPORTED")
    if expected.bookmaker_slug.casefold() != "bet365":
        reasons.append("BOOKMAKER_NOT_APPROVED")
    if expected.market_key not in {"1x2", "goal_line", "goal_line_fixed", "btts"}:
        reasons.append("MARKET_NOT_SUPPORTED")

    try:
        resolved_approval_id = _rights_approval_id(
            expected.competition_id, manifest.retrieved_at
        )
        if manifest.rights_approval_id != resolved_approval_id:
            reasons.append("RIGHTS_APPROVAL_ID_MISMATCH")
    except ValueError:
        reasons.append("RIGHTS_NOT_APPROVED")
        resolved_approval_id = ""

    observations = ()
    if not reasons:
        try:
            payload = _decode_strict(raw_response)
            data = payload.get("data")
            if not isinstance(data, dict):
                raise ValueError("PROVIDER_DATA_MUST_BE_OBJECT")
            returned_fixture_id = data.get("fixture_id")
            if str(returned_fixture_id or "") != expected.provider_fixture_id:
                raise ValueError("PROVIDER_FIXTURE_ID_MISMATCH")
            observations = normalize_5dollar_odds(
                payload,
                provider_fixture_id=expected.provider_fixture_id,
                kickoff_at=expected.kickoff_at,
                request_started_at=manifest.request_started_at,
                retrieved_at=manifest.retrieved_at,
                provider_response_date=manifest.provider_response_date,
                value_bet_decision_cutoff_at=expected.value_bet_decision_cutoff_at,
                source_observation_id=manifest.capture_identity,
                competition_id=expected.competition_id,
            )
            if not observations:
                raise ValueError("NO_ADMISSIBLE_OBSERVATIONS")
            if any(item.rights_approval_id != resolved_approval_id for item in observations):
                raise ValueError("OBSERVATION_RIGHTS_ID_MISMATCH")
            if any(item.bookmaker.casefold().replace(" ", "") != "bet365" for item in observations):
                raise ValueError("OBSERVATION_BOOKMAKER_MISMATCH")
            market_map = {
                "1x2": "1X2",
                "goal_line": "TOTALS",
                "goal_line_fixed": "TOTALS",
                "btts": "BTTS",
            }
            if any(item.market != market_map[expected.market_key] for item in observations):
                raise ValueError("OBSERVATION_MARKET_MISMATCH")
            ticks = [item.source_tick_at for item in observations]
            if min(ticks) != manifest.source_tick_min_at or max(ticks) != manifest.source_tick_max_at:
                raise ValueError("SOURCE_TICK_RANGE_MISMATCH")
            if len({
                (item.bookmaker, item.market, item.selection, item.line, item.source_tick_at)
                for item in observations
            }) != len(observations):
                raise ValueError("DUPLICATE_OBSERVATION")
        except (ValueError, OddsPayloadError) as exc:
            reasons.append(str(exc) if str(exc).isupper() else "ODDS_PAYLOAD_REJECTED")

    if manifest.admission != "ELIGIBLE":
        reasons.append("MANIFEST_NOT_ELIGIBLE")
    return CaptureDryRunResult(
        accepted=not reasons,
        reason_codes=tuple(dict.fromkeys(reasons)),
        observation_count=len(observations) if not reasons else 0,
        response_sha256=digest,
        response_bytes=len(raw_response),
    )
