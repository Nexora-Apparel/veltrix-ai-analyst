from datetime import UTC, datetime, timedelta

import pytest

from app.providers.odds_capture import (
    OddsPayloadError,
    normalize_5dollar_fixture_odds,
    normalize_5dollar_odds,
    normalize_5dollar_odds_history,
)

CUTOFF = datetime(2026, 11, 17, 12, tzinfo=UTC)
KICKOFF = CUTOFF + timedelta(hours=2)
TICK = CUTOFF - timedelta(minutes=5)
RETRIEVED = CUTOFF - timedelta(minutes=4)


def base_args():
    return {
        "provider_fixture_id": "fx-1",
        "kickoff_at": KICKOFF,
        "retrieved_at": RETRIEVED,
        "prediction_cutoff_at": CUTOFF,
        "source_observation_id": "obs-1",
        "rights_approval_id": "rights-1",
        "rights_allow_model_training": True,
    }


def fixture_odds_response():
    return {
        "success": 1,
        "data": {
            "fixture_id": "fx-1",
            "bookmakers": [{
                "name": "Bet 365",
                "slug": "bet365",
                "odds": {
                    "1x2": {
                        "opening": {
                            "home": 2.1, "draw": 3.2, "away": 3.6,
                            "opened_at": TICK.isoformat(),
                        },
                        "closing": {"home": 1.9, "draw": 3.4, "away": 4.0},
                        "inplay": None,
                    },
                    "goal_line": {
                        "opening": {"line": 2.5, "over": 1.9, "under": 1.9},
                        "closing": {"line": 2.75, "over": 1.85, "under": 1.95},
                        "inplay": None,
                    },
                },
            }],
        },
    }


def odds_history_response():
    return {
        "success": 1,
        "data": {
            "fixture_id": "fx-1",
            "bookmaker": {"name": "Bet 365", "slug": "bet365"},
            "market": "1x2",
            "ticks": [
                {
                    "minute": None,
                    "home": 2.1, "draw": 3.2, "away": 3.6,
                    "score": {"home": None, "away": None},
                    "recorded_at": TICK.isoformat(),
                },
                {
                    "minute": 0,
                    "home": 2.0, "draw": 3.3, "away": 3.8,
                    "score": {"home": 0, "away": 0},
                    "recorded_at": (CUTOFF + timedelta(minutes=1)).isoformat(),
                },
            ],
        },
    }


def test_fixture_odds_uses_only_timestamped_1x2_opening_prices():
    rows = normalize_5dollar_fixture_odds(fixture_odds_response(), **base_args())
    assert len(rows) == 3
    assert {row.selection for row in rows} == {"home", "draw", "away"}
    assert all(row.market == "1X2" for row in rows)
    assert all(row.source_tick_at == TICK for row in rows)
    assert all(row.in_play is False for row in rows)
    # Goal-line snapshots and closing prices have no individual source tick in this endpoint.
    assert all(row.line is None for row in rows)


def test_fixture_odds_rejects_missing_opened_at():
    response = fixture_odds_response()
    del response["data"]["bookmakers"][0]["odds"]["1x2"]["opening"]["opened_at"]
    with pytest.raises(OddsPayloadError, match="timestamp is missing"):
        normalize_5dollar_fixture_odds(response, **base_args())


def test_fixture_odds_rejects_mismatched_fixture_identity():
    with pytest.raises(OddsPayloadError, match="does not match"):
        normalize_5dollar_fixture_odds(
            fixture_odds_response(), **{**base_args(), "provider_fixture_id": "other-fixture"}
        )


def test_history_normalizer_keeps_only_pre_match_ticks():
    rows = normalize_5dollar_odds_history(odds_history_response(), **base_args())
    assert len(rows) == 3
    assert {row.selection for row in rows} == {"home", "draw", "away"}
    assert all(row.source_tick_at == TICK for row in rows)
    assert all(row.in_play is False for row in rows)


def test_history_normalizer_rejects_missing_recorded_at():
    response = odds_history_response()
    del response["data"]["ticks"][0]["recorded_at"]
    with pytest.raises(OddsPayloadError, match="timestamp is missing"):
        normalize_5dollar_odds_history(response, **base_args())


def test_history_retrieval_after_cutoff_is_rejected():
    args = {
        **base_args(),
        "retrieved_at": CUTOFF + timedelta(minutes=2),
        "prediction_cutoff_at": CUTOFF,
    }
    with pytest.raises(OddsPayloadError, match="retrieved after"):
        normalize_5dollar_odds_history(odds_history_response(), **args)


def test_history_normalizer_maps_goal_line_to_totals():
    response = odds_history_response()
    response["data"]["market"] = "goalline"
    response["data"]["ticks"] = [{
        "minute": None, "line": 2.5, "over": 1.9, "under": 1.9,
        "score": {"home": None, "away": None}, "recorded_at": TICK.isoformat(),
    }]
    rows = normalize_5dollar_odds_history(response, **base_args())
    assert len(rows) == 2
    assert {row.market for row in rows} == {"TOTALS"}
    assert {row.selection for row in rows} == {"over", "under"}
    assert {row.line for row in rows} == {2.5}


def test_dispatcher_accepts_both_documented_envelopes():
    assert len(normalize_5dollar_odds(fixture_odds_response(), **base_args())) == 3
    assert len(normalize_5dollar_odds(odds_history_response(), **base_args())) == 3


def test_rejects_unapproved_training_rights():
    with pytest.raises(OddsPayloadError, match="rights"):
        normalize_5dollar_fixture_odds(
            fixture_odds_response(),
            **{**base_args(), "rights_allow_model_training": False},
        )


def test_rejects_unsuccessful_or_unrecognized_envelope():
    with pytest.raises(OddsPayloadError, match="success flag"):
        normalize_5dollar_fixture_odds({"success": 0, "data": {}}, **base_args())
    with pytest.raises(OddsPayloadError, match="unrecognized"):
        normalize_5dollar_odds({"success": 1, "data": {}}, **base_args())
