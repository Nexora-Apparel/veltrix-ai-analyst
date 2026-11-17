from datetime import UTC, datetime, timedelta

from app.models.attack_defence import GoalResult
from app.research.train_final_model import build_artifact, dataset_fingerprint

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def make_results():
    teams = ("A", "B", "C", "D")
    return [
        GoalResult(
            fixture_id=f"fixture-{day}",
            kickoff_at=BASE + timedelta(days=day),
            home_team=teams[day % 4],
            away_team=teams[(day + 1) % 4],
            home_goals=2 if day % 3 else 0,
            away_goals=0 if day % 3 else 1,
        )
        for day in range(24)
    ]


def test_dataset_fingerprint_is_order_independent():
    rows = make_results()
    assert dataset_fingerprint(rows) == dataset_fingerprint(list(reversed(rows)))


def test_final_training_artifact_is_research_only_and_keeps_models_separate():
    artifact_id, fingerprint, artifact = build_artifact(make_results())
    assert artifact_id == f"v1-{fingerprint[:32]}"
    assert artifact["training_fixtures"] == 24
    assert artifact["distinct_provider_team_ids"] == 4
    assert artifact["temporal_certification"] == "RETROSPECTIVE_EVENT_TIME_NOT_PIT_CERTIFIED"
    assert artifact["deployment_status"] == "RESEARCH_ARTIFACT_ONLY"
    assert artifact["primary_model"]["family"] == "RECENCY_WEIGHTED_ATTACK_DEFENCE_POISSON"
    assert artifact["elo_comparator"]["status"] == "RETAINED_FOR_RESEARCH_NOT_SELECTED_FOR_ENSEMBLE"
    assert artifact["dixon_coles"]["status"] == "NOT_CALIBRATED; INDEPENDENT_POISSON_BASELINE"
