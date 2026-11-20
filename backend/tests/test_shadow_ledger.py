from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.research.shadow_ledger import validate_shadow_report

COMMIT = "a" * 40
NOW = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def report() -> dict:
    cutoff = NOW - timedelta(minutes=30)
    kickoff = NOW + timedelta(hours=2)
    return {
        "generated_at": NOW.isoformat(),
        "status": "SHADOW_FORECASTS_READY",
        "research_only": True,
        "dataset_sha256": "b" * 64,
        "production_promotion": "LOCKED",
        "release_eligible": False,
        "value_betting": "LOCKED",
        "training_fixture_count": 40,
        "training_cutoff_at": (cutoff - timedelta(days=1)).isoformat(),
        "training_data_sha256": "c" * 64,
        "model": {"version": "hierarchical-poisson-shadow-v1"},
        "forecast_count": 1,
        "abstention_count": 0,
        "predictions": [{
            "canonical_fixture_id": "00000000-0000-0000-0000-000000000001",
            "kickoff_at": kickoff.isoformat(),
            "prediction_cutoff_at": cutoff.isoformat(),
            "generated_at": NOW.isoformat(),
            "training_cutoff_at": (cutoff - timedelta(days=1)).isoformat(),
            "training_data_sha256": "c" * 64,
            "publication_status": "NOT_PUBLISHED",
            "value_betting_status": "LOCKED",
            "markets": {
                "1X2": {"HOME": 0.5, "DRAW": 0.25, "AWAY": 0.25},
                "BTTS": {"YES": 0.6, "NO": 0.4},
                "TOTALS_1_5": {"OVER": 0.7, "UNDER": 0.3},
                "TOTALS_2_5": {"OVER": 0.5, "UNDER": 0.5},
                "TOTALS_3_5": {"OVER": 0.2, "UNDER": 0.8},
            },
        }],
        "abstentions": [],
    }


def test_shadow_ledger_builds_stable_idempotency_key():
    first = validate_shadow_report(report(), code_commit=COMMIT)
    second = validate_shadow_report(report(), code_commit=COMMIT)
    assert first["run_key"] == second["run_key"]
    assert first["report_sha256"] == second["report_sha256"]
    assert first["forecast_count"] == 1


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("research_only", False, "RESEARCH_ONLY_FLAG_REQUIRED"),
        ("production_promotion", "APPROVED", "PRODUCTION_PROMOTION_MUST_REMAIN_LOCKED"),
        ("release_eligible", True, "RELEASE_MUST_REMAIN_INELIGIBLE"),
        ("value_betting", "UNLOCKED", "VALUE_BETTING_MUST_REMAIN_LOCKED"),
    ],
)
def test_shadow_ledger_rejects_any_production_or_value_betting_unlock(field, value, error):
    candidate = report()
    candidate[field] = value
    with pytest.raises(ValueError, match=error):
        validate_shadow_report(candidate, code_commit=COMMIT)


def test_shadow_ledger_rejects_published_or_value_bet_forecast():
    candidate = report()
    candidate["predictions"][0]["publication_status"] = "PUBLISHED"
    with pytest.raises(ValueError, match="SHADOW_FORECAST_MUST_NOT_BE_PUBLISHED"):
        validate_shadow_report(candidate, code_commit=COMMIT)


def test_shadow_ledger_rejects_invalid_probability_distribution():
    candidate = report()
    candidate["predictions"][0]["markets"]["1X2"]["HOME"] = 0.8
    with pytest.raises(ValueError, match="FORECAST_MARKET_PROBABILITIES_UNBALANCED"):
        validate_shadow_report(candidate, code_commit=COMMIT)


def test_shadow_ledger_rejects_post_kickoff_or_late_training_timestamps():
    candidate = report()
    candidate["predictions"][0]["generated_at"] = (
        NOW + timedelta(hours=3)
    ).isoformat()
    with pytest.raises(ValueError, match="FORECAST_PREMATCH_CHRONOLOGY_INVALID"):
        validate_shadow_report(candidate, code_commit=COMMIT)


def test_shadow_ledger_rejects_more_than_daily_fixture_cap():
    candidate = report()
    candidate["predictions"] = candidate["predictions"] * 26
    candidate["forecast_count"] = 26
    with pytest.raises(ValueError, match="SHADOW_FORECAST_LIMIT_EXCEEDED"):
        validate_shadow_report(candidate, code_commit=COMMIT)
