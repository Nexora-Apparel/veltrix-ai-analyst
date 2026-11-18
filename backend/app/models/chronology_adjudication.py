"""Evidence-backed kickoff corrections for retrospective research only.

Raw provider fixture timestamps are immutable. This layer applies separately
sourced official competition kickoff adjudications to research inputs and
records the raw/adjudicated values for auditability.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.models.retrospective import ResearchFixture


def load_kickoff_adjudications(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("adjudications"), list):
        raise ValueError("invalid kickoff adjudication registry")
    output: dict[str, dict[str, Any]] = {}
    for item in payload["adjudications"]:
        fixture_id = str(item["provider_fixture_id"])
        if fixture_id in output:
            raise ValueError(f"duplicate kickoff adjudication: {fixture_id}")
        raw = datetime.fromisoformat(item["raw_provider_kickoff_at"])
        official = datetime.fromisoformat(item["official_kickoff_at"])
        if raw.tzinfo is None or official.tzinfo is None:
            raise ValueError("kickoff adjudication timestamps must be timezone-aware")
        if not item.get("source_url") or not item.get("reason"):
            raise ValueError("kickoff adjudication requires source_url and reason")
        output[fixture_id] = item
    return output


def apply_kickoff_adjudications(
    fixtures: list[ResearchFixture], adjudications: dict[str, dict[str, Any]]
) -> tuple[list[ResearchFixture], list[dict[str, str]]]:
    applied: list[ResearchFixture] = []
    audit: list[dict[str, str]] = []
    seen: set[str] = set()
    for fixture in fixtures:
        item = adjudications.get(fixture.fixture_id)
        if item is None:
            applied.append(fixture)
            continue
        raw = datetime.fromisoformat(item["raw_provider_kickoff_at"])
        official = datetime.fromisoformat(item["official_kickoff_at"])
        if fixture.kickoff_at != raw:
            raise ValueError(
                f"kickoff adjudication raw timestamp mismatch for fixture {fixture.fixture_id}"
            )
        applied.append(replace(fixture, kickoff_at=official))
        audit.append({
            "provider_fixture_id": fixture.fixture_id,
            "raw_provider_kickoff_at": raw.isoformat(),
            "official_kickoff_at": official.isoformat(),
            "source_url": item["source_url"],
            "reason": item["reason"],
            "competition": str(item.get("competition", "")),
            "cbf_match_reference": str(item.get("cbf_match_reference", "")),
            "fixture": str(item.get("fixture", "")),
            "reviewed_at": str(item.get("reviewed_at", "")),
        })
        seen.add(fixture.fixture_id)
    unused = set(adjudications) - seen
    if unused:
        raise ValueError(f"kickoff adjudications did not match source rows: {sorted(unused)}")
    return applied, audit
