from __future__ import annotations

import pytest

from scripts.materialize_round38_incremental import CONFIRMATION, main


def _configured(monkeypatch) -> None:
    monkeypatch.setenv("CANONICAL_INCREMENTAL_CONFIRMATION", CONFIRMATION)
    monkeypatch.setenv("DATABASE_URL", "postgresql://not-used")
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")


def test_round38_incremental_requires_exact_confirmation(monkeypatch) -> None:
    monkeypatch.setenv("CANONICAL_INCREMENTAL_CONFIRMATION", "NO")
    monkeypatch.setenv("DATABASE_URL", "postgresql://not-used")
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")
    with pytest.raises(SystemExit, match="CANONICAL_INCREMENTAL_CONFIRMATION_REQUIRED"):
        main()


def test_round38_incremental_rejects_wrong_database_name(monkeypatch) -> None:
    _configured(monkeypatch)
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "neondb")
    with pytest.raises(SystemExit, match="CANONICAL_INCREMENTAL_EXPECTED_DATABASE_INVALID"):
        main()


def test_round38_incremental_requires_database_url(monkeypatch) -> None:
    monkeypatch.setenv("CANONICAL_INCREMENTAL_CONFIRMATION", CONFIRMATION)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")
    with pytest.raises(SystemExit, match="CANONICAL_INCREMENTAL_DATABASE_URL_MISSING"):
        main()


def test_round38_incremental_scope_is_pinned_and_non_destructive() -> None:
    from scripts.materialize_round38_incremental import (
        EXPECTED_AFTER,
        EXPECTED_BEFORE,
        EXPECTED_CONFLICT_IDS,
        SCOPE,
    )

    assert SCOPE.import_run_id is None
    assert SCOPE.expected_fixture_count == 384
    assert SCOPE.expected_team_count == 21
    assert EXPECTED_BEFORE["canonical_fixtures"] == 374
    assert EXPECTED_AFTER["canonical_fixtures"] == 384
    assert EXPECTED_BEFORE["canonical_fixture_sources"] == 374
    assert EXPECTED_AFTER["canonical_fixture_sources"] == 384
    assert EXPECTED_CONFLICT_IDS == {"2341822348", "3116209225"}
