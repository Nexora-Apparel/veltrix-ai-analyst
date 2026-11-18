"""Zero-odds-credit, read-only The Odds API v4 soccer catalogue probe.

Never prints request URLs, API keys, authorization data, or raw response bodies.
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

ENDPOINT = "https://api.the-odds-api.com/v4/sports/"
TIMEOUT_SECONDS = 20


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def emit(manifest: dict[str, object]) -> None:
    rendered = json.dumps(manifest, sort_keys=True, indent=2)
    Path("odds-api-catalogue-manifest.json").write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def main() -> int:
    key = os.environ.get("THE_ODDS_API_KEY", "").strip()
    manifest: dict[str, object] = {
        "provider": "The Odds API",
        "endpoint": "/v4/sports/",
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
        "active_soccer_sports_count": 0,
        "active_soccer_sport_keys": [],
        "outcome": "NOT_RUN",
    }
    if not key:
        manifest["outcome"] = "MISSING_SECRET"
        print("The Odds API: MISSING_SECRET (THE_ODDS_API_KEY)")
        emit(manifest)
        return 2

    request = Request(
        ENDPOINT + "?" + urlencode({"apiKey": key}),
        headers={"Accept": "application/json", "User-Agent": "VeltrixAIAnalyst/1.0"},
        method="GET",
    )
    manifest["request_started_at"] = utc_now()
    manifest["request_count"] = 1
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
            headers = response.headers
            status = response.status
    except HTTPError as exc:
        body = exc.read(4096)
        headers = exc.headers
        status = exc.code
    except (URLError, TimeoutError, OSError):
        manifest["retrieved_at"] = utc_now()
        manifest["outcome"] = "NETWORK_ERROR"
        emit(manifest)
        return 3

    manifest["retrieved_at"] = utc_now()
    manifest["http_status"] = status
    manifest["response_bytes"] = len(body)
    manifest["response_sha256"] = hashlib.sha256(body).hexdigest()
    manifest["quota_remaining"] = headers.get("x-requests-remaining")
    manifest["quota_used"] = headers.get("x-requests-used")
    manifest["quota_last_cost"] = headers.get("x-requests-last")

    if status != 200:
        manifest["outcome"] = "HTTP_ERROR"
        emit(manifest)
        return 4

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        manifest["outcome"] = "INVALID_JSON"
        emit(manifest)
        return 5

    if not isinstance(payload, list):
        manifest["outcome"] = "UNEXPECTED_SCHEMA"
        emit(manifest)
        return 6

    sports = [
        row for row in payload
        if isinstance(row, dict)
        and str(row.get("key", "")).startswith("soccer_")
        and row.get("active", True)
    ]
    keys = sorted({str(row["key"]) for row in sports if row.get("key")})
    manifest["active_soccer_sports_count"] = len(keys)
    manifest["active_soccer_sport_keys"] = keys
    manifest["outcome"] = (
        "AUTHENTICATED_SOCCER_CATALOGUE_AVAILABLE"
        if keys else "AUTHENTICATED_NO_ACTIVE_SOCCER_SPORTS"
    )
    emit(manifest)
    return 0 if keys else 7


if __name__ == "__main__":
    sys.exit(main())
