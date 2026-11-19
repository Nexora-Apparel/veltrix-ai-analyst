"""Fail-closed production certification gates for prospective model evidence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MARKET_KEYS = (
    "1X2",
    "BTTS",
    "OVER_UNDER_1_5",
    "OVER_UNDER_2_5",
    "OVER_UNDER_3_5",
)


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return parsed if parsed >= 0 else 0


def apply_prospective_certification_gates(
    evaluation: Mapping[str, Any],
    dataset: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach release gates; absent or unverified evidence always fails closed."""
    raw_markets = evaluation.get("markets")
    markets = raw_markets if isinstance(raw_markets, Mapping) else {}
    market_fixture_counts = {
        key: _nonnegative_int(
            (markets.get(key) or {}).get("fixtures")
            if isinstance(markets.get(key), Mapping)
            else 0
        )
        for key in MARKET_KEYS
    }
    settled_labels = _nonnegative_int(dataset.get("settled_label_rows"))
    settled_dates = _nonnegative_int(
        dataset.get("settled_distinct_kickoff_dates")
    )

    gates = {
        "walk_forward_fixtures_per_market": {
            "observed": market_fixture_counts,
            "required": 1000,
            "passed": all(
                count >= 1000 for count in market_fixture_counts.values()
            ),
        },
        "settled_prospective_fixtures": {
            "observed": settled_labels,
            "required": 300,
            "passed": settled_labels >= 300,
        },
        "distinct_kickoff_dates_with_settled_labels": {
            "observed": settled_dates,
            "required": 90,
            "passed": settled_dates >= 90,
        },
        "timestamped_odds_coverage": {
            "observed": None,
            "required": 0.98,
            "passed": False,
            "status": "NOT_EVALUATED_VALUE_BETTING_REMAINS_LOCKED",
        },
        "positive_net_roi_and_positive_lower_95_percent_bound": {
            "observed": None,
            "required": "net ROI > 0 and lower 95% bound > 0",
            "passed": False,
            "status": "NOT_EVALUATED_VALUE_BETTING_REMAINS_LOCKED",
        },
        "1x2_beats_bookmaker_brier_and_log_loss": {
            "observed": None,
            "required": "better than timestamped bookmaker baseline on both metrics",
            "passed": False,
            "status": "NOT_EVALUATED_CURRENT_RESEARCH_BASELINE_IS_NOT_BOOKMAKER_ODDS",
        },
    }
    core_passed = all(
        gates[key]["passed"]
        for key in (
            "walk_forward_fixtures_per_market",
            "settled_prospective_fixtures",
            "distinct_kickoff_dates_with_settled_labels",
        )
    )
    result = dict(evaluation)
    result["certification_gates"] = gates
    result["production_certification"] = (
        "ELIGIBLE_FOR_FORMAL_REVIEW"
        if core_passed and all(gate["passed"] for gate in gates.values())
        else "BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE"
    )
    # Formal review is not deployment approval; no automated gate can publish.
    result["production_promotion"] = "LOCKED"
    result["value_betting"] = "LOCKED"
    result["release_eligible"] = False
    result["certification_is_approval"] = False
    return result
