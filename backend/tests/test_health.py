from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_liveness_payload() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "veltrix-ai-analyst-api",
        "version": "0.1.0",
    }


def test_root_points_to_api_docs() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"
