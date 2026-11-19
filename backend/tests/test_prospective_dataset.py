# ruff: noqa: I001
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.validation.prospective_dataset import (
    FixtureIdentity,
    FixtureObservation,
    ProspectiveDatasetRow,
    build_expanding_window_folds,
    build_prospective_dataset,
)


BASE = datetime(2026, 1, 1, tzinfo=UTC)


def fixture(fid, home, away, day, competition="league"):
    return FixtureIdentity(
        fixture_id=fid,
        provider="5DollarFootballAPI",
        source_id="5dollarfootballapi",
        competition_id=competition,
        home_team_id=home,
        away_team_id=away,
        kickoff_at=BASE + timedelta(days=day),
    )


def observation(fid, oid, sid, when, status, home_goals=None, away_goals=None):
    payload = {"status": status}
    if home_goals is not None:
        payload["home_goals"] = home_goals
    if away_goals is not None:
        payload["away_goals"] = away_goals
    return FixtureObservation(
        observation_id=oid,
        sighting_id=sid,
        provider_response_id=1000 + oid,
        fixture_id=fid,
        provider="5DollarFootballAPI",
        source_id="5dollarfootballapi",
        retrieved_at=when - timedelta(milliseconds=1),
        observed_at=when,
        availability_basis="SYSTEM_OBSERVED_AT",
        point_in_time_certifiable=True,
        payload_sha256=f"{oid:064x}",
        raw_response_sha256=f"{oid + 100:064x}",
        payload=payload,
        rights_approval_id="test-approval",
        rights_status="APPROVED",
        rights_valid_from=BASE - timedelta(days=365),
        rights_permitted_uses=(
            "FEATURE_ENGINEERING",
            "MODEL_TRAINING",
            "MODEL_VALIDATION",
        ),
    )


def test_dataset_uses_only_results_observed_before_target_cutoff():
    fixtures = [
        fixture("past-1", "A", "B", 1),
        fixture("past-2", "C", "A", 2),
        fixture("target", "A", "C", 5),
    ]
    observations = [
        observation("past-1", 1, 1, BASE + timedelta(days=2), "finished", 2, 0),
        observation("past-2", 2, 2, BASE + timedelta(days=3), "finished", 1, 1),
        observation("past-1", 6, 6, BASE + timedelta(days=3, hours=12), "finished", 3, 0),
        observation("target", 3, 3, BASE + timedelta(days=4), "scheduled"),
        # A result captured after the target cutoff must not enter its features.
        observation("past-2", 4, 4, BASE + timedelta(days=4, hours=1), "finished", 4, 0),
        observation("target", 5, 5, BASE + timedelta(days=6), "finished", 2, 1),
    ]
    rows = build_prospective_dataset(fixtures, observations)
    target = next(row for row in rows if row.fixture_id == "target")
    assert target.prediction_cutoff_at == BASE + timedelta(days=4)
    assert target.features["home_matches_last5"] == 2
    assert target.features["home_goals_for_per_match_last5"] == 2.0
    assert target.features["away_matches_last5"] == 1
    assert target.label == {
        "home_goals": 2,
        "away_goals": 1,
        "home_win": True,
        "draw": False,
        "away_win": False,
        "btts": True,
        "over_25": True,
    }
    assert target.label_observation_id == 5
    assert target.label_lineage is not None
    assert target.label_lineage["provider_response_id"] == 1005
    assert all(item["system_observed_at"] <= target.prediction_cutoff_at.isoformat()
               for item in target.feature_lineage)
    assert 6 in {item["source_observation_id"] for item in target.feature_lineage}
    assert 1 not in {item["source_observation_id"] for item in target.feature_lineage}


def test_post_kickoff_schedule_snapshot_is_not_a_target_row():
    target = fixture("target", "A", "B", 1)
    late = observation("target", 1, 1, BASE + timedelta(days=1), "scheduled")
    assert build_prospective_dataset([target], [late]) == ()


def test_retrieval_only_observations_are_excluded():
    target = fixture("target", "A", "B", 2)
    late = observation("target", 1, 1, BASE, "scheduled")
    late = FixtureObservation(
        observation_id=late.observation_id,
        sighting_id=late.sighting_id,
        provider_response_id=late.provider_response_id,
        fixture_id=late.fixture_id,
        provider=late.provider,
        source_id=late.source_id,
        retrieved_at=late.retrieved_at,
        observed_at=late.observed_at,
        availability_basis="RETRIEVED_AT_ONLY",
        point_in_time_certifiable=False,
        payload_sha256=late.payload_sha256,
        raw_response_sha256=late.raw_response_sha256,
        payload=late.payload,
    )
    assert build_prospective_dataset([target], [late]) == ()


def test_expanding_folds_keep_simultaneous_kickoffs_together():
    fixtures = [fixture(f"f-{i}", f"h-{i}", f"a-{i}", i + 1) for i in range(8)]
    observations = []
    for i, f in enumerate(fixtures):
        observations.append(observation(f.fixture_id, i + 1, i + 1, f.kickoff_at - timedelta(hours=2), "scheduled"))
        observations.append(observation(f.fixture_id, i + 101, i + 101, f.kickoff_at + timedelta(hours=2), "finished", 1, 0))
    # Add a simultaneous fixture at day 4.
    simultaneous = fixture("f-same-time", "hx", "ax", 4)
    fixtures.append(simultaneous)
    observations.extend([
        observation("f-same-time", 20, 20, simultaneous.kickoff_at - timedelta(hours=1), "scheduled"),
        observation("f-same-time", 120, 120, simultaneous.kickoff_at + timedelta(hours=2), "finished", 0, 0),
    ])
    rows = build_prospective_dataset(fixtures, observations)
    folds = build_expanding_window_folds(rows, minimum_training_fixtures=3, validation_block_fixtures=2)
    assert folds
    for fold in folds:
        assert set(fold.train_fixture_ids).isdisjoint(fold.validation_fixture_ids)
        assert all(
            next(row for row in rows if row.fixture_id == fid).kickoff_at < fold.validation_start_at
            and next(row for row in rows if row.fixture_id == fid).label_observed_at < fold.validation_start_at
            for fid in fold.train_fixture_ids
        )
        if "f-3" in fold.validation_fixture_ids or "f-same-time" in fold.validation_fixture_ids:
            assert {"f-3", "f-same-time"}.issubset(fold.validation_fixture_ids)


def test_stale_fixture_identity_observation_is_rejected():
    target = fixture("league:target", "A", "B", 2)
    stale = observation(
        "league:target", 1, 1, BASE, "scheduled"
    )
    stale_payload = {
        **stale.payload,
        "competition_id": "league",
        "home_team_id": "A",
        "away_team_id": "B",
        "kickoff_at": (BASE + timedelta(days=3)).isoformat(),
        "provenance": {"provider_record_id": "target"},
    }
    stale = FixtureObservation(
        observation_id=stale.observation_id,
        sighting_id=stale.sighting_id,
        provider_response_id=stale.provider_response_id,
        fixture_id=stale.fixture_id,
        provider=stale.provider,
        source_id=stale.source_id,
        retrieved_at=stale.retrieved_at,
        observed_at=stale.observed_at,
        availability_basis=stale.availability_basis,
        point_in_time_certifiable=stale.point_in_time_certifiable,
        payload_sha256=stale.payload_sha256,
        raw_response_sha256=stale.raw_response_sha256,
        payload=stale_payload,
        rights_approval_id=stale.rights_approval_id,
        rights_status=stale.rights_status,
        rights_valid_from=stale.rights_valid_from,
        rights_valid_until=stale.rights_valid_until,
        rights_permitted_uses=stale.rights_permitted_uses,
        rights_status_events=stale.rights_status_events,
    )
    try:
        build_prospective_dataset([target], [stale])
    except ValueError as exc:
        assert "kickoff_at" in str(exc)
    else:
        raise AssertionError("stale fixture identity must fail closed")


def test_same_provider_fixture_id_isolated_by_competition_scope():
    fixtures = [
        fixture("league-a:shared-id", "A", "B", 2, "league-a"),
        fixture("league-b:shared-id", "C", "D", 2, "league-b"),
    ]
    observations = [
        observation(
            "league-a:shared-id", 91, 91, BASE + timedelta(days=1), "scheduled"
        ),
        observation(
            "league-b:shared-id", 92, 92, BASE + timedelta(days=1), "scheduled"
        ),
    ]
    rows = build_prospective_dataset(fixtures, observations)
    assert {row.fixture_id for row in rows} == {
        "league-a:shared-id",
        "league-b:shared-id",
    }
    assert {row.competition_id for row in rows} == {"league-a", "league-b"}


def test_dataset_derives_rolling_stats_and_events_only_from_prior_matches():
    past = fixture("past", "A", "C", 1)
    target = fixture("target", "A", "B", 5)
    past_observation = observation(
        "past", 101, 101, BASE + timedelta(days=2), "finished", 2, 1
    )
    past_observation.payload.update({
        "statistics": {
            "shots_on_target": {"home": 4, "away": 2},
            "shots_off_target": {"home": 5, "away": 3},
            "dangerous_attacks": {"home": 22, "away": 17},
            "attacks": {"home": 41, "away": 35},
            "possession": {"home": 58, "away": 42},
            "first_half": {
                "shots_on_target": {"home": 2, "away": 1},
                "dangerous_attacks": {"home": 10, "away": 8},
            },
        },
        "home_corners": 6,
        "home_yellow_cards": 1,
        "home_red_cards": 0,
        "events": [
            {"type": "goal", "minute": 80, "team": "home"},
            {"type": "substitution", "minute": 70, "team": "home"},
        ],
    })
    target_observation = observation(
        "target", 102, 102, BASE + timedelta(days=4), "scheduled"
    )
    rows = build_prospective_dataset(
        [past, target],
        [past_observation, target_observation],
    )
    target_row = next(row for row in rows if row.fixture_id == "target")
    assert target_row.features["home_shots_on_target_avg_last5"] == 4.0
    assert target_row.features["home_possession_avg_last5"] == 58.0
    assert target_row.features["home_corners_avg_last5"] == 6.0
    assert target_row.features["home_first_half_shots_on_target_avg_last5"] == 2.0
    assert target_row.features["home_late_goals_for_avg_last5"] == 1.0
    assert target_row.features["home_substitutions_avg_last5"] == 1.0
    assert target_row.features["away_stats_coverage_last5"] == 0.0


def test_no_history_records_counts_but_does_not_invent_zero_rate_features():
    target = fixture("target", "A", "B", 2)
    scheduled = observation("target", 1, 1, BASE, "scheduled")

    rows = build_prospective_dataset([target], [scheduled])

    assert len(rows) == 1
    features = rows[0].features
    assert features["home_matches_last5"] == 0.0
    assert features["away_matches_last5"] == 0.0
    assert features["competition_matches_last20"] == 0.0
    assert "home_goals_for_per_match_last5" not in features
    assert "home_goals_against_per_match_last5" not in features
    assert "home_points_per_match_last5" not in features
    assert "home_rest_days" not in features
    assert "away_goals_for_per_match_last5" not in features
    assert "competition_goals_per_match_last20" not in features
    assert "competition_btts_rate_last20" not in features


def test_one_sided_sparse_history_does_not_fill_missing_team_with_zero_rates():
    past = fixture("past", "A", "C", 1)
    target = fixture("target", "A", "B", 5)
    past_result = observation(
        "past", 10, 10, BASE + timedelta(days=2), "finished", 2, 1
    )
    target_schedule = observation(
        "target", 11, 11, BASE + timedelta(days=4), "scheduled"
    )

    rows = build_prospective_dataset(
        [past, target],
        [past_result, target_schedule],
    )
    target_row = next(row for row in rows if row.fixture_id == "target")
    features = target_row.features

    assert features["home_matches_last5"] == 1.0
    assert features["home_goals_for_per_match_last5"] == 2.0
    assert features["home_goals_against_per_match_last5"] == 1.0
    assert features["away_matches_last5"] == 0.0
    assert "away_goals_for_per_match_last5" not in features
    assert "away_goals_against_per_match_last5" not in features


def test_canonical_competition_key_unifies_provider_scope_for_team_history():
    past = FixtureIdentity(
        fixture_id="provider-league-a:past",
        provider="5DollarFootballAPI",
        source_id="5dollarfootballapi",
        competition_id="provider-league-a",
        home_team_id="canonical-team-a",
        away_team_id="canonical-team-c",
        kickoff_at=BASE + timedelta(days=1),
        canonical_competition_id="canonical-league",
        provider_home_team_id="provider-team-a",
        provider_away_team_id="provider-team-c",
    )
    target = FixtureIdentity(
        fixture_id="provider-league-b:target",
        provider="5DollarFootballAPI",
        source_id="5dollarfootballapi",
        competition_id="provider-league-b",
        home_team_id="canonical-team-a",
        away_team_id="canonical-team-b",
        kickoff_at=BASE + timedelta(days=5),
        canonical_competition_id="canonical-league",
        provider_home_team_id="provider-team-a",
        provider_away_team_id="provider-team-b",
    )
    past_result = observation(
        past.fixture_id, 201, 201, BASE + timedelta(days=2), "finished", 2, 1
    )
    past_result.payload.update({
        "competition_id": "provider-league-a",
        "home_team_id": "provider-team-a",
        "away_team_id": "provider-team-c",
        "kickoff_at": past.kickoff_at.isoformat(),
        "provenance": {"provider_record_id": "past"},
    })
    target_schedule = observation(
        target.fixture_id, 202, 202, BASE + timedelta(days=4), "scheduled"
    )
    target_schedule.payload.update({
        "competition_id": "provider-league-b",
        "home_team_id": "provider-team-a",
        "away_team_id": "provider-team-b",
        "kickoff_at": target.kickoff_at.isoformat(),
        "provenance": {"provider_record_id": "target"},
    })

    rows = build_prospective_dataset(
        [past, target], [past_result, target_schedule]
    )
    target_row = next(row for row in rows if row.fixture_id == target.fixture_id)

    assert target_row.features["home_matches_last5"] == 1.0
    assert target_row.canonical_competition_id == "canonical-league"


def test_historical_training_only_rows_seed_folds_but_never_validate():
    def labelled_row(fid, day, observed_day, *, validation_eligible):
        kickoff = BASE + timedelta(days=day)
        observed = BASE + timedelta(days=observed_day)
        training_only = not validation_eligible
        lineage = {
            "rights_approval_id": "test-approval",
            "rights_status": "APPROVED",
            "rights_valid_from": (BASE - timedelta(days=365)).isoformat(),
            "rights_valid_until": None,
            "rights_permitted_uses": ["MODEL_TRAINING", "MODEL_VALIDATION"],
            "rights_status_events": [],
            "availability_basis": (
                "DATABASE_INSERTED_AT_TRAINING_ONLY"
                if training_only else "SYSTEM_OBSERVED_AT"
            ),
            "point_in_time_certifiable": not training_only,
        }
        if training_only:
            lineage["database_inserted_at"] = observed.isoformat()
        else:
            lineage["system_observed_at"] = observed.isoformat()
        return ProspectiveDatasetRow(
            fixture_id=fid,
            provider="5DollarFootballAPI",
            source_id="5dollarfootballapi",
            competition_id="league",
            kickoff_at=kickoff,
            prediction_cutoff_at=(
                None if training_only else kickoff - timedelta(hours=2)
            ),
            home_team_id=f"{fid}-home",
            away_team_id=f"{fid}-away",
            features={},
            feature_lineage=(),
            label={
                "home_goals": 2,
                "away_goals": 1,
                "home_win": True,
                "draw": False,
                "away_win": False,
                "btts": True,
                "over_25": True,
            },
            label_observed_at=observed,
            label_observation_id=1,
            label_lineage=lineage,
            validation_eligible=validation_eligible,
        )

    history = labelled_row(
        "history-only", 1, 2, validation_eligible=False
    )
    first = labelled_row("prospective-1", 5, 6, validation_eligible=True)
    second = labelled_row("prospective-2", 7, 8, validation_eligible=True)

    folds = build_expanding_window_folds(
        [history, first, second],
        minimum_training_fixtures=1,
        validation_block_fixtures=1,
    )

    assert len(folds) == 2
    assert folds[0].train_fixture_ids == ("history-only",)
    assert folds[0].validation_fixture_ids == ("prospective-1",)
    assert "history-only" in folds[1].train_fixture_ids
    assert "prospective-1" in folds[1].train_fixture_ids
    assert all(
        "history-only" not in fold.validation_fixture_ids
        for fold in folds
    )

