from app.validation.binary_market_metrics import (
    BinaryForecast,
    binary_metrics,
    evaluate_paired_binary_market,
)


def rows(probabilities):
    return [
        BinaryForecast(
            fixture_id=f"f-{index}",
            competition_id="league-a" if index < 4 else "league-b",
            actual=index % 2 == 0,
            probability=probability,
        )
        for index, probability in enumerate(probabilities)
    ]


def test_binary_metrics_calculate_brier_and_log_loss():
    result = binary_metrics(rows([0.8, 0.2, 0.7, 0.3, 0.6, 0.4]))
    assert result.fixtures == 6
    assert result.brier_score >= 0
    assert result.log_loss >= 0


def test_paired_evaluation_reports_market_and_competition_metrics():
    model = rows([0.9, 0.1, 0.8, 0.2, 0.9, 0.1])
    baseline = rows([0.6, 0.4, 0.6, 0.4, 0.6, 0.4])
    report = evaluate_paired_binary_market(
        model, baseline, bootstrap_replicates=200, seed=7
    )
    assert report["fixtures"] == 6
    assert set(report["per_competition"]) == {"league-a", "league-b"}
    assert "brier_score_ci_95" in report["paired_delta_model_minus_baseline"]
    assert report["bootstrap"]["release_test"] is False


def test_paired_evaluation_rejects_mismatched_fixture_sets():
    model = rows([0.5, 0.5])
    baseline = rows([0.5])
    try:
        evaluate_paired_binary_market(model, baseline, bootstrap_replicates=200)
    except ValueError as exc:
        assert "identical" in str(exc)
    else:
        raise AssertionError("mismatched fixture sets must fail closed")


def test_probability_bounds_are_enforced():
    try:
        BinaryForecast("f", "league", True, 1.1)
    except ValueError as exc:
        assert "[0, 1]" in str(exc)
    else:
        raise AssertionError("out-of-range probabilities must fail")
