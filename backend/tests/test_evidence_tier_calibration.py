import pytest

from app.validation.evidence_tier_calibration import (
    MarketForecastObservation,
    evaluate_evidence_tier_calibration,
)


def test_calibration_metrics_are_separated_by_evidence_tier():
    rows = (
        MarketForecastObservation("1", "STRONG", "1X2", {"H": 0.7, "D": 0.2, "A": 0.1}, "H"),
        MarketForecastObservation("2", "STRONG", "1X2", {"H": 0.6, "D": 0.2, "A": 0.2}, "H"),
        MarketForecastObservation("3", "MEDIUM", "1X2", {"H": 0.4, "D": 0.3, "A": 0.3}, "D"),
        MarketForecastObservation("4", "LOW", "1X2", {"H": 0.34, "D": 0.33, "A": 0.33}, "A"),
    )
    result = evaluate_evidence_tier_calibration(rows, bins=5)
    assert {item.evidence_tier for item in result} == {"STRONG", "MEDIUM", "LOW"}
    assert all(item.observations > 0 for item in result)
    assert all(0 <= item.expected_calibration_error <= 1 for item in result)
    assert all(item.mean_entropy >= 0 for item in result)


def test_calibration_rejects_duplicate_fixture_market():
    row = MarketForecastObservation("1", "LOW", "BTTS", {"YES": 0.5, "NO": 0.5}, "YES")
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_evidence_tier_calibration((row, row))


def test_calibration_rejects_non_normalized_probabilities():
    with pytest.raises(ValueError, match="sum to one"):
        MarketForecastObservation("1", "MEDIUM", "BTTS", {"YES": 0.6, "NO": 0.6}, "YES")
