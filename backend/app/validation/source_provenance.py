"""Validation rules for retrospective source-observation provenance.

A retrieved-at-only observation may carry available_at as a copy of its
capture timestamp. That does not make it point-in-time certified or imply
pre-match availability.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def is_valid_retrospective_observation(row: Mapping[str, Any]) -> bool:
    """Return whether an observation is safe to use as retrospective evidence.

    RETRIEVED_AT_ONLY records must not claim publication or independent
    availability timestamps. If available_at is populated, it must exactly
    equal retrieved_at (capture-time metadata), never precede retrieval.
    """
    retrieved_at = row.get("retrieved_at")
    available_at = row.get("available_at")
    http_status = row.get("http_status")

    return bool(
        row.get("availability_basis") == "RETRIEVED_AT_ONLY"
        and row.get("point_in_time_certifiable") is False
        and row.get("source_published_at") is None
        and retrieved_at is not None
        and (available_at is None or available_at == retrieved_at)
        and row.get("provider_response_id") is not None
        and http_status is not None
        and 200 <= http_status < 300
    )
