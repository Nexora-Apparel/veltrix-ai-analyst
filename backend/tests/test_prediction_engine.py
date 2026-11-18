from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.contracts.prediction import FixturePredictionRequest
from app.models.prediction_engine import ModelArtifactNotPromoted, predict_fixture

CUTOFF = datetime(2026, 11, 18, 12, 0, tzinfo=UTC)


def make_request() -> FixturePredictionRequest:
    return FixturePredictionRequest(
        request_id="req-1",
        canonical_fixture_id=UUID("00000000-0000-0000-0000-000000000001"),
        canonical_competition_id=UUID("00000000-0000-0000-0000-000000000002"),
        home_team_id=UUID("00000000-0000-0000-0000-000000000010"),
        away_team_id=UUID("00000000-0000-0000-0000-000000000011"),
        kickoff_at=CUTOFF + timedelta(hours=4),
        prediction_cutoff_at=CUTOFF,
        feature_snapshot_id="snapshot-1",
        feature_snapshot_sha256="a" * 64,
        feature_schema_version="1.0.0",
        requested_markets=("1X2", "BTTS", "TOTALS_1_5", "TOTALS_2_5", "TOTALS_3_5"),
        data_quality_tier="STRONG",
    )


def make_artifact(**changes: object) -> dict[str, object]:
    artifact: dict[str, object] = {
        "deployment_status": "PRODUCTION_APPROVED",
        "point_in_time_certified": True,
        "model_id": "veltrix-v1",
        "model_version": "1.0.0",
        "code_commit": "a" * 40,
        "training_dataset_manifest_id": "manifest-1",
        "training_cutoff_at": (CUTOFF - timedelta(days=1)).isoformat(),
        "primary_model": {
            "attack": {"home": 0.0, "away": 0.0},
            "defence": {"home": 0.0, "away": 0.0},
            "intercept": 0.25,
            "home_advantage_log_rate": 0.12,
            "half_life_days": 180.0,
            "ridge": 0.08,
            "training_fixtures": 500,
        },
        "dixon_coles": {"rho": -0.03},
    }
    artifact.update(changes)
    return artifact


def test_v1_inference_returns_all_required_markets_from_one_distribution() -> None:
    result = predict_fixture(
        make_artifact(),
        make_request(),
        home_model_team_id="home",
        away_model_team_id="away",
        team_identity_verified=True,
        generated_at=CUTOFF,
    )
    markets = result.market_probabilities

    assert set(markets) == {
        "1X2", "BTTS", "TOTALS_1_5", "TOTALS_2_5", "TOTALS_3_5"
    }
    assert set(markets["1X2"]) == {"HOME", "DRAW", "AWAY"}
    assert set(markets["BTTS"]) == {"YES", "NO"}
    for line in ("TOTALS_1_5", "TOTALS_2_5", "TOTALS_3_5"):
        assert set(markets[line]) == {"OVER", "UNDER"}
    assert result.publication_status == "NOT_PUBLISHED"
    assert result.expected_home_goals > 0
    assert result.expected_away_goals > 0


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"deployment_status": "RESEARCH_ARTIFACT_ONLY"}, "MODEL_NOT_PRODUCTION_APPROVED"),
        ({"point_in_time_certified": False}, "MODEL_TRAINING_DATA_NOT_PIT_CERTIFIED"),
    ],
)
def test_research_or_non_pit_artifacts_cannot_predict(
    changes: dict[str, object], reason: str
) -> None:
    with pytest.raises(ModelArtifactNotPromoted, match=reason):
        predict_fixture(
            make_artifact(**changes),
            make_request(),
            home_model_team_id="home",
            away_model_team_id="away",
            team_identity_verified=True,
        )


def test_training_cutoff_must_precede_prediction_cutoff() -> None:
    artifact = make_artifact(training_cutoff_at=CUTOFF.isoformat())
    with pytest.raises(
        ModelArtifactNotPromoted, match="MODEL_TRAINING_CUTOFF_NOT_BEFORE_PREDICTION"
    ):
        predict_fixture(
            artifact,
            make_request(),
            home_model_team_id="home",
            away_model_team_id="away",
            team_identity_verified=True,
        )


def test_missing_model_provenance_fails_closed() -> None:
    artifact = make_artifact()
    artifact.pop("code_commit")
    with pytest.raises(ModelArtifactNotPromoted, match="CODE_COMMIT_MISSING"):
        predict_fixture(
            artifact,
            make_request(),
            home_model_team_id="home",
            away_model_team_id="away",
            team_identity_verified=True,
        )



def test_inference_expands_score_grid_for_high_goal_rates() -> None:
    artifact = make_artifact()
    primary = artifact["primary_model"]
    assert isinstance(primary, dict)
    primary["intercept"] = 3.7
    result = predict_fixture(
        artifact,
        make_request(),
        home_model_team_id="home",
        away_model_team_id="away",
        team_identity_verified=True,
        generated_at=CUTOFF,
    )
    assert result.uncertainty["scoreline_probability_mass_before_renormalization"] > 0.99999
