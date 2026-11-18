"""Single event-specific h2h odds probe, gated by exact cross-provider identity match.

Exactly one request, one market (h2h), one region (UK), no retries and no DB writes.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.providers.the_odds_api_markets import (
    OddsApiMarketPayloadError,
    normalize_event_h2h_odds_response,
)

ODDS_MANIFEST = Path("odds-api-events-manifest.json")
FIXTURE_MANIFEST = Path("5dollar-scheduled-fixtures-manifest.json")
MATCH_MANIFEST = Path("odds-api-5dollar-fixture-match-manifest.json")
OUTPUT = Path("the-odds-api-event-h2h-probe-manifest.json")
BASE_URL = "https://api.the-odds-api.com/v4/sports"
TIMEOUT_SECONDS = 20


def now_utc() -> datetime:
    return datetime.now(UTC)


def emit(manifest: dict[str, object]) -> None:
    OUTPUT.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, sort_keys=True, indent=2))


def skipped(reason: str) -> int:
    emit({
        "provider": "The Odds API",
        "endpoint": "/v4/sports/{sport}/events/{event_id}/odds",
        "request_count": 0,
        "retries": 0,
        "regions": ["uk"],
        "markets": ["h2h"],
        "outcome": reason,
    })
    return 0


def main() -> int:
    for path in (ODDS_MANIFEST, FIXTURE_MANIFEST, MATCH_MANIFEST):
        if not path.exists():
            return skipped("SKIPPED_REQUIRED_CATALOGUE_MANIFEST_MISSING")

    odds_manifest = json.loads(ODDS_MANIFEST.read_text(encoding="utf-8"))
    fixture_manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    match_manifest = json.loads(MATCH_MANIFEST.read_text(encoding="utf-8"))
    if match_manifest.get("market_probe_candidate") is not True:
        return skipped("SKIPPED_NO_UNIQUE_EXACT_FIXTURE_MATCH")
    if match_manifest.get("market_probe_authorized") is not True:
        return skipped("SKIPPED_MARKET_PROBE_NOT_AUTHORIZED")
    if match_manifest.get("catalogues_complete") is not True:
        return skipped("SKIPPED_INCOMPLETE_CATALOGUES")
    matches = match_manifest.get("matches")
    events = odds_manifest.get("events")
    fixtures = fixture_manifest.get("fixtures")
    if not isinstance(matches, list) or not isinstance(events, list) or not isinstance(fixtures, list):
        return skipped("SKIPPED_INVALID_CATALOGUE_MANIFEST")
    exact = [row for row in matches if isinstance(row, dict) and row.get("status") == "MATCHED"]
    if len(exact) != 1:
        return skipped("SKIPPED_MATCH_NOT_UNIQUE")

    event_id = exact[0].get("event_id")
    fixture_id = exact[0].get("fixture_id")
    event_rows = [row for row in events if isinstance(row, dict) and row.get("event_id") == event_id]
    fixture_rows = [
        row for row in fixtures
        if isinstance(row, dict) and row.get("provider_fixture_id") == fixture_id
    ]
    if len(event_rows) != 1 or len(fixture_rows) != 1:
        return skipped("SKIPPED_MATCH_REFERENCES_NOT_UNIQUE")
    event = event_rows[0]
    fixture = fixture_rows[0]
    sport_key = event.get("sport_key")
    if not isinstance(sport_key, str) or not sport_key.strip():
        return skipped("SKIPPED_SPORT_KEY_MISSING")
    key = os.environ.get("THE_ODDS_API_KEY", "").strip()
    if not key:
        return skipped("SKIPPED_SECRET_MISSING")

    started = now_utc()
    params = urlencode({
        "apiKey": key,
        "regions": "uk",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    })
    url = f"{BASE_URL}/{sport_key}/events/{event_id}/odds?{params}"
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "VeltrixAIAnalyst/1.0"},
        method="GET",
    )
    manifest: dict[str, object] = {
        "provider": "The Odds API",
        "endpoint": "/v4/sports/{sport}/events/{event_id}/odds",
        "event_id": event_id,
        "sport_key": sport_key,
        "canonical_fixture_id": fixture_id,
        "market": "h2h",
        "regions": ["uk"],
        "odds_format": "decimal",
        "request_count": 1,
        "retries": 0,
        "pagination_requests": 0,
        "expected_credit_cost": 1,
        "request_started_at": started.isoformat(),
        "retrieved_at": None,
        "provider_response_date": None,
        "http_status": None,
        "response_sha256": None,
        "response_bytes": None,
        "quota_remaining": None,
        "quota_used": None,
        "quota_last_cost": None,
        "quotes": [],
        "quote_count": 0,
        "outcome": "REQUEST_STARTED",
        "database_write": False,
    }
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
            headers = response.headers
            status = response.status
    except HTTPError as exc:
        body, headers, status = exc.read(4096), exc.headers, exc.code
    except (URLError, TimeoutError, OSError):
        manifest["retrieved_at"] = now_utc().isoformat()
        manifest["outcome"] = "NETWORK_ERROR_NO_RETRY"
        emit(manifest)
        return 0

    retrieved = now_utc()
    manifest["retrieved_at"] = retrieved.isoformat()
    manifest["provider_response_date"] = headers.get("Date")
    manifest["http_status"] = status
    manifest["response_bytes"] = len(body)
    manifest["response_sha256"] = hashlib.sha256(body).hexdigest()
    manifest["quota_remaining"] = headers.get("x-requests-remaining")
    manifest["quota_used"] = headers.get("x-requests-used")
    manifest["quota_last_cost"] = headers.get("x-requests-last")
    if status != 200:
        manifest["outcome"] = "HTTP_ERROR_NO_RETRY"
        emit(manifest)
        return 0

    try:
        payload = json.loads(body.decode("utf-8"))
        normalized = normalize_event_h2h_odds_response(
            payload,
            expected_event=event,
            canonical_fixture=fixture,
            retrieved_at=retrieved,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OddsApiMarketPayloadError) as exc:
        manifest["outcome"] = "INVALID_OR_MISMATCHED_EVENT_ODDS_RESPONSE"
        manifest["validation_error"] = (
            str(exc) if isinstance(exc, OddsApiMarketPayloadError) else "INVALID_JSON"
        )
        emit(manifest)
        return 0

    manifest.update(normalized)
    manifest["outcome"] = (
        "TIMESTAMPED_H2H_QUOTES_AVAILABLE"
        if normalized["quote_count"]
        else "ENDPOINT_ACCESS_CONFIRMED_NO_TIMESTAMPED_H2H_QUOTES"
    )
    manifest["quota_cost_within_one_credit_expectation"] = (
        str(manifest["quota_last_cost"]) == "1"
        if manifest["quota_last_cost"] is not None
        else None
    )
    emit(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
