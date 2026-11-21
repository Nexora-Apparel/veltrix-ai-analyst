from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.validation.independent_1x2_evaluator import (
    BASELINE_CLIMATOLOGY,
    BASELINE_TEAM_AWARE,
    EvaluationRow,
    PreRegistration,
    assess_power,
    evaluate_primary_1x2,
    preregistration_sha256,
    validate_preregistration,
    _date_block_bootstrap,
    _log_loss,
)


def _protocol(**overrides):
    values = {
        "protocol_version": "synthetic-protocol-v1",
        "smallest_worthwhile_improvement": 0.01,
        "alpha": 0.05,
        "target_power": 0.80,
        "planned_distinct_dates": 20,
        "minimum_fixtures": 20,
        "bootstrap_replicates": 500,
        "bootstrap_seed": 20261121,
        "climatology_baseline_version": "synthetic-climatology-v1",
        "team_baseline_version": "synthetic-team-baseline-v1",
        "approval_status": "APPROVED",
        "approval_reference": "TEST_ONLY_NOT_A_REAL_APPROVAL",
        "threshold_sha256": "",
    }
    values.update(overrides)
    protocol = PreRegistration(**values)
    return replace(protocol, threshold_sha256=preregistration_sha256(protocol))


def _power(protocol, daily_value=0.05):
    dates = {
        f"2026-01-{index:02d}": [daily_value, daily_value + 0.001]
        for index in range(1, 31)
    }
    return assess_power(
        {
            BASELINE_CLIMATOLOGY: dates,
            BASELINE_TEAM_AWARE: dates,
        },
        planned_distinct_dates=protocol.planned_distinct_dates,
        smallest_worthwhile_improvement=protocol.smallest_worthwhile_improvement,
        alpha=protocol.alpha,
        target_power=protocol.target_power,
    )


def _rows(count=40):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    rows = []
    outcomes = ("HOME", "DRAW", "AWAY")
    candidate = {
        "HOME": (0.75, 0.15, 0.10),
        "DRAW": (0.15, 0.75, 0.10),
        "AWAY": (0.10, 0.15, 0.75),
    }
    climatology = {
        "HOME": (0.45, 0.30, 0.25),
        "DRAW": (0.25, 0.45, 0.30),
        "AWAY": (0.25, 0.30, 0.45),
    }
    team_baseline = {
        "HOME": (0.50, 0.27, 0.23),
        "DRAW": (0.25, 0.50, 0.25),
        "AWAY": (0.23, 0.27, 0.50),
    }
    for index in range(count):
        kickoff = start + timedelta(days=index // 2, hours=15)
        cutoff = kickoff - timedelta(hours=2)
        outcome = outcomes[index % 3]
        rows.append(EvaluationRow(
            fixture_id=f"synthetic-fixture-{index:04d}",
            kickoff_at=kickoff,
            prediction_cutoff_at=cutoff,
            forecast_generated_at=cutoff - timedelta(minutes=1),
            training_cutoff_at=cutoff - timedelta(days=1),
            label_observed_at=kickoff + timedelta(hours=2),
            outcome=outcome,
            candidate_probabilities=candidate[outcome],
            climatology_probabilities=climatology[outcome],
            team_baseline_probabilities=team_baseline[outcome],
            label_availability_basis="SYSTEM_OBSERVED_AT",
            point_in_time_certifiable=True,
            rights_status="APPROVED",
            rights_valid_from=start - timedelta(days=30),
            rights_valid_until=None,
            rights_permitted_uses=("MODEL_VALIDATION",),
        ))
    return rows


def test_log_loss_uses_probability_of_observed_1x2_outcome():
    assert _log_loss((0.7, 0.2, 0.1), "HOME") == pytest.approx(-__import__("math").log(0.7))
    assert _log_loss((0.1, 0.8, 0.1), "DRAW") == pytest.approx(-__import__("math").log(0.8))
    assert _log_loss((0.1, 0.2, 0.7), "AWAY") == pytest.approx(-__import__("math").log(0.7))


def test_preregistration_hash_and_explicit_approval_are_required():
    protocol = _protocol()
    validate_preregistration(protocol)
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        validate_preregistration(replace(protocol, threshold_sha256="0" * 64))
    draft = _protocol(approval_status="DRAFT", approval_reference="")
    draft = replace(draft, threshold_sha256=preregistration_sha256(draft))
    with pytest.raises(ValueError, match="NOT_EXPLICITLY_APPROVED"):
        validate_preregistration(draft)


def test_mde_increases_with_variance_and_decreases_with_planned_dates():
    low_variance = {
        BASELINE_CLIMATOLOGY: {f"d{i}": [0.04 + i * 0.0001, 0.041 + i * 0.0001] for i in range(20)},
        BASELINE_TEAM_AWARE: {f"d{i}": [0.05 + i * 0.0001, 0.051 + i * 0.0001] for i in range(20)},
    }
    high_variance = {
        BASELINE_CLIMATOLOGY: {f"d{i}": [(-1.0 if i % 2 else 1.0)] for i in range(20)},
        BASELINE_TEAM_AWARE: {f"d{i}": [(-0.8 if i % 2 else 0.8)] for i in range(20)},
    }
    def calc(values, dates):
        return assess_power(
            values,
            planned_distinct_dates=dates,
            smallest_worthwhile_improvement=0.01,
            alpha=0.05,
            target_power=0.80,
        )
    low = calc(low_variance, 20)
    high = calc(high_variance, 20)
    more_dates = calc(low_variance, 80)
    assert high.mde_by_baseline[BASELINE_CLIMATOLOGY] > low.mde_by_baseline[BASELINE_CLIMATOLOGY]
    assert more_dates.mde_by_baseline[BASELINE_CLIMATOLOGY] < low.mde_by_baseline[BASELINE_CLIMATOLOGY]


def test_insufficient_power_fails_closed_before_scoring():
    protocol = _protocol()
    power = assess_power(
        {
            BASELINE_CLIMATOLOGY: {"one-date": [0.01]},
            BASELINE_TEAM_AWARE: {"one-date": [0.01]},
        },
        planned_distinct_dates=protocol.planned_distinct_dates,
        smallest_worthwhile_improvement=protocol.smallest_worthwhile_improvement,
        alpha=protocol.alpha,
        target_power=protocol.target_power,
    )
    report = evaluate_primary_1x2(
        _rows(),
        evaluation_as_of=datetime(2026, 3, 1, tzinfo=UTC),
        protocol=protocol,
        power=power,
    )
    assert report["status"] == "INSUFFICIENT_POWER"
    assert report["scored_fixtures"] == 0
    assert report["secondary_markets"] == "NOT_EVALUATED"


def test_primary_1x2_must_beat_both_baselines_and_defers_secondary_markets():
    protocol = _protocol()
    report = evaluate_primary_1x2(
        _rows(),
        evaluation_as_of=datetime(2026, 3, 1, tzinfo=UTC),
        protocol=protocol,
        power=_power(protocol),
    )
    assert report["status"] == "PRIMARY_1X2_PASS"
    assert report["primary_metric"] == "1X2_LOG_LOSS"
    assert report["scored_fixtures"] == 40
    assert set(report["baselines"]) == {BASELINE_CLIMATOLOGY, BASELINE_TEAM_AWARE}
    assert all(item["beats_baseline"] for item in report["baselines"].values())
    assert report["secondary_markets"] == "NOT_EVALUATED"
    assert report["production_promotion"] == "LOCKED"
    assert report["value_betting"] == "LOCKED"


def test_duplicate_fixture_ids_are_rejected():
    protocol = _protocol()
    rows = _rows()
    rows[1] = replace(rows[1], fixture_id=rows[0].fixture_id)
    with pytest.raises(ValueError, match="DUPLICATE_FIXTURE_IDS"):
        evaluate_primary_1x2(
            rows,
            evaluation_as_of=datetime(2026, 3, 1, tzinfo=UTC),
            protocol=protocol,
            power=_power(protocol),
        )


def test_prediction_or_label_chronology_violation_is_rejected():
    protocol = _protocol()
    rows = _rows()
    rows[0] = replace(
        rows[0],
        forecast_generated_at=rows[0].kickoff_at + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="CHRONOLOGY_INVALID"):
        evaluate_primary_1x2(
            rows,
            evaluation_as_of=datetime(2026, 3, 1, tzinfo=UTC),
            protocol=protocol,
            power=_power(protocol),
        )


def test_non_point_in_time_or_rights_invalid_label_is_rejected():
    protocol = _protocol()
    rows = _rows()
    rows[0] = replace(rows[0], point_in_time_certifiable=False)
    with pytest.raises(ValueError, match="NOT_POINT_IN_TIME_CERTIFIABLE"):
        evaluate_primary_1x2(
            rows,
            evaluation_as_of=datetime(2026, 3, 1, tzinfo=UTC),
            protocol=protocol,
            power=_power(protocol),
        )


def test_date_block_bootstrap_resamples_whole_date_clusters():
    lower, upper = _date_block_bootstrap(
        {"date-a": [0.0, 0.0, 0.0, 0.0], "date-b": [1.0]},
        replicates=500,
        seed=17,
        alpha=0.05,
    )
    assert lower in {0.0, 0.2, 1.0}
    assert upper in {0.0, 0.2, 1.0}
