from app.research.shrinkage_repair_metrics import (
    blend_probabilities,
    evaluation_diagnostics,
    paired_date_block_bootstrap,
)


def test_blend_probabilities_preserves_simplex_and_endpoints():
    model = {"HOME": 0.6, "DRAW": 0.2, "AWAY": 0.2}
    climate = {"HOME": 0.4, "DRAW": 0.3, "AWAY": 0.3}
    assert blend_probabilities(model, climate, 1.0) == model
    blended = blend_probabilities(model, climate, 0.5)
    assert sum(blended.values()) == 1.0
    assert blended == {"HOME": 0.5, "DRAW": 0.25, "AWAY": 0.25}


def test_calibration_and_extreme_probability_report_include_empty_bins():
    rows = [
        {"competition_id": "L", "label": {"home_goals": 2, "away_goals": 0},
         "probabilities": {"HOME": 0.85, "DRAW": 0.10, "AWAY": 0.05}},
        {"competition_id": "L", "label": {"home_goals": 0, "away_goals": 1},
         "probabilities": {"HOME": 0.10, "DRAW": 0.15, "AWAY": 0.75}},
        {"competition_id": "M", "label": {"home_goals": 1, "away_goals": 1},
         "probabilities": {"HOME": 0.20, "DRAW": 0.70, "AWAY": 0.10}},
    ]
    report = evaluation_diagnostics(rows)
    assert report["n"] == 3
    assert len(report["reliability"]["HOME"]["reliability_bins"]) == 10
    assert report["extreme_probability"]["forecast_count_any_outcome_above_threshold"] == 1
    assert report["extreme_probability"]["hit_rate"] == 1.0
    assert set(report["competition_breakdown"]) == {"L", "M"}


def test_paired_date_block_bootstrap_is_reproducible():
    differences = [
        ("2026-01-01", 0.1), ("2026-01-01", 0.2),
        ("2026-01-02", -0.1), ("2026-01-03", 0.0),
    ]
    first = paired_date_block_bootstrap(differences, seed=7)
    second = paired_date_block_bootstrap(differences, seed=7)
    assert first == second
    assert first["date_blocks"] == 3
