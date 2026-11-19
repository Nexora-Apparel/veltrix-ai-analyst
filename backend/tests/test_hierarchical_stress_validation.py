from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.hierarchical_poisson import (
    HierarchicalGoalResult,
    fit_hierarchical_poisson,
)
from app.validation.hierarchical_tuning import (
    ChronologicalFold,
    select_hierarchical_hyperparameters,
)


def _multi_competition_history(count_per_competition: tuple[int, ...]):
    start = datetime(2025, 1, 1, tzinfo=UTC)
    rows = []
    fixture_no = 0
    for comp_no, fixture_count in enumerate(count_per_competition):
        competition = f"comp-{comp_no}"
        teams = [f"{competition}-team-{i}" for i in range(10)]
        for match_no in range(fixture_count):
            home = teams[match_no % len(teams)]
            away = teams[(match_no * 3 + 1) % len(teams)]
            if home == away:
                away = teams[(match_no * 3 + 2) % len(teams)]
            # Deterministic heterogeneity: both competition scoring levels and
            # team strength vary; no random seed or hardcoded forecast labels.
            home_goals = (match_no * 7 + comp_no * 3 + match_no // 11) % 5
            away_goals = (match_no * 5 + comp_no + match_no // 17) % 4
            rows.append(HierarchicalGoalResult(
                fixture_id=f"synthetic-{fixture_no}",
                kickoff_at=start + timedelta(days=match_no + comp_no * 2),
                competition_id=competition,
                home_team_id=home,
                away_team_id=away,
                home_goals=home_goals,
                away_goals=away_goals,
            ))
            fixture_no += 1
    return rows


def test_optimizer_converges_on_imbalanced_multi_competition_history():
    rows = _multi_competition_history((180, 90, 45, 24, 12))
    model = fit_hierarchical_poisson(
        rows,
        half_life_days=365.0,
        team_ridge=1.5,
        competition_ridge=2.5,
        learning_rate=0.35,
        max_iterations=12000,
        tolerance=2e-6,
    )
    assert model.optimizer_converged
    assert model.training_fixtures == sum((180, 90, 45, 24, 12))
    assert len(model.competition_effects) == 5
    assert model.optimizer_gradient_norm <= 2e-6
    for competition in model.competition_effects:
        rates = model.predict(
            f"{competition}-unseen-home",
            f"{competition}-unseen-away",
            competition,
        )
        assert rates.home_lambda > 0
        assert rates.away_lambda > 0


def test_chronological_selection_scores_multiple_development_folds():
    rows = _multi_competition_history((160, 110, 60))
    origin = datetime(2025, 1, 1, tzinfo=UTC)
    folds = (
        ChronologicalFold(origin + timedelta(days=45), origin + timedelta(days=75)),
        ChronologicalFold(origin + timedelta(days=76), origin + timedelta(days=105)),
        ChronologicalFold(origin + timedelta(days=106), origin + timedelta(days=145)),
    )
    availability = {
        row.fixture_id: row.kickoff_at + timedelta(hours=1)
        for row in rows
    }
    selection = select_hierarchical_hyperparameters(
        rows,
        folds,
        label_available_at=availability,
        evaluation_as_of=origin + timedelta(days=200),
        half_lives=(180.0, 365.0),
        team_ridges=(0.5, 2.0),
        competition_ridges=(1.0, 4.0),
        min_training_fixtures=40,
    )
    assert selection.leaderboard
    assert selection.leaderboard[0].folds_scored == 3
    assert selection.leaderboard[0].scored_matches > 0
    assert all(item.mean_validation_nll > 0 for item in selection.leaderboard)



def test_tuning_excludes_labels_not_available_at_the_fold_cutoff():
    rows = _multi_competition_history((60,))
    origin = datetime(2025, 1, 1, tzinfo=UTC)
    cutoff = origin + timedelta(days=45)
    folds = (ChronologicalFold(cutoff, origin + timedelta(days=60)),)
    availability = {
        row.fixture_id: (
            origin + timedelta(days=50)
            if row.kickoff_at <= origin + timedelta(days=20)
            else row.kickoff_at + timedelta(hours=2)
        )
        for row in rows
    }

    # Forty-six matches have kicked off by the cutoff, but twenty-one results
    # were not imported/observed until day 50. Only 25 labels are trainable.
    import pytest

    with pytest.raises(ValueError, match="no chronological fold"):
        select_hierarchical_hyperparameters(
            rows,
            folds,
            half_lives=(180.0,),
            team_ridges=(0.5,),
            competition_ridges=(1.0,),
            min_training_fixtures=30,
            label_available_at=availability,
            evaluation_as_of=origin + timedelta(days=70),
        )


def test_tuning_accepts_labels_only_after_their_recorded_availability_time():
    rows = _multi_competition_history((60,))
    origin = datetime(2025, 1, 1, tzinfo=UTC)
    cutoff = origin + timedelta(days=50)
    folds = (ChronologicalFold(cutoff, origin + timedelta(days=60)),)
    availability = {
        row.fixture_id: (
            origin + timedelta(days=50)
            if row.kickoff_at <= origin + timedelta(days=20)
            else row.kickoff_at + timedelta(hours=2)
        )
        for row in rows
    }

    selection = select_hierarchical_hyperparameters(
        rows,
        folds,
        half_lives=(180.0,),
        team_ridges=(0.5,),
        competition_ridges=(1.0,),
        min_training_fixtures=30,
        label_available_at=availability,
        evaluation_as_of=origin + timedelta(days=70),
    )

    assert selection.protocol == (
        "EXPANDING_WINDOW_LABEL_AVAILABILITY_AWARE_PAIRED_POISSON_NLL_V2"
    )
    assert selection.leaderboard[0].scored_matches == 9
    assert selection.leaderboard[0].folds_scored == 1



def test_availability_aware_tuning_requires_an_evaluation_timestamp():
    rows = _multi_competition_history((60,))
    folds = (ChronologicalFold(
        datetime(2025, 2, 15, tzinfo=UTC),
        datetime(2025, 3, 2, tzinfo=UTC),
    ),)
    availability = {
        row.fixture_id: row.kickoff_at + timedelta(hours=1)
        for row in rows
    }

    import pytest

    with pytest.raises(ValueError, match="requires evaluation_as_of"):
        select_hierarchical_hyperparameters(
            rows,
            folds,
            half_lives=(180.0,),
            team_ridges=(0.5,),
            competition_ridges=(1.0,),
            label_available_at=availability,
        )
