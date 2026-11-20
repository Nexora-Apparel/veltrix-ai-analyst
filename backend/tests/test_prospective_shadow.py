from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from app.research.prospective_shadow import (
    build_shadow_predictions,
    select_training_rows,
)
from app.validation.prospective_dataset import ProspectiveDatasetRow

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _rights_lineage(
    *,
    observed_at: datetime,
    availability_basis: str,
    import_run_id: int | None = None,
    valid_until: datetime | None = None,
) -> dict:
    lineage = {
        "availability_basis": availability_basis,
        "rights_status": "APPROVED",
        "rights_valid_from": (BASE - timedelta(days=2)).isoformat(),
        "rights_valid_until": valid_until.isoformat() if valid_until else None,
        "rights_permitted_uses": ["MODEL_TRAINING", "MODEL_VALIDATION"],
        "rights_status_events": [],
        "point_in_time_certifiable": availability_basis == "SYSTEM_OBSERVED_AT",
    }
    if availability_basis == "SYSTEM_OBSERVED_AT":
        lineage["system_observed_at"] = observed_at.isoformat()
    else:
        lineage["import_run_finished_at"] = observed_at.isoformat()
        lineage["import_run_id"] = import_run_id
    return lineage


def _labelled_row(
    fixture_id: str,
    *,
    kickoff_at: datetime,
    observed_at: datetime,
    validation_eligible: bool,
    prediction_cutoff_at: datetime | None = None,
    valid_until: datetime | None = None,
    import_run_id: int = 100,
) -> ProspectiveDatasetRow:
    basis = (
        "SYSTEM_OBSERVED_AT"
        if validation_eligible
        else "IMPORT_RUN_COMPLETED_AT_TRAINING_ONLY"
    )
    return ProspectiveDatasetRow(
        fixture_id=fixture_id,
        provider="5DollarFootballAPI",
        source_id="5dollarfootballapi",
        competition_id="league",
        kickoff_at=kickoff_at,
        prediction_cutoff_at=prediction_cutoff_at,
        home_team_id=f"{fixture_id}-home",
        away_team_id=f"{fixture_id}-away",
        features={},
        feature_lineage=(),
        label={"home_goals": 2, "away_goals": 1},
        label_observed_at=observed_at,
        label_observation_id=import_run_id,
        label_lineage=_rights_lineage(
            observed_at=observed_at,
            availability_basis=basis,
            import_run_id=import_run_id,
            valid_until=valid_until,
        ),
        canonical_fixture_id=f"canonical-{fixture_id}",
        canonical_competition_id="canonical-league",
        validation_eligible=validation_eligible,
    )


def _target_row(
    fixture_id: str,
    *,
    kickoff_at: datetime,
    prediction_cutoff_at: datetime,
) -> ProspectiveDatasetRow:
    return ProspectiveDatasetRow(
        fixture_id=fixture_id,
        provider="5DollarFootballAPI",
        source_id="5dollarfootballapi",
        competition_id="league",
        kickoff_at=kickoff_at,
        prediction_cutoff_at=prediction_cutoff_at,
        home_team_id="target-home",
        away_team_id="target-away",
        features={"home_matches_last5": 0.0},
        feature_lineage=(),
        label=None,
        label_observed_at=None,
        label_observation_id=None,
        label_lineage=None,
        canonical_fixture_id=f"canonical-{fixture_id}",
        canonical_competition_id="canonical-league",
        validation_eligible=True,
    )


def test_training_rows_require_label_availability_and_rights_before_cutoff():
    cutoff = BASE + timedelta(days=10)
    eligible_history = _labelled_row(
        "history-eligible",
        kickoff_at=BASE + timedelta(days=1),
        observed_at=cutoff - timedelta(hours=3),
        validation_eligible=False,
    )
    late_history = _labelled_row(
        "history-late",
        kickoff_at=BASE + timedelta(days=2),
        observed_at=cutoff + timedelta(hours=1),
        validation_eligible=False,
        import_run_id=101,
    )
    expired_history = _labelled_row(
        "history-rights-expired",
        kickoff_at=BASE + timedelta(days=2),
        observed_at=cutoff - timedelta(hours=2),
        validation_eligible=False,
        valid_until=cutoff - timedelta(hours=1),
        import_run_id=102,
    )
    eligible_prospective = _labelled_row(
        "prospective-eligible",
        kickoff_at=BASE + timedelta(days=4),
        observed_at=BASE + timedelta(days=4, hours=3),
        validation_eligible=True,
        prediction_cutoff_at=BASE + timedelta(days=4) - timedelta(hours=1),
        import_run_id=103,
    )

    selected = select_training_rows(
        [eligible_history, late_history, expired_history],
        [eligible_prospective],
        prediction_cutoff_at=cutoff,
    )

    assert [row.fixture_id for row in selected] == [
        "history-eligible",
        "prospective-eligible",
    ]
    assert all(row.label_observed_at < cutoff for row in selected)


def test_shadow_builder_rejects_stale_snapshots():
    generated_at = BASE + timedelta(days=10)
    stale_target = _target_row(
        "stale-target",
        kickoff_at=generated_at + timedelta(days=1),
        prediction_cutoff_at=BASE + timedelta(days=1),
    )

    report = build_shadow_predictions(
        {"rows": [stale_target], "training_only_rows": [], "dataset_sha256": "a" * 64},
        generated_at=generated_at,
    )

    assert report["status"] == "NO_FRESH_UPCOMING_SNAPSHOTS"
    assert report["predictions"] == []
    assert report["production_promotion"] == "LOCKED"
    assert report["value_betting"] == "LOCKED"


def test_shadow_builder_refuses_to_fit_without_cutoff_valid_training_labels():
    generated_at = BASE + timedelta(days=10)
    fresh_target = _target_row(
        "fresh-target",
        kickoff_at=generated_at + timedelta(days=1),
        prediction_cutoff_at=generated_at - timedelta(hours=1),
    )

    report = build_shadow_predictions(
        {"rows": [fresh_target], "training_only_rows": [], "dataset_sha256": "b" * 64},
        generated_at=generated_at,
    )

    assert report["status"] == "INSUFFICIENT_CUTOFF_VALID_TRAINING_LABELS"
    assert report["training_fixture_count"] == 0
    assert report["predictions"] == []


def test_shadow_builder_produces_auditable_forecast_from_cutoff_valid_labels():
    generated_at = BASE + timedelta(days=45)
    training_rows = []
    for index in range(40):
        kickoff = BASE + timedelta(days=index + 1)
        observed = kickoff + timedelta(hours=3)
        row = _labelled_row(
            f"training-{index:02d}",
            kickoff_at=kickoff,
            observed_at=observed,
            validation_eligible=False,
            import_run_id=1000 + index,
        )
        home_index = index % 8
        away_index = (home_index + 1) % 8
        training_rows.append(replace(
            row,
            home_team_id=f"team-{home_index}",
            away_team_id=f"team-{away_index}",
        ))

    target = _target_row(
        "future-target",
        kickoff_at=generated_at + timedelta(days=1),
        prediction_cutoff_at=generated_at - timedelta(hours=1),
    )
    report = build_shadow_predictions(
        {
            "rows": [target],
            "training_only_rows": training_rows,
            "dataset_sha256": "c" * 64,
            "feature_schema_version": "test-v1",
        },
        generated_at=generated_at,
        minimum_training_fixtures=30,
    )

    assert report["status"] == "SHADOW_FORECASTS_READY"
    assert report["training_fixture_count"] == 40
    assert report["training_cutoff_at"] == (
        BASE + timedelta(days=40, hours=3)
    ).isoformat()
    assert report["forecast_count"] == 1
    prediction = report["predictions"][0]
    assert prediction["canonical_fixture_id"] == "canonical-future-target"
    assert prediction["publication_status"] == "NOT_PUBLISHED"
    assert prediction["value_betting_status"] == "LOCKED"
    assert prediction["snapshot_feature_audit"]["field_count"] == 1
    assert sum(prediction["markets"]["1X2"].values()) == pytest.approx(1.0)
    assert report["production_promotion"] == "LOCKED"
    assert report["value_betting"] == "LOCKED"
