"""Offline reconciliation of Odds API events and 5Dollar scheduled fixtures."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.providers.event_matching import match_event_to_fixture

ODDS_MANIFEST = Path("odds-api-events-manifest.json")
FIXTURE_MANIFEST = Path("5dollar-scheduled-fixtures-manifest.json")
OUTPUT = Path("odds-api-5dollar-fixture-match-manifest.json")


def main() -> int:
    if not ODDS_MANIFEST.exists() or not FIXTURE_MANIFEST.exists():
        print("Both provider manifests are required for reconciliation.")
        return 2

    odds = json.loads(ODDS_MANIFEST.read_text(encoding="utf-8"))
    fixtures_payload = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    events = odds.get("events")
    fixtures = fixtures_payload.get("fixtures")
    if not isinstance(events, list) or not isinstance(fixtures, list):
        print("Provider manifests do not contain normalized arrays.")
        return 3

    decisions = [
        match_event_to_fixture(event, fixtures)
        for event in events
    ]
    status_counts = Counter(decision.status for decision in decisions)
    matches = [
        {
            "event_id": decision.event_id,
            "fixture_id": decision.fixture_id,
            "status": decision.status,
            "candidate_fixture_ids": list(decision.candidate_fixture_ids),
            "kickoff_delta_seconds": decision.kickoff_delta_seconds,
        }
        for decision in decisions
    ]
    complete = (
        odds.get("outcome") in {"EVENTS_AVAILABLE", "NO_FUTURE_EVENTS"}
        and fixtures_payload.get("outcome")
        in {"FIXTURES_AVAILABLE", "NO_FUTURE_FIXTURES"}
        and fixtures_payload.get("pagination_has_more") is False
    )
    exact_matches = status_counts.get("MATCHED", 0)
    result = {
        "provider": "The Odds API + 5DollarFootballAPI",
        "odds_event_count": len(events),
        "5dollar_fixture_count": len(fixtures),
        "catalogues_complete": complete,
        "match_status_counts": dict(sorted(status_counts.items())),
        "exact_unique_match_count": exact_matches,
        "matches": matches,
        "market_probe_candidate": bool(complete and exact_matches == 1),
        "market_probe_authorized": bool(complete and exact_matches == 1),
        "outcome": (
            "ONE_EXACT_MATCH_CANDIDATE_REQUIRES_REVIEW"
            if complete and exact_matches == 1
            else "CATALOGUE_TRUNCATED"
            if not complete
            else "NO_UNIQUE_EXACT_MATCH"
            if exact_matches == 0
            else "MULTIPLE_EXACT_MATCHES"
        ),
    }
    OUTPUT.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
