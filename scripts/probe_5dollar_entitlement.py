"""Probe and print only non-sensitive 5Dollar plan and quota fields."""

from __future__ import annotations

import asyncio
import json
import os

from app.providers.five_dollar import FiveDollarFootballProvider

SAFE_TERMS = ("plan", "tier", "request", "limit", "remaining", "used", "history", "season", "league", "coverage", "reset")
SENSITIVE_TERMS = ("key", "token", "secret", "email", "account_id", "customer")


def _safe_fields(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = str(key).casefold()
            if any(term in normalized for term in SENSITIVE_TERMS):
                continue
            if any(term in normalized for term in SAFE_TERMS):
                if isinstance(item, (str, int, float, bool)) or item is None:
                    result[str(key)] = item
                elif isinstance(item, list):
                    result[str(key)] = {"item_count": len(item)}
                elif isinstance(item, dict):
                    result[str(key)] = _safe_fields(item)
        return result
    return {}


async def _run() -> dict:
    provider = FiveDollarFootballProvider()
    status = await provider.fetch_account_status()
    return _safe_fields(status)


def main() -> int:
    if not (
        os.getenv("FIVEDOLLARFOOTBALL_COMMUNITY_API_KEY")
        or os.getenv("FIVEDOLLARFOOTBALL_API_KEY")
        or os.getenv("FIVE_DOLLAR_FOOTBALL_API_KEY")
    ):
        raise SystemExit("5DOLLAR_API_KEY_REQUIRED")
    status = asyncio.run(_run())
    print(json.dumps({"provider_entitlement_fields": status}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
