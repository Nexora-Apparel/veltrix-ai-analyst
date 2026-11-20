"""Classification rules for labeled and unlabeled retrospective source rows."""
from __future__ import annotations


def classify_fixture_row(status: str, home_goals: int | None, away_goals: int | None) -> str:
    """Return FINISHED, UNKNOWN, SCHEDULED, or INVALID without inventing labels."""
    scores_present = home_goals is not None and away_goals is not None
    scores_absent = home_goals is None and away_goals is None
    if status == "FINISHED" and scores_present:
        return "FINISHED"
    if status == "UNKNOWN" and scores_absent:
        return "UNKNOWN"
    if status == "SCHEDULED" and scores_absent:
        return "SCHEDULED"
    return "INVALID"
