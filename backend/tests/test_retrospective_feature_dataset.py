from datetime import datetime, timezone

import pytest

from app.research.retrospective_feature_dataset import build_dataset, write_content_addressed


def _row(fixture_id: str, kickoff: datetime, home: str, away: str, home_goals: int, away_goals: int):
    return {
        "fixture_id": fixture_id,
        "competition_id": "league-a",
        "kickoff_at": kickoff,
        "home_team_id": home,
        "away_team_id": away,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "home_corners": 4,
        "away_corners": 3,
        "home_yellow_cards": 1,
        "away_yellow_cards": 2,
        "home_red_cards": 0,
        "away_red_cards": 0,
        "source_observation_id": int(fixture_id),
        "provider_response_id": 100 + int(fixture_id),
        "retrieved_at": datetime(2026, 11, 19, tzinfo=timezone.utc),
        "availability_basis": "RETRIEVED_AT_ONLY",
        "point_in_time_certifiable": False,
        "payload_sha256": "a" * 64,
        "rights_approval_id": "approval-a",
        "rights_status": "APPROVED",
        "permitted_uses": ["FEATURE_ENGINEERING", "MODEL_TRAINING"],
        "rights_valid_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "rights_valid_until": None,
    }


def test_dataset_is_separate_and_non_pit_with_source_lineage():
    rows = [
        _row("1", datetime(2026, 1, 1, tzinfo=timezone.utc), "A", "B", 2, 0),
        _row("2", datetime(2026, 1, 8, tzinfo=timezone.utc), "B", "C", 1, 1),
    ]
    dataset = build_dataset(rows)
    assert dataset["dataset_type"] == "RETROSPECTIVE_RESEARCH_TRAINING_ONLY"
    assert dataset["validation_eligible"] is False
    assert dataset["point_in_time_certifiable"] is False
    assert dataset["prospective_dataset_join"] is False
    second = dataset["rows"][1]
    assert second["features"]["home_prior_match_count"] == 1
    assert second["features"]["home_goals_for_mean"] == 0.0
    assert second["feature_provenance"]["history_fixture_ids"] == ["1"]
    assert second["feature_provenance"]["source_observation_id"] == 2
    assert second["feature_provenance"]["availability_basis"] == "RETRIEVED_AT_ONLY"
    assert second["validation_eligible"] is False
    assert second["certification_eligible"] is False


def test_simultaneous_fixtures_do_not_leak_into_each_other():
    kickoff = datetime(2026, 1, 1, tzinfo=timezone.utc)
    dataset = build_dataset([
        _row("1", kickoff, "A", "B", 2, 0),
        _row("2", kickoff, "B", "C", 1, 1),
    ])
    assert dataset["rows"][0]["features"]["home_prior_match_count"] == 0
    assert dataset["rows"][1]["features"]["home_prior_match_count"] == 0


def test_content_addressed_artifact_is_stable(tmp_path):
    dataset = build_dataset([
        _row("1", datetime(2026, 1, 1, tzinfo=timezone.utc), "A", "B", 2, 0),
    ])
    path, digest = write_content_addressed(dataset, tmp_path)
    assert path.exists()
    assert digest in path.name
    assert path.read_text(encoding="utf-8").find('"validation_eligible": false') >= 0

def test_dataset_fails_closed_when_research_rights_are_not_approved():
    row = _row("1", datetime(2026, 1, 1, tzinfo=timezone.utc), "A", "B", 2, 0)
    row["rights_status"] = "PROVISIONAL"
    with pytest.raises(RuntimeError, match="RETROSPECTIVE_TRAINING_RIGHTS_NOT_VERIFIED"):
        build_dataset([row])


def test_dataset_fails_closed_when_model_training_use_is_missing():
    row = _row("1", datetime(2026, 1, 1, tzinfo=timezone.utc), "A", "B", 2, 0)
    row["permitted_uses"] = ["FEATURE_ENGINEERING"]
    with pytest.raises(RuntimeError, match="RETROSPECTIVE_TRAINING_RIGHTS_NOT_VERIFIED"):
        build_dataset([row])
