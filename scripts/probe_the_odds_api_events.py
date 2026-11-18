"""Manual, one-sport, zero-odds-credit The Odds API event discovery probe.

This calls only /v4/sports/{sport}/events. It never requests odds markets,
writes to Neon, retries, or logs credentials/raw responses.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.providers.the_odds_api_events import (
    OddsApiEventPayloadError,
    normalize_event_catalogue,
)

ALLOWED_SPORT_KEYS = {
    "soccer_brazil_campeonato",
    "soccer_brazil_serie_b",
    "soccer_epl",
    "soccer_france_ligue_one",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_spain_la_liga",
}
BASE_URL = "https://api.the-odds-api.com/v4/sports"
TIMEOUT_SECONDS = 20


def now_utc() -> datetime:
    return datetime.now(UTC)


def emit(manifest: dict[str, object]) -> None:
    Path("odds-api-events-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, sort_keys=True, indent=2))


def main() -> int:
    sport_key = os.environ.get("ODDS_API_SPORT_KEY", "soccer_epl").strip()
    key = os.environ.get("THE_ODDS_API_KEY", "").strip()
    started: datetime | None = None
    manifest: dict[str, object] = {
        "provider": "The Odds API",
        "endpoint": "/v4/sports/{sport}/events",
        "sport_key": sport_key,
        "request_count": 0,
        "retries": 0,
        "request_started_at": None,
        "retrieved_at": None,
        "http_status": None,
        "response_sha256": None,
        "response_bytes": None,
        "quota_remaining": None,
        "quota_used": None,
        "quota_last_cost": None,
        "future_event_count": 0,
        "events": [],
        "outcome": "NOT_RUN",
    }
    if sport_key not in ALLOWED_SPORT_KEYS:
        manifest["outcome"] = "UNAPPROVED_SPORT_KEY"
        emit(manifest)
        return 2
    if not key:
        manifest["outcome"] = "MISSING_SECRET"
        emit(manifest)
        return 3

    started = now_utc()
    manifest["request_started_at"] = started.isoformat()
    manifest["request_count"] = 1
    url = f"{BASE_URL}/{sport_key}/events?" + urlencode({
        "apiKey": key, "dateFormat": "iso", "commenceTimeFrom": started.isoformat(),
        "commenceTimeTo": (started + timedelta(days=30)).isoformat()
    })
    request = Request(
        url, headers={"Accept": "application/json", "User-Agent": "VeltrixAIAnalyst/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
            headers = response.headers
            status = response.status
    except HTTPError as exc:
        body, headers, status = exc.read(4096), exc.headers, exc.code
    except (URLError, TimeoutError, OSError):
        manifest["retrieved_at"] = now_utc().isoformat()
        manifest["outcome"] = "NETWORK_ERROR"
        emit(manifest)
        return 4

    retrieved = now_utc()
    manifest["retrieved_at"] = retrieved.isoformat()
    manifest["http_status"] = status
    manifest["response_bytes"] = len(body)
    manifest["response_sha256"] = hashlib.sha256(body).hexdigest()
    manifest["quota_remaining"] = headers.get("x-requests-remaining")
    manifest["quota_used"] = headers.get("x-requests-used")
    manifest["quota_last_cost"] = headers.get("x-requests-last")
    if status != 200:
        manifest["outcome"] = "HTTP_ERROR"
        emit(manifest)
        return 5
    try:
        payload = json.loads(body.decode("utf-8"))
        events = normalize_event_catalogue(
            payload, requested_sport_key=sport_key, as_of=retrieved
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OddsApiEventPayloadError):
        manifest["outcome"] = "INVALID_EVENT_RESPONSE"
        emit(manifest)
        return 6

    manifest["future_event_count"] = len(events)
    manifest["events"] = list(events)
    manifest["outcome"] = "EVENTS_AVAILABLE" if events else "NO_FUTURE_EVENTS"
    emit(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
