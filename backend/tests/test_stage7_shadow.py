import hashlib
import json
from pathlib import Path

from app.research.stage7_shadow import (
    MODEL_VERSION,
    _summary,
    concentration_violations,
    insufficient_team_history,
)


def _prediction(home, draw, away, btts_yes=0.5, over25=0.5):
    return {
        "markets": {
            "1X2": {"HOME": home, "DRAW": draw, "AWAY": away},
            "BTTS": {"YES": btts_yes, "NO": 1 - btts_yes},
            "TOTALS_1_5": {"OVER": 0.5, "UNDER": 0.5},
            "TOTALS_2_5": {"OVER": over25, "UNDER": 1 - over25},
            "TOTALS_3_5": {"OVER": 0.5, "UNDER": 0.5},
        }
    }


def test_abstention_requires_five_matches_for_both_teams():
    assert insufficient_team_history(4, 20)
    assert insufficient_team_history(20, 4)
    assert not insufficient_team_history(5, 5)


def test_selected_version_is_frozen():
    assert MODEL_VERSION == "hierarchical-poisson-newton-shadow-v2"


def test_concentration_monitor_does_not_gate_slates_below_15():
    predictions = [_prediction(0.6, 0.2, 0.2) for _ in range(14)]
    assert concentration_violations(_summary(predictions)) == []


def test_concentration_monitor_quarantines_low_home_probability_dispersion():
    predictions = [
        _prediction(0.5 + i * 0.0001, 0.3, 0.2 - i * 0.0001)
        for i in range(15)
    ]
    assert "P_HOME_SD_OUTSIDE_0_08_0_22" in concentration_violations(_summary(predictions))


def test_concentration_monitor_quarantines_single_outcome_dominance():
    predictions = [_prediction(0.7, 0.2, 0.1) for _ in range(15)]
    assert "SINGLE_1X2_OUTCOME_TOP_PICK_OVER_85_PERCENT" in concentration_violations(
        _summary(predictions)
    )


def test_concentration_monitor_quarantines_btts_and_over_pick_concentration():
    predictions = [
        _prediction(0.4, 0.3, 0.3, btts_yes=0.95, over25=0.95)
        for _ in range(15)
    ]
    violations = concentration_violations(_summary(predictions))
    assert "BTTS_YES_PICK_SHARE_OVER_90_PERCENT" in violations
    assert "OVER_2_5_PICK_SHARE_OVER_90_PERCENT" in violations


def test_committed_selected_configuration_matches_model_and_evaluation():
    root = Path(__file__).resolve().parents[2]
    config = json.loads(
        (root / "docs/research/hierarchical-poisson-shadow-v2.json").read_text()
    )
    assert config["model_version"] == MODEL_VERSION
    assert config["selection"] == {
        "k": 4.0,
        "half_life_days": 730.0,
        "blend_weight": 1.0,
        "solver": "damped_newton_analytic_hessian_backtracking_line_search",
    }
    assert config["evaluation"]["workflow_run_id"] == 44929166889
    assert config["evaluation"]["artifact_id"] == 14717051631
    canonical = json.dumps(
        config, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ) + "\n"
    assert hashlib.sha256(canonical.encode()).hexdigest() == (
        "87063b2ddec253c65ce4071ce9e508d396c2ee5bb11b8dd85513dc97260d0698"
    )


def test_unadmitted_model_version_stays_quarantined(monkeypatch, tmp_path):
    from app.routes import research_predictions

    admission = {
        "model_version": "some-other-model",
        "tier": "SHADOW",
        "certification": "RETROSPECTIVE_NOT_PIT_CERTIFIED",
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
        "app_display_enabled": False,
        "config_sha256": "a" * 64,
        "training_data_sha256": "b" * 64,
        "report_sha256": "c" * 64,
    }
    path = tmp_path / "admission.json"
    path.write_text(json.dumps(admission))
    monkeypatch.setattr(research_predictions, "_ADMISSION_PATH", path)
    monkeypatch.setenv("VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED", "true")
    response = research_predictions.list_research_predictions()
    assert response["status"] == "MODEL_QUARANTINED"
    assert response["predictions"] == []



def test_committed_admission_is_shadow_only_and_app_display_is_off():
    root = Path(__file__).resolve().parents[2]
    admission = json.loads(
        (root / "backend/app/research/admissions/hierarchical-poisson-newton-shadow-v2.json").read_text()
    )
    assert admission["model_version"] == MODEL_VERSION
    assert admission["tier"] == "SHADOW"
    assert admission["certification"] == "RETROSPECTIVE_NOT_PIT_CERTIFIED"
    assert admission["app_display_enabled"] is False



def test_inference_workflow_is_manual_only_and_old_schedule_remains_disabled():
    root = Path(__file__).resolve().parents[2]
    manual = (root / ".github/workflows/research-shadow-inference.yml").read_text()
    existing = (root / ".github/workflows/prospective-shadow-predictions.yml").read_text()
    assert "workflow_dispatch:" in manual
    assert "schedule:" not in manual
    assert "workflow_run:" not in manual
    assert "confirm_research_ledger_write" in manual
    assert "if: false" in existing

def test_research_query_has_two_placeholders_and_model_version_filter():
    from app.routes import research_predictions

    assert research_predictions._RESEARCH_QUERY.count("%s") == 3
    assert "WHERE model_version = %s" in research_predictions._RESEARCH_QUERY
    assert "latest_run.model_version" in research_predictions._RESEARCH_QUERY


def test_research_route_passes_model_version_then_now(monkeypatch):
    from app.routes import research_predictions

    class FakeConnection:
        def __init__(self):
            self.params = None
            self.query = None
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params):
            self.query, self.params = query, params
            return self

        def fetchall(self):
            return []

        def close(self):
            self.closed = True

    fake = FakeConnection()
    monkeypatch.setenv("VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED", "true")
    monkeypatch.setattr(research_predictions, "_model_admitted", lambda: True)
    monkeypatch.setattr(research_predictions, "_database_connection", lambda: fake)
    response = research_predictions.list_research_predictions()
    assert fake.query.count("%s") == len(fake.params) == 3
    assert fake.params[0] == research_predictions.MODEL_VERSION
    day_start, day_end = fake.params[1:]
    assert day_start.tzinfo is not None
    assert day_end.tzinfo is not None
    assert day_start < day_end
    assert response["status"] == "NO_RESEARCH_FORECASTS_AVAILABLE"
    assert fake.closed
