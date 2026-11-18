from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta

import pytest

from app.validation.paired_chronological import evaluate_paired_chronological_report
from scripts.evaluate_paired_chronological import main as evaluate_cli_main

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def make_report(count: int = 80) -> dict:
    predictions = []
    for index in range(count):
        kickoff = BASE + timedelta(days=index // 2)
        elo = [0.55, 0.25, 0.20] if index % 3 else [0.25, 0.30, 0.45]
        poisson = [0.48, 0.29, 0.23] if index % 4 else [0.30, 0.30, 0.40]
        weight = 0.35 if index < 50 else 0.5
        predictions.append({
            "fixture_id": f"fx-{index:03d}",
            "kickoff_at": kickoff.isoformat(),
            "actual_home_goals": 1 if index % 3 else 0,
            "actual_away_goals": 0 if index % 3 else 1,
            "elo_1x2": elo,
            "poisson_1x2": poisson,
            "ensemble_elo_weight": weight,
        })
    unsigned = {
        "dataset_type": "RETROSPECTIVE_RESEARCH_NOT_PIT_CERTIFIED",
        "fixture_count": count,
        "predictions": predictions,
    }
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False)
    unsigned["report_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return unsigned


def test_paired_report_keeps_three_models_on_identical_fixtures():
    result = evaluate_paired_chronological_report(make_report(), resamples=100, block_size=8)
    assert result["fixture_count"] == 80
    assert set(result["overall"]) == {"elo", "poisson", "ensemble"}
    assert all(value["matches"] == 80 for value in result["overall"].values())


def test_periods_keep_simultaneous_kickoffs_together():
    result = evaluate_paired_chronological_report(make_report(40), resamples=100, block_size=5)
    periods = result["chronological_periods"]
    assert sum(period["matches"] for period in periods) == 40
    assert all(period["matches"] % 2 == 0 for period in periods)


def test_cold_start_and_warmup_phases_account_for_every_fixture():
    result = evaluate_paired_chronological_report(make_report(80), resamples=100, block_size=8)
    phases = result["cold_start_warmup"]
    assert sum(phase["matches"] for phase in phases) == 80
    assert phases[0]["matches"] == 2
    assert phases[-1]["matches"] > 0


def test_bootstrap_is_deterministic_and_paired():
    report = make_report(40)
    first = evaluate_paired_chronological_report(report, resamples=100, block_size=6, seed=7)
    second = evaluate_paired_chronological_report(report, resamples=100, block_size=6, seed=7)
    assert first["paired_block_bootstrap"] == second["paired_block_bootstrap"]
    bootstrap = first["paired_block_bootstrap"]
    assert bootstrap["resample_size_min"] >= 40
    assert bootstrap["resample_size_min"] % 2 == 0
    comparisons = first["paired_block_bootstrap"]["comparisons"]
    assert set(comparisons) == {"elo_minus_poisson", "elo_minus_ensemble", "poisson_minus_ensemble"}
    for comparison in comparisons.values():
        for metric in ("brier", "log_loss"):
            low, high = comparison[metric]["ci_95"]
            assert low <= high


def test_calibration_reports_classwise_reliability_bands_for_each_model():
    result = evaluate_paired_chronological_report(make_report(), resamples=100, block_size=8)
    classes = result["calibration_reliability"]["classes"]
    assert set(classes) == {"home", "draw", "away"}
    for class_data in classes.values():
        assert set(class_data) == {"elo", "poisson", "ensemble"}
        for model_data in class_data.values():
            assert model_data["classwise_ece"] >= 0
            assert sum(row["matches"] for row in model_data["reliability_bands"]) == 80


def test_rejects_nested_or_pit_certified_input_as_wrong_protocol():
    report = make_report()
    report["dataset_type"] = "NESTED_WALK_FORWARD"
    with pytest.raises(ValueError, match="non-PIT retrospective"):
        evaluate_paired_chronological_report(report, resamples=100)


def test_rejects_invalid_ensemble_weight():
    report = make_report()
    report["predictions"][0]["ensemble_elo_weight"] = 1.5
    with pytest.raises(ValueError, match="invalid model probability"):
        evaluate_paired_chronological_report(report, resamples=100)


def test_cli_writes_valid_json_with_one_trailing_newline(tmp_path, monkeypatch):
    report_path = tmp_path / "input.json"
    output_path = tmp_path / "diagnostics.json"
    report_path.write_text(json.dumps(make_report(12)), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "evaluate_paired_chronological.py",
        "--input", str(report_path),
        "--output", str(output_path),
        "--resamples", "100",
        "--block-size", "4",
    ])

    assert evaluate_cli_main() == 0
    output = output_path.read_text(encoding="utf-8")
    assert output.endswith("\\n")
    assert not output.endswith("\\n\\n")
    assert json.loads(output)["fixture_count"] == 12
