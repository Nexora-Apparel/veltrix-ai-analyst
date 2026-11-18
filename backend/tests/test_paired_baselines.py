import pytest

from app.validation.paired_baselines import (
    ProbabilityForecast,
    compare_paired_baselines,
    evaluate_paired_multiclass,
)


def test_paired_comparison_requires_and_scores_identical_fixture_sets():
    rows = (
        ProbabilityForecast("1", "hierarchical", {"H": 0.6, "D": 0.2, "A": 0.2}, "H"),
        ProbabilityForecast("2", "hierarchical", {"H": 0.2, "D": 0.3, "A": 0.5}, "A"),
        ProbabilityForecast("1", "elo", {"H": 0.5, "D": 0.3, "A": 0.2}, "H"),
        ProbabilityForecast("2", "elo", {"H": 0.3, "D": 0.3, "A": 0.4}, "A"),
    )
    result = compare_paired_baselines(rows)
    assert result.fixture_ids == ("1", "2")
    assert {score.model_name for score in result.scores} == {"hierarchical", "elo"}
    assert all(score.fixtures == 2 for score in result.scores)


def test_paired_comparison_rejects_different_fixture_coverage():
    rows = (
        ProbabilityForecast("1", "new", {"H": 0.5, "D": 0.3, "A": 0.2}, "H"),
        ProbabilityForecast("2", "new", {"H": 0.5, "D": 0.3, "A": 0.2}, "A"),
        ProbabilityForecast("1", "baseline", {"H": 0.5, "D": 0.3, "A": 0.2}, "H"),
    )
    with pytest.raises(ValueError, match="identical fixture IDs"):
        compare_paired_baselines(rows)



def test_paired_multiclass_reports_competition_metrics_and_confidence_intervals():
    rows = []
    for index in range(8):
        actual = "H" if index % 2 == 0 else "A"
        competition = "league-a" if index < 4 else "league-b"
        rows.extend(
            (
                ProbabilityForecast(
                    str(index),
                    "hierarchical",
                    {"H": 0.8 if actual == "H" else 0.1, "D": 0.1, "A": 0.1 if actual == "H" else 0.8},
                    actual,
                    competition,
                ),
                ProbabilityForecast(
                    str(index),
                    "baseline",
                    {"H": 0.5, "D": 0.2, "A": 0.3},
                    actual,
                    competition,
                ),
            )
        )
    report = evaluate_paired_multiclass(
        rows,
        model_name="hierarchical",
        baseline_name="baseline",
        bootstrap_replicates=200,
        seed=11,
    )
    assert report["fixtures"] == 8
    assert set(report["per_competition"]) == {"league-a", "league-b"}
    assert report["per_competition"]["league-a"]["fixtures"] == 4
    assert "brier_score_ci_95" in report["paired_delta_model_minus_baseline"]
    assert report["bootstrap"]["release_test"] is False
