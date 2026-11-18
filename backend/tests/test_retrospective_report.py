from __future__ import annotations

import hashlib
import json

import pytest

from app.models.retrospective_report import validate_retrospective_report


def sealed_report() -> dict:
    report = {
        "dataset_type": "RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED",
        "fixture_count": 2,
        "team_count": 4,
        "source": {
            "source_rows": 3,
            "finished_labeled_rows": 2,
            "unknown_unlabeled_rows_excluded": 1,
            "invalid_rows": 0,
            "identity_namespace": "PROVIDER_LOCAL_TEAM_IDS",
            "feature_semantics": "RETROSPECTIVE_LAGGED_RESULTS_NOT_HISTORICAL_PIT_REPLAY",
        },
        "predictions": [
            {
                "fixture_id": "fx-1",
                "kickoff_at": "2026-01-01T15:00:00+00:00",
                "actual_home_goals": 1,
                "actual_away_goals": 0,
                "elo_1x2": [0.5, 0.25, 0.25],
                "poisson_1x2": [0.45, 0.3, 0.25],
                "goal_rates": [1.4, 1.1],
                "rho": 0.0,
                "ensemble_elo_weight": 0.35,
            },
            {
                "fixture_id": "fx-2",
                "kickoff_at": "2026-01-02T15:00:00+00:00",
                "actual_home_goals": 0,
                "actual_away_goals": 0,
                "elo_1x2": [0.4, 0.3, 0.3],
                "poisson_1x2": [0.38, 0.32, 0.3],
                "goal_rates": [1.2, 1.0],
                "rho": 0.01,
                "ensemble_elo_weight": 0.4,
            },
        ],
        "elo": {"matches": 2.0, "brier": 0.5, "log_loss": 0.9},
        "poisson": {"matches": 2.0, "brier": 0.6, "log_loss": 1.0},
        "ensemble": {"matches": 2.0, "brier": 0.4, "log_loss": 0.8},
        "ensemble_elo_weight_baseline": 0.35,
        "ensemble_elo_weight_mean": 0.375,
        "ensemble_elo_weight_min": 0.35,
        "ensemble_elo_weight_max": 0.4,
        "dixon_coles_rho_full_corpus_diagnostic_only": 0.01,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["report_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def reseal(report: dict) -> dict:
    unsigned = {key: value for key, value in report.items() if key != "report_sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["report_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return report


def test_accepts_valid_sealed_retrospective_report() -> None:
    validate_retrospective_report(sealed_report())


def test_rejects_hash_mismatch() -> None:
    report = sealed_report()
    report["team_count"] = 5
    with pytest.raises(ValueError, match="REPORT_SHA256_MISMATCH"):
        validate_retrospective_report(report)


def test_rejects_non_normalized_probabilities_even_with_valid_hash() -> None:
    report = sealed_report()
    report["predictions"][0]["elo_1x2"] = [0.6, 0.3, 0.2]
    reseal(report)
    with pytest.raises(ValueError, match="REPORT_PROBABILITIES_NOT_NORMALIZED"):
        validate_retrospective_report(report)


def test_rejects_duplicate_fixture_ids_even_with_valid_hash() -> None:
    report = sealed_report()
    report["predictions"][1]["fixture_id"] = "fx-1"
    reseal(report)
    with pytest.raises(ValueError, match="REPORT_DUPLICATE_OR_INVALID_FIXTURE_ID"):
        validate_retrospective_report(report)


def test_rejects_source_accounting_mismatch() -> None:
    report = sealed_report()
    report["source"]["source_rows"] = 4
    reseal(report)
    with pytest.raises(ValueError, match="REPORT_SOURCE_ACCOUNTING_MISMATCH"):
        validate_retrospective_report(report)


def test_rejects_naive_prediction_timestamp() -> None:
    report = sealed_report()
    report["predictions"][0]["kickoff_at"] = "2026-01-01T15:00:00"
    reseal(report)
    with pytest.raises(ValueError, match="PREDICTION_TIMESTAMP_NOT_AWARE"):
        validate_retrospective_report(report)


def test_rejects_scorecard_match_count_mismatch() -> None:
    report = sealed_report()
    report["ensemble"]["matches"] = 1.0
    reseal(report)
    with pytest.raises(ValueError, match="REPORT_SCORECARD_MATCH_COUNT_MISMATCH:ensemble"):
        validate_retrospective_report(report)


def test_rejects_nan_before_accepting_hash() -> None:
    report = sealed_report()
    report["predictions"][0]["rho"] = float("nan")
    with pytest.raises(ValueError, match="REPORT_NOT_JSON_SAFE"):
        validate_retrospective_report(report)
