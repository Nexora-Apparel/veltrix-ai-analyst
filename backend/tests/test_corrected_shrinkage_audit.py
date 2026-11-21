import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.models.hierarchical_poisson import fit_hierarchical_poisson
from app.research import corrected_shrinkage_audit as audit
from app.research.corrected_shrinkage_audit import (
    ARCHIVED_CONFIG,
    FOLD_RULE,
    HOME_ADVANTAGE_TREATMENT,
    REFERENCE_K,
)


def test_preregistered_design_is_frozen():
    assert REFERENCE_K == (0.5, 2.0)
    assert ARCHIVED_CONFIG == {"team_ridge": 0.5, "competition_ridge": 0.5, "half_life_days": 365.0}
    assert "60%" in FOLD_RULE and "90%" in FOLD_RULE
    assert HOME_ADVANTAGE_TREATMENT == "unpenalized in archived and both reference fits"
    assert audit.MAX_ITERATIONS == 4000
    assert audit.OPTIMIZER_TOLERANCE == 1e-7


def test_audit_module_has_no_database_or_provider_imports():
    path = Path(__file__).parents[1] / "app" / "research" / "corrected_shrinkage_audit.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = ("psycopg", "sqlalchemy", "httpx", "requests", "app.db", "app.providers")
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(any(token in name for token in forbidden) for name in imports)



def _known_league_rows() -> list[dict]:
    strengths = {"strong": 1.1, "upper": 0.45, "lower": -0.45, "weak": -1.1}
    teams = list(strengths)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    index = 0
    for round_no in range(24):
        for home_index in range(len(teams)):
            for away_index in range(len(teams)):
                if home_index == away_index:
                    continue
                home, away = teams[home_index], teams[away_index]
                home_signal = strengths[home] - strengths[away] + 0.35
                away_signal = strengths[away] - strengths[home]
                hg = max(0, round(1.45 + 0.62 * home_signal + ((round_no + home_index) % 3 - 1) * 0.25))
                ag = max(0, round(1.05 + 0.58 * away_signal + ((round_no + away_index) % 3 - 1) * 0.25))
                kickoff = start + timedelta(days=index)
                rows.append({
                    "fixture_id": f"known-{index}",
                    "kickoff_at": kickoff.isoformat(),
                    "competition_id": "league",
                    "home_team_id": home,
                    "away_team_id": away,
                    "label": {"home_goals": hg, "away_goals": ag},
                })
                index += 1
    return rows


def _summed_objective_gradient_norm(rows, cutoff, model, tau_team, tau_competition):
    weights = audit._weights(rows, cutoff)
    team_gradient = {team: 0.0 for team in model.attack}
    defence_gradient = {team: 0.0 for team in model.defence}
    competition_gradient = {competition: 0.0 for competition in model.competition_effects}
    global_gradient = 0.0
    home_gradient = 0.0
    for row, weight in zip(rows, weights):
        rates = model.predict(row["home_team_id"], row["away_team_id"], row["competition_id"])
        residual_home = rates.home_lambda - row["label"]["home_goals"]
        residual_away = rates.away_lambda - row["label"]["away_goals"]
        global_gradient += weight * (residual_home + residual_away)
        home_gradient += weight * residual_home
        competition_gradient[row["competition_id"]] += weight * (
            residual_home + residual_away
        )
        team_gradient[row["home_team_id"]] += weight * residual_home
        team_gradient[row["away_team_id"]] += weight * residual_away
        defence_gradient[row["away_team_id"]] -= weight * residual_home
        defence_gradient[row["home_team_id"]] -= weight * residual_away
    for team in team_gradient:
        team_gradient[team] += tau_team * model.attack[team]
        defence_gradient[team] += tau_team * model.defence[team]
    for competition in competition_gradient:
        competition_gradient[competition] += (
            tau_competition * model.competition_effects[competition]
        )
    return (
        global_gradient**2
        + home_gradient**2
        + sum(value**2 for value in competition_gradient.values())
        + sum(value**2 for value in team_gradient.values())
        + sum(value**2 for value in defence_gradient.values())
    ) ** 0.5


def test_fold_prior_conversion_matches_summed_objective_stationarity_scale():
    rows = _known_league_rows()[:36]
    cutoff = datetime.fromisoformat(rows[-1]["kickoff_at"])
    total_weight, mu = audit._fold_weight_and_mean_goals(rows, cutoff)
    k = 0.5
    team_ridge, competition_ridge = audit._ridge_for_unnormalized_prior(
        k, mu, total_weight
    )
    converted = fit_hierarchical_poisson(
        [audit._result(row) for row in rows],
        as_of=cutoff,
        half_life_days=365,
        team_ridge=team_ridge,
        competition_ridge=competition_ridge,
    )
    assert converted.optimizer_converged
    tau_team = k * mu
    tau_competition = k * 2 * mu
    assert total_weight * converted.team_ridge == pytest.approx(
        tau_team, rel=1e-12
    )
    assert total_weight * converted.competition_ridge == pytest.approx(
        tau_competition, rel=1e-12
    )
    stationarity_limit = total_weight * 1e-7 * 1.01 + 1e-8
    converted_gradient = _summed_objective_gradient_norm(
        rows, cutoff, converted, tau_team, tau_competition
    )
    assert converted_gradient <= stationarity_limit

    # Negative control: reproduce the original units bug by passing summed
    # tau values directly to an API that averages the likelihood by W.
    unconverted = fit_hierarchical_poisson(
        [audit._result(row) for row in rows],
        as_of=cutoff,
        half_life_days=365,
        team_ridge=k * mu,
        competition_ridge=k * 2 * mu,
    )
    unconverted_gradient = _summed_objective_gradient_norm(
        rows, cutoff, unconverted, tau_team, tau_competition
    )
    assert unconverted_gradient > stationarity_limit


def test_synthetic_overpenalization_suppresses_signal_and_scaled_prior_recovers_ranking():
    rows = _known_league_rows()[:96]
    cutoff = datetime.fromisoformat(rows[-1]["kickoff_at"])
    total_weight, mu = audit._fold_weight_and_mean_goals(rows, cutoff)
    scaled_team, scaled_comp = audit._ridge_for_unnormalized_prior(2.0, mu, total_weight)
    results = [audit._result(row) for row in rows]
    overfit = fit_hierarchical_poisson(
        results, as_of=cutoff, half_life_days=365,
        team_ridge=0.5, competition_ridge=0.5,
    )
    recovered = fit_hierarchical_poisson(
        results, as_of=cutoff, half_life_days=365,
        team_ridge=scaled_team, competition_ridge=scaled_comp,
    )
    true_order = ["strong", "upper", "lower", "weak"]
    recovered_order = sorted(recovered.attack, key=recovered.attack.get, reverse=True)
    over_spread = max(overfit.attack.values()) - min(overfit.attack.values())
    recovered_spread = max(recovered.attack.values()) - min(recovered.attack.values())
    assert over_spread < recovered_spread
    assert recovered_order == true_order
    assert recovered_spread > 0.25


def test_nonconverging_fit_is_reported_and_not_dropped(monkeypatch):
    rows = _known_league_rows()[:12]
    cutoff = datetime.fromisoformat(rows[-1]["kickoff_at"])

    def fail_fit(*args, **kwargs):
        raise ArithmeticError("optimizer did not converge after 1 iterations")

    monkeypatch.setattr(audit, "fit_hierarchical_poisson", fail_fit)
    result = audit._fit_for_audit(rows, cutoff, k=0.5)
    assert result["converged"] is False
    assert result["model"] is None
    assert "did not converge" in result["error"]
    assert result["total_recency_weight"] > 0
    assert result["weighted_mean_goals_per_team_match"] > 0
