from __future__ import annotations

import pytest

from scripts.materialize_canonical_entities import main


def test_materialization_runner_requires_exact_confirmation(monkeypatch) -> None:
    monkeypatch.setenv("CANONICAL_MATERIALIZATION_CONFIRMATION", "NO")
    monkeypatch.setenv("DATABASE_URL", "postgresql://not-used")
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")

    with pytest.raises(SystemExit, match="CANONICAL_MATERIALIZATION_CONFIRMATION_REQUIRED"):
        main()


def test_materialization_runner_requires_dedicated_database_name(monkeypatch) -> None:
    monkeypatch.setenv(
        "CANONICAL_MATERIALIZATION_CONFIRMATION",
        "MATERIALIZE_BRAZIL_SERIE_B_RUN_3",
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql://not-used")
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "neondb")

    with pytest.raises(SystemExit, match="CANONICAL_MATERIALIZATION_EXPECTED_DATABASE_INVALID"):
        main()


def test_materialization_runner_requires_database_url(monkeypatch) -> None:
    monkeypatch.setenv(
        "CANONICAL_MATERIALIZATION_CONFIRMATION",
        "MATERIALIZE_BRAZIL_SERIE_B_RUN_3",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")

    with pytest.raises(SystemExit, match="CANONICAL_MATERIALIZATION_DATABASE_URL_MISSING"):
        main()
