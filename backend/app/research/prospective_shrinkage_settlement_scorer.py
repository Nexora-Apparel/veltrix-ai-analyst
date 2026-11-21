"""Read-only, idempotent scoring of prospectively settled frozen-config forecasts."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.research.shrinkage_repair_metrics import evaluation_diagnostics

OUTCOMES = ("HOME", "DRAW", "AWAY")
PROSPECTIVE_AFTER = datetime.fromisoformat("2026-11-21T00:00:00+00:00")


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed


def score_settlements(
    forecasts: dict[str, Any], settlements: list[dict[str, Any]], *, frozen_config_sha256: str
) -> dict[str, Any]:
    eligible_forecasts: dict[str, dict[str, Any]] = {}
    exclusions: list[dict[str, str]] = []
    for forecast in forecasts.get("predictions", []):
        fixture_id = forecast.get("canonical_fixture_id")
        if not fixture_id:
            exclusions.append({"reason": "MISSING_CANONICAL_FIXTURE_ID"})
            continue
        if forecast.get("config_sha256") != frozen_config_sha256:
            exclusions.append({"fixture_id": str(fixture_id), "reason": "FROZEN_CONFIG_HASH_MISMATCH"})
            continue
        cutoff = _dt(forecast["prediction_cutoff_at"])
        kickoff = _dt(forecast["kickoff_at"])
        if cutoff >= kickoff:
            exclusions.append({"fixture_id": str(fixture_id), "reason": "PREDICTION_CUTOFF_NOT_BEFORE_KICKOFF"})
            continue
        if fixture_id in eligible_forecasts:
            exclusions.append({"fixture_id": str(fixture_id), "reason": "DUPLICATE_FORECAST_ID"})
            eligible_forecasts.pop(fixture_id, None)
            continue
        eligible_forecasts[fixture_id] = forecast

    settlement_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for settlement in settlements:
        fixture_id = settlement.get("canonical_fixture_id")
        if fixture_id:
            settlement_groups[str(fixture_id)].append(settlement)
    scored = []
    for fixture_id, forecast in sorted(eligible_forecasts.items()):
        matches = settlement_groups.get(str(fixture_id), [])
        if len(matches) != 1:
            exclusions.append({
                "fixture_id": str(fixture_id),
                "reason": "MISSING_SETTLEMENT" if not matches else "DUPLICATE_SETTLEMENTS",
            })
            continue
        settlement = matches[0]
        settled_at = _dt(settlement["settled_at"])
        observed_at = _dt(settlement["label_observed_at"])
        kickoff = _dt(forecast["kickoff_at"])
        if settled_at < PROSPECTIVE_AFTER:
            exclusions.append({"fixture_id": str(fixture_id), "reason": "NOT_SETTLED_AFTER_PREREGISTRATION_DATE"})
            continue
        if observed_at < kickoff or observed_at > settled_at:
            exclusions.append({"fixture_id": str(fixture_id), "reason": "INVALID_LABEL_OBSERVATION_TIMING"})
            continue
        label = settlement.get("label")
        if not isinstance(label, dict):
            exclusions.append({"fixture_id": str(fixture_id), "reason": "MISSING_SETTLED_LABEL"})
            continue
        probabilities = forecast.get("markets", {}).get("1X2")
        if not isinstance(probabilities, dict) or any(key not in probabilities for key in OUTCOMES):
            exclusions.append({"fixture_id": str(fixture_id), "reason": "MISSING_1X2_PROBABILITIES"})
            continue
        scored.append({
            "competition_id": str(forecast.get("canonical_competition_id", "UNKNOWN")),
            "kickoff_at": forecast["kickoff_at"],
            "label": label,
            "probabilities": {key: float(probabilities[key]) for key in OUTCOMES},
            "settled_at": settlement["settled_at"],
            "label_observed_at": settlement["label_observed_at"],
        })

    report = evaluation_diagnostics(scored) if scored else {
        "n": 0, "log_loss": None, "multiclass_brier": None,
        "reliability": None, "extreme_probability": None, "competition_breakdown": {},
    }
    return {
        "status": "PROSPECTIVE_SETTLEMENT_SCORE" if scored else "NO_ELIGIBLE_PROSPECTIVE_SETTLEMENTS",
        "frozen_config_sha256": frozen_config_sha256,
        "prospective_after": PROSPECTIVE_AFTER.isoformat(),
        "scored_fixture_count": len(scored),
        "metrics": report,
        "exclusions": exclusions,
        "idempotency_key": "canonical_fixture_id",
        "database_writes": 0,
        "provider_calls": 0,
        "odds_calls": 0,
        "telegram_notifications": 0,
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
    }


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: score_prospective_settlements.py FORECASTS_JSON SETTLEMENTS_JSON CONFIG_SHA256")
    forecast_payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    settlement_payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    report = score_settlements(
        forecast_payload, settlement_payload.get("settlements", []),
        frozen_config_sha256=sys.argv[3],
    )
    Path("prospective-settlement-report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
