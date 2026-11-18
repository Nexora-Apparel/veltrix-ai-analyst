from __future__ import annotations

import pytest

from app.validation.binary_markets import evaluate_binary_markets


def market_row(btts: float, o15: float, o25: float, o35: float):
    return {
        "BTTS": {"YES": btts, "NO": 1.0 - btts},
        "TOTALS_1_5": {"OVER": o15, "UNDER": 1.0 - o15},
        "TOTALS_2_5": {"OVER": o25, "UNDER": 1.0 - o25},
        "TOTALS_3_5": {"OVER": o35, "UNDER": 1.0 - o35},
    }


def test_scores_all_binary_v1_markets_independently() -> None:
    rows = [
        (market_row(0.9, 0.9, 0.8, 0.6), 2, 1),
        (market_row(0.1, 0.1, 0.2, 0.1), 0, 0),
        (market_row(0.8, 0.8, 0.7, 0.2), 1, 1),
        (market_row(0.2, 0.2, 0.1, 0.1), 1, 0),
    ]
    result = evaluate_binary_markets(rows, bins=5)

    assert set(result) == {"BTTS", "TOTALS_1_5", "TOTALS_2_5", "TOTALS_3_5"}
    assert all(metric.samples == 4 for metric in result.values())
    assert all(0 <= metric.brier_score <= 1 for metric in result.values())
    assert all(metric.log_loss >= 0 for metric in result.values())
    assert all(0 <= metric.accuracy_at_half <= 1 for metric in result.values())
    assert all(0 <= metric.expected_calibration_error <= 1 for metric in result.values())
    assert result["TOTALS_1_5"].brier_score <= result["TOTALS_3_5"].brier_score


def test_binary_market_scoring_rejects_missing_or_invalid_probabilities() -> None:
    with pytest.raises(ValueError, match="missing probability"):
        evaluate_binary_markets([({}, 1, 0)])
    bad = market_row(1.2, 0.5, 0.5, 0.5)
    with pytest.raises(ValueError, match="invalid probability"):
        evaluate_binary_markets([(bad, 1, 0)])


def test_binary_market_scoring_requires_settled_rows() -> None:
    with pytest.raises(ValueError, match="at least one"):
        evaluate_binary_markets([])
