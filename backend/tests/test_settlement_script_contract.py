import pytest

from scripts.settle_published_predictions import (
    CANDIDATE_QUERY,
    DATABASE_NAME,
    parse_args,
    settle_published_predictions,
)


def test_settlement_worker_defaults_to_read_only_dry_run():
    args = parse_args([])

    assert args.execute is False
    assert args.limit == 250


def test_settlement_worker_bounds_batch_size():
    with pytest.raises(SystemExit):
        parse_args(["--limit", "0"])
    with pytest.raises(SystemExit):
        parse_args(["--limit", "5001"])


def test_settlement_worker_checks_database_target_before_connecting():
    with pytest.raises(ValueError, match="EXPECTED_DATABASE_NAME_MISMATCH"):
        settle_published_predictions(
            "",
            expected_database="wrong_database",
            execute=True,
        )


def test_settlement_candidate_query_requires_verified_pit_result_evidence():
    assert "latest_prediction_settlements" in CANDIDATE_QUERY
    assert "SOURCE_FIXTURE_LINK_REVIEWED" in CANDIDATE_QUERY
    assert "SYSTEM_OBSERVED_AT" in CANDIDATE_QUERY
    assert "point_in_time_certifiable IS TRUE" in CANDIDATE_QUERY
    assert "MODEL_TRAINING" in CANDIDATE_QUERY
    assert "MODEL_VALIDATION" in CANDIDATE_QUERY
    assert "provider_response_sha256" not in CANDIDATE_QUERY
    assert "5DollarFootballAPI" in CANDIDATE_QUERY
    assert "The Odds API" not in CANDIDATE_QUERY
    assert DATABASE_NAME == "veltrix_ai_analyst"
