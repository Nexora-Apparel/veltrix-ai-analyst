from app.research.shadow_model_audit import training_data_sha256
from app.research.shrinkage_repair_evaluation import validate_artifact_fingerprints

DATASET_SHA = "a" * 64


def _training_rows():
    return [
        {
            "fixture_id": "fixture-1",
            "competition_id": "league-1",
            "home_team_id": "team-1",
            "away_team_id": "team-2",
            "kickoff_at": "2026-01-01T12:00:00+00:00",
            "label": {"home_goals": 2, "away_goals": 1},
            "label_observed_at": "2026-01-01T15:00:00+00:00",
            "label_observation_id": 1,
            "label_lineage": {"availability_basis": "IMPORT_RUN_COMPLETED_AT_TRAINING_ONLY"},
        },
        {
            "fixture_id": "fixture-2",
            "competition_id": "league-1",
            "home_team_id": "team-3",
            "away_team_id": "team-4",
            "kickoff_at": "2026-01-02T12:00:00+00:00",
            "label": {"home_goals": 0, "away_goals": 0},
            "label_observed_at": "2026-01-02T15:00:00+00:00",
            "label_observation_id": 2,
            "label_lineage": {"availability_basis": "IMPORT_RUN_COMPLETED_AT_TRAINING_ONLY"},
        },
    ]


def _artifacts():
    rows = _training_rows()
    training_sha = training_data_sha256(rows)
    return (
        {
            "dataset_sha256": DATASET_SHA,
            "training_only_rows": rows,
            "training_pool_sha256": "823fb3894d40153217cad1223808d059dd8ecaef548326b39ef19ceb1c01ecae",
        },
        {"dataset_sha256": DATASET_SHA, "training_data_sha256": training_sha},
        training_sha,
    )


def test_matching_model_fingerprints_pass_even_when_pool_hash_differs():
    dataset, forecast, training_sha = _artifacts()
    result = validate_artifact_fingerprints(
        dataset, forecast, expected_dataset_sha=DATASET_SHA, expected_training_sha=training_sha
    )
    assert result["dataset_sha256"] == DATASET_SHA
    assert result["training_data_sha256"] == training_sha
    assert result["forecast_training_data_sha256"] == training_sha
    assert result["training_pool_sha256_observed"] == dataset["training_pool_sha256"]


def test_wrong_recomputed_training_hash_fails_closed():
    import pytest

    dataset, forecast, _ = _artifacts()
    with pytest.raises(ValueError, match="DATASET_TRAINING_DATA_FINGERPRINT_MISMATCH"):
        validate_artifact_fingerprints(
            dataset, forecast, expected_dataset_sha=DATASET_SHA, expected_training_sha="b" * 64
        )


def test_dataset_and_forecast_hashes_remain_fatal():
    import pytest

    dataset, forecast, training_sha = _artifacts()
    dataset["dataset_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="DATASET_CONTENT_FINGERPRINT_MISMATCH"):
        validate_artifact_fingerprints(
            dataset, forecast, expected_dataset_sha=DATASET_SHA, expected_training_sha=training_sha
        )

    dataset, forecast, training_sha = _artifacts()
    forecast["dataset_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="FORECAST_DATASET_FINGERPRINT_MISMATCH"):
        validate_artifact_fingerprints(
            dataset, forecast, expected_dataset_sha=DATASET_SHA, expected_training_sha=training_sha
        )

    dataset, forecast, training_sha = _artifacts()
    forecast["training_data_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="FORECAST_TRAINING_FINGERPRINT_MISMATCH"):
        validate_artifact_fingerprints(
            dataset, forecast, expected_dataset_sha=DATASET_SHA, expected_training_sha=training_sha
        )
