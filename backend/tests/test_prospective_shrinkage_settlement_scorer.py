from app.research.prospective_shrinkage_settlement_scorer import score_settlements


def test_prospective_scorer_is_read_only_and_requires_frozen_hash():
    forecasts = {
        "predictions": [{
            "canonical_fixture_id": "fx-1",
            "canonical_competition_id": "league",
            "prediction_cutoff_at": "2026-11-22T10:00:00+00:00",
            "kickoff_at": "2026-11-22T12:00:00+00:00",
            "config_sha256": "frozen",
            "markets": {"1X2": {"HOME": 0.7, "DRAW": 0.2, "AWAY": 0.1}},
        }]
    }
    settlements = [{
        "canonical_fixture_id": "fx-1",
        "settled_at": "2026-11-22T14:00:00+00:00",
        "label_observed_at": "2026-11-22T13:30:00+00:00",
        "label": {"home_goals": 2, "away_goals": 0},
    }]
    report = score_settlements(forecasts, settlements, frozen_config_sha256="frozen")
    assert report["scored_fixture_count"] == 1
    assert report["database_writes"] == 0
    assert report["provider_calls"] == 0
    assert report["value_betting"] == "LOCKED"


def test_prospective_scorer_excludes_config_mismatch():
    forecasts = {"predictions": [{
        "canonical_fixture_id": "fx-2",
        "prediction_cutoff_at": "2026-11-22T10:00:00+00:00",
        "kickoff_at": "2026-11-22T12:00:00+00:00",
        "config_sha256": "wrong",
        "markets": {"1X2": {"HOME": 0.4, "DRAW": 0.3, "AWAY": 0.3}},
    }]}
    report = score_settlements(forecasts, [], frozen_config_sha256="right")
    assert report["scored_fixture_count"] == 0
    assert report["exclusions"][0]["reason"] == "FROZEN_CONFIG_HASH_MISMATCH"
