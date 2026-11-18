from types import SimpleNamespace

import psycopg
from fastapi.testclient import TestClient

from app.main import app
from app.routes import readiness as readiness_module

client = TestClient(app)


class _Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _Connection:
    def __init__(self, row, database="veltrix_ai_analyst"):
        self.info = SimpleNamespace(dbname=database)
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, _query, _params):
        return _Result(self.row)


def test_readiness_fails_closed_when_database_url_is_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "not_configured"


def test_readiness_rejects_wrong_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    monkeypatch.setattr(
        readiness_module.psycopg,
        "connect",
        lambda _dsn: _Connection(None, database="other_database"),
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"] == "wrong_database"


def test_readiness_reports_pending_migrations(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    monkeypatch.setattr(
        readiness_module.psycopg,
        "connect",
        lambda _dsn: _Connection(("veltrix_ai_analyst", [], False, False)),
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["migrations"] == "pending"
    assert response.json()["checks"]["prediction_storage"] == "pending"


def test_readiness_reports_ready_only_when_all_v1_dependencies_exist(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    monkeypatch.setattr(
        readiness_module.psycopg,
        "connect",
        lambda _dsn: _Connection(
            (
                "veltrix_ai_analyst",
                list(readiness_module.REQUIRED_MIGRATIONS),
                True,
                True,
            )
        ),
    )

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_does_not_expose_database_errors(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")

    def fail(_dsn):
        raise psycopg.OperationalError("sensitive connection detail")

    monkeypatch.setattr(readiness_module.psycopg, "connect", fail)

    response = client.get("/ready")

    assert response.status_code == 503
    assert "sensitive connection detail" not in response.text
