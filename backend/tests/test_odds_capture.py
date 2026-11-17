from datetime import UTC, datetime, timedelta
import pytest
from pydantic import ValidationError
from app.providers.odds_capture import normalize_5dollar_odds

CUTOFF = datetime(2026, 11, 17, 12, tzinfo=UTC)
KICKOFF = CUTOFF + timedelta(hours=2)
TICK = CUTOFF - timedelta(minutes=5)
RETRIEVED = CUTOFF - timedelta(minutes=4)

def payload():
    return {"odds": [{"bookmaker": "Bet365", "markets": [{"market": "1X2", "outcomes": [
        {"name": "Home", "odds": 2.1, "recorded_at": TICK.isoformat()},
        {"name": "Draw", "odds": 3.2, "recorded_at": TICK.isoformat()},
    ]}]}]}

def normalize(data, **overrides):
    args = dict(provider_fixture_id="fx-1", kickoff_at=KICKOFF, retrieved_at=RETRIEVED,
        prediction_cutoff_at=CUTOFF, source_observation_id="obs-1",
        rights_approval_id="rights-1", rights_allow_model_training=True)
    args.update(overrides)
    return normalize_5dollar_odds(data, **args)

def test_normalizes_separate_source_and_retrieval_clocks():
    rows = normalize(payload())
    assert len(rows) == 2
    assert rows[0].source_tick_at == TICK
    assert rows[0].retrieved_at == RETRIEVED

def test_rejects_retrieval_after_prediction_cutoff():
    with pytest.raises(ValidationError, match="retrieved after"):
        normalize(payload(), retrieved_at=CUTOFF + timedelta(seconds=1))

def test_rejects_source_tick_after_cutoff():
    data = payload()
    data["odds"][0]["markets"][0]["outcomes"][0]["recorded_at"] = (CUTOFF + timedelta(seconds=1)).isoformat()
    with pytest.raises(ValidationError, match="retrieved after"):
        normalize(data, retrieved_at=CUTOFF + timedelta(minutes=2))

def test_rejects_missing_source_tick_instead_of_inventing_it():
    data = {"odds": [{"bookmaker": "Bet365", "markets": [{"market": "1X2",
        "outcomes": [{"name": "Home", "odds": 2.1}]}]}]}
    with pytest.raises(ValueError, match="missing recorded_at"):
        normalize(data)

def test_rejects_unapproved_rights():
    with pytest.raises(ValidationError, match="rights"):
        normalize(payload(), rights_allow_model_training=False)

def test_rejects_in_play_market():
    data = payload()
    data["odds"][0]["in_play"] = True
    with pytest.raises(ValidationError, match="in-play"):
        normalize(data)
