from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_cbf_scores_rounds_1_29 import parse_scored_row  # noqa: E402


def test_parse_cbf_score_row_with_full_schedule_metadata() -> None:
    row = [
        "005", "1ª", "21/03", "sáb", "16:00", "Ceará", "CE",
        "1", "x", "1", "São Bernardo", "FC", "SP", "Arena Castelão",
    ]

    parsed = parse_scored_row(row)

    assert parsed is not None
    assert parsed["cbf_reference"] == "5"
    assert parsed["home_label"] == "Ceará"
    assert parsed["away_label"] == "São Bernardo FC"
    assert parsed["home_goals"] == 1
    assert parsed["away_goals"] == 1
    assert parsed["home_team_provider_id"] == "1657329649"
    assert parsed["away_team_provider_id"] == "844813267"


def test_parse_cbf_score_row_with_merged_round_and_date_cells() -> None:
    row = [
        "010", "17:00", "Vila", "Nova", "GO", "2", "x", "2",
        "CRB", "AL", "Onésio", "B. Alvarenga",
    ]

    parsed = parse_scored_row(row)

    assert parsed is not None
    assert parsed["home_label"] == "Vila Nova"
    assert parsed["away_label"] == "CRB"
    assert (parsed["home_goals"], parsed["away_goals"]) == (2, 2)


def test_unplayed_cbf_fixture_is_not_treated_as_a_score() -> None:
    row = [
        "292", "30ª", "25/09", "sex", "19:30", "Novorizontino", "SP",
        "x", "São Bernardo", "FC", "SP",
    ]

    assert parse_scored_row(row) is None
