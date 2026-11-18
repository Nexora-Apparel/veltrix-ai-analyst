"""Manual one-request 5Dollar scheduled fixture catalogue probe.

No odds are requested, no pagination/retries occur, and no database is written.
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

from app.providers.fixture_catalogue import (
    FixtureCatalogueError,
    normalize_scheduled_fixture_catalogue,
)

ALLOWED_COMPETITION_IDS = {
    "3118717965",
    "522514093",
    "4160026622",
    "3614399544",
    "686337048",
    "3405541143",
    "4212821298",
}
BASE_URL = "https://api.5dollarfootballapi.com/v1/leagues"
TIMEOUT_SECONDS = 20


def now_utc() -> datetime:
    return datetime.now(UTC)


def emit(manifest: dict[str, object]) -> None:
    Path("5dollar-scheduled-fixtures-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, sort_keys=True, indent=2))


def main() -> int:
    competition_id = os.environ.get(
        "FIVEDOLLAR_COMPETITION_ID", "4160026622"
    ).strip()
    key = (
        os.environ.get("FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY", "").strip()
        or os.environ.get("FIVEDOLLARFOOTBALL_API_KEY", "").strip()
        or os.environ.get("FIVE_DOLLAR_FOOTBALL_API_KEY", "").strip()
    )
    manifest: dict[str, object] = {
        "provider": "5DollarFootballAPI",
        "endpoint": "/v1/leagues/{id}/fixtures",
        "competition_id": competition_id,
        "request_count": 0,
        "retries": 0,
        "pagination_requests": 0,
        "request_started_at": None,
        "retrieved_at": None,
        "http_status": None,
        "response_sha256": None,
        "response_bytes": None,
        "rate_limit_limit": None,
        "rate_limit_remaining": None,
        "rate_limit_reset": None,
        "future_fixture_count": 0,
        "excluded_nonfuture_count": 0,
        "pagination_has_more": None,
        "fixtures": [],
        "outcome": "NOT_RUN",
    }
    if competition_id not in ALLOWED_COMPETITION_IDS:
        manifest["outcome"] = "UNAPPROVED_COMPETITION"
        emit(manifest)
        return 2
    if not key:
        manifest["outcome"] = "MISSING_SECRET"
        emit(manifest)
        return 3

    started = now_utc()
    manifest["request_started_at"] = started.isoformat()
    manifest["request_count"] = 1
    url = f"{BASE_URL}/{competition_id}/fixtures?" + urlencode(
        {
            "start_time": int(started.timestamp()),
            "end_time": int((started + timedelta(days=30)).timestamp()),
            "status": "scheduled",
            "page": 1,
            "per_page": 100,
        }
    )
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "VeltrixAIAnalyst/1.0",
        },
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
    manifest["rate_limit_limit"] = headers.get("x-ratelimit-limit")
    manifest["rate_limit_remaining"] = headers.get("x-ratelimit-remaining")
    manifest["rate_limit_reset"] = headers.get("x-ratelimit-reset")
    if status != 200:
        manifest["outcome"] = "HTTP_ERROR"
        emit(manifest)
        return 5
    try:
        payload = json.loads(body.decode("utf-8"))
        fixtures, has_more, excluded = normalize_scheduled_fixture_catalogue(
            payload, competition_id=competition_id, as_of=retrieved
        )
    except (UnicodeDecodeError, json.JSONDecodeError, FixtureCatalogueError):
        manifest["outcome"] = "INVALID_FIXTURE_RESPONSE"
        emit(manifest)
        return 6

    manifest["future_fixture_count"] = len(fixtures)
    manifest["excluded_nonfuture_count"] = excluded
    manifest["pagination_has_more"] = has_more
    manifest["fixtures"] = list(fixtures)
    if has_more:
        manifest["outcome"] = "TRUNCATED_REVIEW_REQUIRED"
    else:
        manifest["outcome"] = (
            "FIXTURES_AVAILABLE" if fixtures else "NO_FUTURE_FIXTURES"
        )
    emit(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
