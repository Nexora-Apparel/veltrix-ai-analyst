import pytest

from app.models.regularization_contract import regularization_scales


def test_team_attack_and_defence_share_one_competition_scaled_prior():
    scales = regularization_scales(
        league_mean_goals=1.35,
        pooled_mean_goals=1.40,
        k_team=4.0,
        k_competition=3.0,
        k_home_competition=5.0,
        k_home_global=8.0,
    )

    assert scales.team_attack_tau == pytest.approx(5.4)
    assert scales.team_defence_tau == pytest.approx(5.4)


def test_competition_effect_uses_two_goal_observation_information_scale():
    scales = regularization_scales(
        league_mean_goals=1.35,
        pooled_mean_goals=1.40,
        k_team=4.0,
        k_competition=3.0,
        k_home_competition=5.0,
        k_home_global=8.0,
    )

    assert scales.competition_tau == pytest.approx(3.0 * 2.0 * 1.35)
    assert scales.competition_tau == pytest.approx(2.0 * 3.0 * 1.35)


def test_home_advantage_has_competition_and_global_priors():
    scales = regularization_scales(
        league_mean_goals=1.35,
        pooled_mean_goals=1.40,
        k_team=4.0,
        k_competition=3.0,
        k_home_competition=5.0,
        k_home_global=8.0,
    )

    assert scales.competition_home_tau == pytest.approx(6.75)
    assert scales.global_home_tau == pytest.approx(11.2)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"league_mean_goals": 0.0, "pooled_mean_goals": 1.4},
        {"league_mean_goals": 1.3, "pooled_mean_goals": -1.0},
        {"league_mean_goals": float("nan"), "pooled_mean_goals": 1.4},
    ],
)
def test_invalid_goal_rate_inputs_fail_closed(kwargs):
    defaults = {
        "league_mean_goals": 1.3,
        "pooled_mean_goals": 1.4,
        "k_team": 4.0,
        "k_competition": 3.0,
        "k_home_competition": 5.0,
        "k_home_global": 8.0,
    }
    defaults.update(kwargs)

    with pytest.raises(ValueError):
        regularization_scales(**defaults)
