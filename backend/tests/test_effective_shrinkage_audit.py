from test_shadow_model_audit import _artifacts

from app.research.effective_shrinkage_audit import effective_shrinkage_report


def test_effective_shrinkage_reports_each_team_and_runtime_values():
    dataset, forecast = _artifacts()

    report = effective_shrinkage_report(dataset, forecast)

    assert report["status"] == "EFFECTIVE_SHRINKAGE_AUDIT_COMPLETE"
    assert report["training_fixture_count"] == 40
    assert report["team_count"] == 8
    assert report["effective_runtime"]["team_ridge"] == 0.5
    assert report["effective_runtime"]["competition_ridge"] == 0.5
    assert report["effective_runtime"]["half_life_days"] == 365.0
    assert report["effective_runtime"]["near_unpenalized_reference_ridge"] == 1e-9
    assert len(report["teams"]) == 8
    assert all("attack_effect_ratio" in row for row in report["teams"])
    assert all("defence_effect_ratio" in row for row in report["teams"])
    assert all(row["attack_tau_to_data_information"] > 0 for row in report["teams"])
    assert all(row["defence_tau_to_data_information"] > 0 for row in report["teams"])
    assert report["production_promotion"] == "LOCKED"
    assert report["value_betting"] == "LOCKED"
