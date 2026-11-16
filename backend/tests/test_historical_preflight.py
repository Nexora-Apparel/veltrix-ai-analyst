from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "preflight_brazil_serie_b_history.py"
)
SPEC = importlib.util.spec_from_file_location("historical_preflight", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


def test_items_accepts_decoded_json_and_json_text() -> None:
    assert preflight._items(["522514093", "other"]) == {"522514093", "other"}
    assert preflight._items('["522514093"]') == {"522514093"}
    assert preflight._items("not-json") == set()
    assert preflight._items({"unexpected": "object"}) == set()


def test_preflight_fails_closed_when_secret_or_expected_database_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("VELTRIX_AI_ANALYST_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")

    def forbidden_connect(*args: object, **kwargs: object) -> None:
        pytest.fail("database connection must not be attempted without a URL")

    monkeypatch.setattr(preflight.psycopg, "connect", forbidden_connect)
    assert preflight.main() == 2
    assert "PREFLIGHT_FAILED:CONFIGURATION_MISSING_OR_INVALID" in capsys.readouterr().out


def test_preflight_rejects_neondb_uri_before_connecting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv(
        "VELTRIX_AI_ANALYST_DATABASE_URL",
        "postgresql://user:password@example.neon.tech/neondb?sslmode=require",
    )
    monkeypatch.setenv("EXPECTED_DATABASE_NAME", "veltrix_ai_analyst")

    def forbidden_connect(*args: object, **kwargs: object) -> None:
        pytest.fail("wrong database URI must be rejected before connecting")

    monkeypatch.setattr(preflight.psycopg, "connect", forbidden_connect)
    assert preflight.main() == 2
    assert "PREFLIGHT_FAILED:DATABASE_URL_TARGET_MISMATCH" in capsys.readouterr().out


def test_preflight_uses_registered_community_approval() -> None:
    assert preflight.APPROVAL_ID == "approval-5dollar-community-fixtures-2026-11-12"
