from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from app.research.shadow_ledger import validate_shadow_report


def _synthetic_report() -> dict:
    generated = datetime(2026, 11, 22, 8, 0, tzinfo=UTC)
    training_cutoff = generated - timedelta(days=1)
    cutoff = generated - timedelta(minutes=20)
    kickoff = generated + timedelta(hours=2)
    return {
        "generated_at": generated.isoformat(),
        "status": "SHADOW_FORECASTS_READY",
        "research_only": True,
        "research_label": "RESEARCH ONLY",
        "certification": "RETROSPECTIVE_NOT_PIT_CERTIFIED",
        "dataset_sha256": "b" * 64,
        "training_fixture_count": 40,
        "training_cutoff_at": training_cutoff.isoformat(),
        "training_data_sha256": "c" * 64,
        "model": {"version": "hierarchical-poisson-newton-shadow-v2"},
        "forecast_count": 1,
        "abstention_count": 0,
        "predictions": [{
            "canonical_fixture_id": "00000000-0000-0000-0000-000000000001",
            "canonical_competition_id": "00000000-0000-0000-0000-000000000002",
            "home_canonical_team_id": "00000000-0000-0000-0000-000000000003",
            "away_canonical_team_id": "00000000-0000-0000-0000-000000000004",
            "kickoff_at": kickoff.isoformat(),
            "prediction_cutoff_at": cutoff.isoformat(),
            "generated_at": generated.isoformat(),
            "training_cutoff_at": training_cutoff.isoformat(),
            "training_data_sha256": "c" * 64,
            "expected_home_goals": 1.4,
            "expected_away_goals": 1.1,
            "publication_status": "NOT_PUBLISHED",
            "value_betting_status": "LOCKED",
            "markets": {
                "1X2": {"HOME": 0.5, "DRAW": 0.25, "AWAY": 0.25},
                "BTTS": {"YES": 0.6, "NO": 0.4},
                "TOTALS_1_5": {"OVER": 0.7, "UNDER": 0.3},
                "TOTALS_2_5": {"OVER": 0.5, "UNDER": 0.5},
                "TOTALS_3_5": {"OVER": 0.2, "UNDER": 0.8},
            },
        }],
        "abstentions": [],
        "concentration_monitor": {
            "p_home_mean": 0.5, "p_home_min": 0.5, "p_home_max": 0.5,
            "p_home_sd": 0.0, "p_draw_above_050_share": 0.0,
            "any_probability_above_080_share": 0.0, "top_pick_shares": {},
            "quarantined": False, "violations": [],
        },
        "sanitized_summary": {
            "fixtures_considered": 1, "fitted": 1, "shown": 1,
            "expected_goals_sd": 0.0, "extremes": {},
        },
        "provider_calls": 0,
        "database_writes": 0,
        "odds_used": False,
        "production_promotion": "LOCKED",
        "release_eligible": False,
        "value_betting": "LOCKED",
    }


def test_builder_main_writes_report_and_summary_maps_names_and_never_writes_db(
    monkeypatch, tmp_path
):
    backend = Path(__file__).resolve().parents[1]
    scripts = backend / "scripts"
    sys.path.insert(0, str(scripts))
    module_path = scripts / "build_stage7_shadow_predictions.py"
    spec = importlib.util.spec_from_file_location("stage7_builder_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    report = _synthetic_report()
    dataset = {
        "rows": [{"fixture": "target"}],
        "training_only_rows": [],
        "dataset_sha256": "b" * 64,
    }
    monkeypatch.setattr(module, "build_report", lambda *args, **kwargs: dataset)
    monkeypatch.setattr(module, "_dataset_row", lambda row: row)
    monkeypatch.setattr(module, "build_stage7_shadow_predictions", lambda *args, **kwargs: report)
    monkeypatch.setenv(
        "VELTRIX_AI_ANALYST_DATABASE_URL",
        "postgresql://x/y/veltrix_ai_analyst",
    )
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")
    monkeypatch.setattr(sys, "argv", ["builder", "--output", str(tmp_path / "report.json")])

    class FakeConnection:
        info = SimpleNamespace(dbname="veltrix_ai_analyst")

        def __init__(self):
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params):
            self.queries.append(query)
            if "canonical_teams" in query:
                rows = [
                    {"id": "00000000-0000-0000-0000-000000000003", "display_name": "Home FC"},
                    {"id": "00000000-0000-0000-0000-000000000004", "display_name": "Away FC"},
                ]
            else:
                rows = [{
                    "id": "00000000-0000-0000-0000-000000000002",
                    "display_name": "Premier League",
                }]
            return SimpleNamespace(fetchall=lambda: rows)

    fake = FakeConnection()
    monkeypatch.setattr(module.psycopg, "connect", lambda *args, **kwargs: fake)
    assert module.main() == 0

    report_path = tmp_path / "report.json"
    summary_path = tmp_path / "stage7-shadow-sanitized-summary.json"
    assert report_path.is_file() and summary_path.is_file()
    written_report = json.loads(report_path.read_text())
    summary = json.loads(summary_path.read_text())
    prediction = written_report["predictions"][0]
    assert (prediction["home_team"], prediction["away_team"]) == ("Home FC", "Away FC")
    assert prediction["competition"] == "Premier League"
    assert {
        "fixtures_considered", "fitted_fixture_count", "shown_fixture_count",
        "fixture_count", "p_home_mean", "p_home_min", "p_home_max",
        "expected_goals_sd", "p_draw_above_050_share",
        "any_probability_above_080_share", "monitor_status", "extreme_forecasts",
    } <= summary.keys()
    assert summary["sample_forecasts"][0]["competition"] == "Premier League"
    assert fake.queries and all(query.lstrip().startswith("SELECT") for query in fake.queries)
    assert not any(
        query.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for query in fake.queries
    )
    accepted = validate_shadow_report(written_report, code_commit="a" * 40)
    assert accepted["model_version"] == "hierarchical-poisson-newton-shadow-v2"
    assert accepted["forecast_count"] == 1


def test_v2_validator_accepts_zero_forecast_nonready_status():
    report = _synthetic_report()
    report.update({
        "status": "NO_FRESH_UPCOMING_SNAPSHOTS",
        "forecast_count": 0,
        "predictions": [],
        "training_fixture_count": 0,
        "training_cutoff_at": None,
        "training_data_sha256": None,
    })
    accepted = validate_shadow_report(report, code_commit="a" * 40)
    assert accepted["forecast_count"] == 0
