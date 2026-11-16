"""One-request, one-page 5Dollar Brazil Serie B fixture endpoint probe.

No retries, no pagination, no persistence, no odds endpoints. The response body
is summarized and hashed; raw provider data is never printed or uploaded.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://api.5dollarfootballapi.com/v1"
COMPETITION_ID = "522514093"
START = datetime(2026, 11, 7, 0, 0, tzinfo=timezone.utc)
END = datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)
PER_PAGE = 100
OUTPUT = Path("probe-artifact/manifest.json")


def timestamp_candidates(value: Any, prefix: str = "") -> dict[str, Any]:
    found: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).casefold()
            if any(token in lowered for token in ("time", "date", "timestamp", "_ts", "updated", "created")):
                found[path] = item if isinstance(item, (str, int, float, type(None))) else type(item).__name__
            if isinstance(item, (dict, list)):
                found.update(timestamp_candidates(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value[:10]):
            if isinstance(item, (dict, list)):
                found.update(timestamp_candidates(item, f"{prefix}[{index}]"))
    return found


def main() -> int:
    key = os.getenv("FIVE_DOLLAR_FOOTBALL_API_KEY", "").strip()
    if not key:
        print("BLOCKED: repository secret is not configured")
        return 2

    params = {
        "start_time": int(START.timestamp()),
        "end_time": int(END.timestamp()),
        "status": "all",
        "page": 1,
        "per_page": PER_PAGE,
    }
    url = f"{BASE_URL}/leagues/{COMPETITION_ID}/fixtures"
    try:
        response = httpx.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            timeout=20.0,
            follow_redirects=False,
        )
    except httpx.HTTPError as exc:
        print(f"PROBE FAILED: network error ({type(exc).__name__}); request count=1")
        return 1

    body = response.content
    digest = hashlib.sha256(body).hexdigest()
    manifest: dict[str, Any] = {
        "provider": "5DollarFootballAPI",
        "endpoint": f"/v1/leagues/{COMPETITION_ID}/fixtures",
        "competition_id": COMPETITION_ID,
        "window_utc": {"start_inclusive": START.isoformat(), "end_exclusive": END.isoformat()},
        "request": {"count": 1, "page": 1, "per_page": PER_PAGE, "retries": 0, "pagination_followed": False},
        "http_status": response.status_code,
        "response_bytes": len(body),
        "response_sha256": digest,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    if response.status_code == 429:
        manifest["stop_reason"] = "HTTP 429; no retry attempted"
    elif response.status_code in (401, 403):
        manifest["stop_reason"] = f"HTTP {response.status_code}; entitlement/authentication blocked"
    elif response.status_code >= 300:
        manifest["stop_reason"] = f"HTTP {response.status_code}; redirects and errors are not followed"
    else:
        try:
            payload = response.json()
        except ValueError:
            manifest["stop_reason"] = "Response was not valid JSON"
        else:
            if not isinstance(payload, dict) or payload.get("success") != 1 or not isinstance(payload.get("data"), list):
                manifest["stop_reason"] = "Unexpected response envelope/schema"
                manifest["top_level_keys"] = sorted(payload.keys()) if isinstance(payload, dict) else []
            else:
                rows = payload["data"]
                manifest["success"] = True
                manifest["row_count"] = len(rows)
                manifest["top_level_keys"] = sorted(payload.keys())
                manifest["pagination"] = payload.get("pagination")
                manifest["has_more"] = bool(
                    isinstance(payload.get("pagination"), dict)
                    and payload["pagination"].get("has_more")
                )
                manifest["fixture_field_union"] = sorted({
                    str(key) for row in rows[:100] if isinstance(row, dict) for key in row.keys()
                })
                manifest["first_fixture_timestamp_fields"] = (
                    timestamp_candidates(rows[0]) if rows and isinstance(rows[0], dict) else {}
                )
                manifest["first_fixture_sample"] = (
                    {
                        "id": rows[0].get("id"),
                        "status": rows[0].get("status"),
                        "kickoff_utc": rows[0].get("kickoff_utc"),
                        "kickoff_ts": rows[0].get("kickoff_ts"),
                    }
                    if rows and isinstance(rows[0], dict) else None
                )
                manifest["stop_reason"] = (
                    "First page reports more data; probe stopped without pagination"
                    if manifest["has_more"] else "Single-page probe complete"
                )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
