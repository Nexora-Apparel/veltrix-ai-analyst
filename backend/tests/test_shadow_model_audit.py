from datetime import UTC, datetime, timedelta
import pytest

from app.models.hierarchical_poisson import fit_hierarchical_poisson, HierarchicalGoalResult
from app.research.shadow_model_audit import (
    reproduce_shadow_fit,
    training_data_sha256,
    training_pool_sha256,
)


def _artifacts():
    base = datetime(2026, 1, 1, tzinfo=UTC)
    rows = []
    teams = [f"team-{index}" for index in range(8)]
    for index in range(40):
        kickoff = base + timedelta(days=index + 1)
        observed = kickoff + timedelta(hours=3)
        home = index % len(teams)
        away = (home + 1 + index % 3) % len(teams)
        home_goals = (index * 3 + 1) % 4
        away_goals = (index * 2 + 2) % 3
        rows.append({
            "fixture_id": f"league:fixture-{index:03d}",
            "competition_id": "league",
            "home_team_id": teams[home],
            "away_team_id": teams[away],
            "kickoff_at": kickoff.isoformat(),
            "label": {"home_goals": home_goals, "away_goals": away_goals},
            "label_observed_at": observed.isoformat(),
            "label_observation_id": index + 1,
            "label_lineage": {
                "availability_basis": "IMPORT_RUN_COMPLETED_AT_TRAINING_ONLY",
                "point_in_time_certifiable": False,
            },
            "validation_eligible": False,
        })
    pool_hash = training_pool_sha256(rows)
    training_hash = training_data_sha256(rows)
    cutoff = max(datetime.fromisoformat(row["label_observed_at"]) for row in rows)
    results = [
        HierarchicalGoalResult(
            fixture_id=row["fixture_id"],
            kickoff_at=datetime.fromisoformat(row["kickoff_at"]),
            competition_id=row["competition_id"],
            home_team_id=row["home_team_id"],
            away_team_id=row["away_team_id"],
            home_goals=row["label"]["home_goals"],
            away_goals=row["label"]["away_goals"],
        )
        for row in rows
    ]
    model = fit_hierarchical_poisson(
        results,
        as_of=cutoff,
        half_life_days=365.0,
        team_ridge=0.5,
        competition_ridge=0.5,
    )
    target = {
        "canonical_fixture_id": "future-fixture",
        "competition_id": "league",
        "home_team_id": teams[0],
        "away_team_id": teams[3],
    }
    rates = model.predict(
        target["home_team_id"], target["away_team_id"], target["competition_id"]
    )
    dataset = {
        "report_type": "VELTRIX_PROSPECTIVE_EXPANDING_DATASET",
        "dataset_sha256": "d" * 64,
        "training_only_label_rows": len(rows),
        "training_pool_sha256": pool_hash,
        "training_only_rows": rows,
        "rows": [target],
    }
    forecast = {
        "dataset_sha256": "d" * 64,
        "training_data_sha256": training_hash,
        "training_cutoff_at": cutoff.isoformat(),
        "training_fixture_count": len(rows),
        "model": {
            "family": "HIERARCHICAL_POISSON_DIXON_COLES",
            "half_life_days": 365.0,
            "team_ridge": 0.5,
            "competition_ridge": 0.5,
        },
        "predictions": [{
            "canonical_fixture_id": "future-fixture",
            "expected_home_goals": rates.home_lambda,
            "expected_away_goals": rates.away_lambda,
            "markets": {"1X2": {"HOME": 0.46, "DRAW": 0.24, "AWAY": 0.30}},
        }],
    }
    return dataset, forecast


def test_reproduction_verifies_exact_training_and_fit():
    dataset, forecast = _artifacts()
    report = reproduce_shadow_fit(dataset, forecast)

    assert report["status"] == "FIT_REPRODUCTION_VERIFIED"
    assert report["training_fixture_count"] == 40
    assert report["forecast_count"] == 1
    assert report["max_absolute_home_goal_rate_error"] <= 1e-6
    assert report["max_absolute_away_goal_rate_error"] <= 1e-6
    assert report["performance_evaluation_performed"] is False
    assert report["production_promotion"] == "LOCKED"


def test_reproduction_rejects_modified_training_fingerprint():
    dataset, forecast = _artifacts()
    forecast["training_data_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="MODEL_TRAINING_FINGERPRINT_MISMATCH"):
        reproduce_shadow_fit(dataset, forecast)


def test_reproduction_rejects_non_training_only_labels():
    dataset, forecast = _artifacts()
    dataset["training_only_rows"][0]["validation_eligible"] = True

    with pytest.raises(ValueError, match="TRAINING_POOL_FINGERPRINT_MISMATCH"):
        reproduce_shadow_fit(dataset, forecast)
