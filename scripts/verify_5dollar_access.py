"""Verify 5DollarFootballAPI account plan and Brazil competition access.

Run after setting FIVE_DOLLAR_FOOTBALL_API_KEY in the local environment.
The script prints no credential values and does not fetch match history.
"""
from __future__ import annotations

import asyncio
import os
import sys

from app.providers.five_dollar import (
    FiveDollarFootballProvider,
    ProviderConfigurationError,
    ProviderError,
)


async def main() -> int:
    if not os.getenv("FIVE_DOLLAR_FOOTBALL_API_KEY", "").strip():
        print("BLOCKED: FIVE_DOLLAR_FOOTBALL_API_KEY is not configured.")
        return 2

    provider = FiveDollarFootballProvider()
    try:
        status = await provider.fetch_account_status()
        competitions = await provider.fetch_competitions(country_code="BR")
    except ProviderConfigurationError as exc:
        print(f"BLOCKED: {exc}")
        return 2
    except ProviderError as exc:
        print(f"PROVIDER CHECK FAILED: {exc}")
        return 1

    plan = str(status.get("plan") or "unknown").casefold()
    limits = status.get("limits") if isinstance(status.get("limits"), dict) else {}
    usage = status.get("usage") if isinstance(status.get("usage"), dict) else {}

    print(f"Provider: {provider.provider_name}")
    print(f"Account plan: {plan}")
    print(f"Request limit: {limits.get('rate_limit', 'unknown')}")
    print(f"Rate window seconds: {limits.get('rate_window_seconds', 'unknown')}")
    print(f"Burst per minute: {limits.get('burst_per_minute', 'unknown')}")
    print(f"Requests used today: {usage.get('today', 'unknown')}")
    print(f"Brazil competitions visible: {len(competitions)}")

    for competition in competitions:
        print(f"- {competition.competition_id}: {competition.name}")

    serie_b = [
        competition
        for competition in competitions
        if "serie b" in competition.name.casefold()
        or "second division" in competition.name.casefold()
    ]
    print(f"Brazil Serie B visible: {'yes' if serie_b else 'no'}")

    if plan != "community":
        print("QUALIFICATION: expected Community Access plan is not active.")
        return 1
    if not competitions:
        print("QUALIFICATION: no Brazil competitions are visible to this key.")
        return 1

    print("QUALIFICATION: account plan and Brazil league listing verified.")
    print("Historical fixture access still requires a separate bounded fixture probe.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
