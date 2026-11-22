from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "Personal AI Workspace"
    assert data["configured_providers"] == 0
    assert data["checks"]["database"]["status"] == "ok"
    assert data["checks"]["storage"]["status"] == "ok"
    assert data["uptime_seconds"] >= 0


def test_not_found_returns_structured_error(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "HTTP_404"
    assert isinstance(data["error"]["message"], str)
