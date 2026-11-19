from __future__ import annotations

from app.validation.certification_gates import apply_prospective_certification_gates


def complete_market_counts() -> dict:
    return {
        key: {"fixtures": 1000}
        for key in (
            "1X2",
            "BTTS",
            "OVER_UNDER_1_5",
            "OVER_UNDER_2_5",
            "OVER_UNDER_3_5",
        )
    }


def test_upcoming_fixture_dates_cannot_satisfy_settled_date_gate():
    evaluation = {"markets": complete_market_counts(), "fixtures": 1000}
    dataset = {
        "settled_label_rows": 300,
        "distinct_kickoff_dates": 120,
        "settled_distinct_kickoff_dates": 0,
    }

    report = apply_prospective_certification_gates(evaluation, dataset)

    gate = report["certification_gates"][
        "distinct_kickoff_dates_with_settled_labels"
    ]
    assert gate["observed"] == 0
    assert gate["passed"] is False
    assert report["production_promotion"] == "LOCKED"


def test_each_market_must_individually_reach_walk_forward_threshold():
    markets = complete_market_counts()
    markets["OVER_UNDER_3_5"] = {"fixtures": 999}
    report = apply_prospective_certification_gates(
        {"markets": markets},
        {"settled_label_rows": 300, "settled_distinct_kickoff_dates": 90},
    )

    gate = report["certification_gates"]["walk_forward_fixtures_per_market"]
    assert gate["observed"]["OVER_UNDER_3_5"] == 999
    assert gate["passed"] is False


def test_missing_market_metrics_fail_closed():
    report = apply_prospective_certification_gates(
        {"status": "INSUFFICIENT_PROSPECTIVE_DATA"},
        {"settled_label_rows": 0, "settled_distinct_kickoff_dates": 0},
    )

    gate = report["certification_gates"]["walk_forward_fixtures_per_market"]
    assert set(gate["observed"].values()) == {0}
    assert gate["passed"] is False
    assert report["production_certification"] == (
        "BLOCKED_INSUFFICIENT_OR_UNCERTIFIED_EVIDENCE"
    )


def test_bookmaker_and_value_gates_stay_locked_without_odds_evidence():
    report = apply_prospective_certification_gates(
        {"markets": complete_market_counts()},
        {"settled_label_rows": 300, "settled_distinct_kickoff_dates": 90},
    )

    gates = report["certification_gates"]
    assert gates["timestamped_odds_coverage"]["passed"] is False
    assert gates["positive_net_roi_and_positive_lower_95_percent_bound"]["passed"] is False
    assert gates["1x2_beats_bookmaker_brier_and_log_loss"]["passed"] is False
    assert report["value_betting"] == "LOCKED"
    assert report["release_eligible"] is False


def test_boolean_and_invalid_counts_do_not_pass_thresholds():
    report = apply_prospective_certification_gates(
        {"markets": {"1X2": {"fixtures": True}, "BTTS": {"fixtures": "bad"}}},
        {"settled_label_rows": True, "settled_distinct_kickoff_dates": -5},
    )

    assert report["certification_gates"]["walk_forward_fixtures_per_market"]["passed"] is False
    assert report["certification_gates"]["settled_prospective_fixtures"]["observed"] == 0
    assert report["certification_gates"]["distinct_kickoff_dates_with_settled_labels"]["observed"] == 0
