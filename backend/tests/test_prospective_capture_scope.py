from app.providers.prospective_capture_scope import PROSPECTIVE_CAPTURE_COMPETITIONS


def test_prospective_capture_uses_only_identity_safe_competitions() -> None:
    competition_ids = [competition_id for competition_id, _ in PROSPECTIVE_CAPTURE_COMPETITIONS]
    competition_names = [name for _, name in PROSPECTIVE_CAPTURE_COMPETITIONS]

    assert len(competition_ids) == 6
    assert len(competition_ids) == len(set(competition_ids))
    assert "3614399544" not in competition_ids
    assert "France Ligue 1" not in competition_names
    assert set(competition_names) == {
        "Brazil Serie A",
        "Brazil Serie B",
        "England Premier League",
        "Germany Bundesliga I",
        "Italy Serie A",
        "Spain La Liga",
    }
