from fastapi.testclient import TestClient

from event_platform.main import app


def test_live_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

