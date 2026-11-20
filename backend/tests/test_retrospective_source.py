from app.models.retrospective_source import classify_fixture_row


def test_classifies_finished_rows_with_both_scores() -> None:
    assert classify_fixture_row("FINISHED", 2, 1) == "FINISHED"


def test_classifies_unknown_unlabeled_rows() -> None:
    assert classify_fixture_row("UNKNOWN", None, None) == "UNKNOWN"


def test_classifies_scheduled_unlabeled_rows_separately() -> None:
    assert classify_fixture_row("SCHEDULED", None, None) == "SCHEDULED"


def test_rejects_finished_rows_without_scores() -> None:
    assert classify_fixture_row("FINISHED", None, None) == "INVALID"


def test_rejects_partial_scores_even_for_unlabeled_status() -> None:
    assert classify_fixture_row("SCHEDULED", 1, None) == "INVALID"
