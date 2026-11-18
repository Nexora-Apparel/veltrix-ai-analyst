import pytest

from app.validation.paired_baselines import (
    ProbabilityForecast,
    compare_paired_baselines,
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
