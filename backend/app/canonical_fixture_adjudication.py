"""Deterministic collision detection and evidence hashing for source-local fixture links."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from typing import Any

POLICY_VERSION = "veltrix-exact-provider-fixture-link-v1"
REVIEWER_ID = "VELTRIX_EXACT_PROVIDER_FIXTURE_LINK_ADJUDICATION_V1"
EVIDENCE_URI = (
    "https://github.com/Nexora-Apparel/veltrix-ai-analyst/"
    "blob/main/docs/policies/exact-provider-fixture-link-adjudication-v1.md"
)
COLLISION_WINDOW_SECONDS = 120
REVIEWED_MAPPING_STATUSES = frozenset(
    {"SOURCE_IDENTITY_REVIEWED", "REAL_WORLD_IDENTITY_VERIFIED"}
)


def find_fixture_link_collisions(
    rows: list[dict[str, Any]],
    *,
    window_seconds: int = COLLISION_WINDOW_SECONDS,
) -> dict[int, tuple[int, ...]]:
    """Return source-link IDs that collide on canonical competition, teams and kickoff.

    Only the same ordered home/away pairing within the same canonical competition
    is treated as a duplicate candidate. The function never merges or deletes rows.
    """
    if window_seconds < 0:
        raise ValueError("window_seconds must be non-negative")
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    seen_link_ids: set[int] = set()
    for row in rows:
        link_id = int(row["link_id"])
        if link_id in seen_link_ids:
            raise ValueError("duplicate fixture source link IDs")
        seen_link_ids.add(link_id)
        kickoff = row["kickoff_at"]
        if not isinstance(kickoff, datetime) or kickoff.tzinfo is None:
            raise ValueError("fixture kickoff must be timezone-aware")
        key = (
            str(row["canonical_competition_id"]),
            str(row["home_canonical_team_id"]),
            str(row["away_canonical_team_id"]),
        )
        grouped[key].append(row)

    collisions: dict[int, set[int]] = defaultdict(set)
    for candidates in grouped.values():
        candidates.sort(key=lambda item: item["kickoff_at"])
        for index, left in enumerate(candidates):
            for right in candidates[index + 1 :]:
                delta = (right["kickoff_at"] - left["kickoff_at"]).total_seconds()
                if delta > window_seconds:
                    break
                if delta >= 0:
                    left_id, right_id = int(left["link_id"]), int(right["link_id"])
                    collisions[left_id].add(right_id)
                    collisions[right_id].add(left_id)
    return {
        link_id: tuple(sorted(other_ids))
        for link_id, other_ids in collisions.items()
    }


def evidence_sha256(evidence: dict[str, Any]) -> str:
    """Hash a stable JSON representation of the exact adjudication evidence."""
    def normalize(value: Any) -> Any:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                raise ValueError("evidence datetimes must be timezone-aware")
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        return value

    canonical = json.dumps(
        normalize(evidence),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
