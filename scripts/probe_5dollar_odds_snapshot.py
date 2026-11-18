"""One-request 5Dollar fixture-odds snapshot probe.

No retries, no pagination, no persistence of raw odds. The artifact contains
only a response hash and a compact schema/1X2-opening summary.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://api.5dollarfootballapi.com/v1"
OUTPUT = Path("probe-artifact/odds-snapshot-manifest.json")


def summarize_bookmaker(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"malformed": True}
    odds = row.get("odds") if isinstance(row.get("odds"), dict) else {}
    one_x_two = odds.get("1x2") if isinstance(odds.get("1x2"), dict) else {}
    opening = one_x_two.get("opening") if isinstance(one_x_two.get("opening"), dict) else None
    return {
        "name": row.get("name"),
        "slug": row.get("slug"),
        "markets": sorted(str(key) for key in odds),
        "one_x_two_opening": (
            {
                "home": opening.get("home"),
                "draw": opening.get("draw"),
                "away": opening.get("away"),
                "opened_at": opening.get("opened_at"),
            }
            if opening is not None
            else None
        ),
        "one_x_two_closing_fields": (
            sorted(str(key) for key in one_x_two.get("closing", {}))
            if isinstance(one_x_two.get("closing"), dict)
            else []
        ),
    }


def main() -> int:
    key = os.getenv("FIVE_DOLLAR_FOOTBALL_API_KEY", "").strip()
    fixture_id = os.getenv("ODDS_PROBE_FIXTURE_ID", "").strip()
    if not key:
        print("BLOCKED: repository API secret is not configured")
        return 2
    if not re.fullmatch(r"[0-9]+", fixture_id):
        print("BLOCKED: fixture id must contain digits only")
        return 2

    url = f"{BASE_URL}/fixtures/{fixture_id}/odds"
    started_at = datetime.now(UTC)
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            timeout=20.0,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        print(f"PROBE FAILED: network error ({type(exc).__name__}); request count=1")
        return 1
    retrieved_at = datetime.now(UTC)
    body = response.content
    manifest: dict[str, Any] = {
        "provider": "5DollarFootballAPI",
        "endpoint": f"/v1/fixtures/{fixture_id}/odds",
        "fixture_id": fixture_id,
        "request": {"count": 1, "retries": 0, "pagination_followed": False},
        "request_started_at_utc": started_at.isoformat(),
        "retrieved_at_utc": retrieved_at.isoformat(),
        "http_status": response.status_code,
        "response_bytes": len(body),
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "response_date_header": response.headers.get("Date"),
        "rate_limit_headers": {
            name: response.headers.get(name)
            for name in ("x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset")
            if response.headers.get(name) is not None
        },
    }

    if response.status_code in (401, 403):
        manifest["access_result"] = "AUTHENTICATION_OR_ENTITLEMENT_BLOCKED"
        manifest["stop_reason"] = f"HTTP {response.status_code}; no retry attempted"
    elif response.status_code == 429:
        manifest["access_result"] = "RATE_LIMITED"
        manifest["stop_reason"] = "HTTP 429; no retry attempted"
    elif response.status_code >= 300:
        manifest["access_result"] = "HTTP_ERROR"
        manifest["stop_reason"] = f"HTTP {response.status_code}; redirects/errors not followed"
    else:
        try:
            payload = response.json()
        except ValueError:
            manifest["access_result"] = "INVALID_JSON"
            manifest["stop_reason"] = "Response was not valid JSON"
        else:
            data = payload.get("data") if isinstance(payload, dict) else None
            if (
                not isinstance(payload, dict)
                or payload.get("success") != 1
                or not isinstance(data, dict)
                or str(data.get("fixture_id")) != fixture_id
                or not isinstance(data.get("bookmakers"), list)
            ):
                manifest["access_result"] = "UNEXPECTED_RESPONSE_SCHEMA"
                manifest["top_level_keys"] = sorted(payload) if isinstance(payload, dict) else []
                manifest["data_keys"] = sorted(data) if isinstance(data, dict) else []
                manifest["stop_reason"] = "Response envelope or fixture identity did not match"
            else:
                manifest["bookmaker_count"] = len(data["bookmakers"])
                manifest["bookmakers"] = [
                    summarize_bookmaker(row) for row in data["bookmakers"]
                ]
                bet365 = [
                    row for row in data["bookmakers"]
                    if isinstance(row, dict) and row.get("slug") == "bet365"
                ]
                timestamped_opening = any(
                    isinstance(row.get("odds"), dict)
                    and isinstance(row["odds"].get("1x2"), dict)
                    and isinstance(row["odds"]["1x2"].get("opening"), dict)
                    and row["odds"]["1x2"]["opening"].get("opened_at")
                    for row in bet365
                )
                if timestamped_opening:
                    manifest["access_result"] = "ODDS_SNAPSHOT_ACCESS_CONFIRMED"
                    manifest["stop_reason"] = "Timestamped Bet365 1X2 opening received; one request only"
                elif not data["bookmakers"]:
                    manifest["access_result"] = "ENDPOINT_ACCESS_CONFIRMED_NO_BOOKMAKERS"
                    manifest["stop_reason"] = "Endpoint returned no bookmakers for this fixture"
                elif not bet365:
                    manifest["access_result"] = "ENDPOINT_ACCESS_CONFIRMED_BET365_NOT_RETURNED"
                    manifest["stop_reason"] = "Endpoint returned bookmakers but no Bet365 row"
                else:
                    manifest["access_result"] = "ENDPOINT_ACCESS_CONFIRMED_NO_TIMESTAMPED_1X2_OPENING"
                    manifest["stop_reason"] = "Bet365 returned without a timestamped 1X2 opening"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest.get("access_result") in {
        "ODDS_SNAPSHOT_ACCESS_CONFIRMED",
        "ENDPOINT_ACCESS_CONFIRMED_NO_BOOKMAKERS",
        "ENDPOINT_ACCESS_CONFIRMED_BET365_NOT_RETURNED",
        "ENDPOINT_ACCESS_CONFIRMED_NO_TIMESTAMPED_1X2_OPENING",
        "AUTHENTICATION_OR_ENTITLEMENT_BLOCKED",
        "RATE_LIMITED",
        "HTTP_ERROR",
    } else 1


if __name__ == "__main__":
    sys.exit(main())
