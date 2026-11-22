from fastapi.testclient import TestClient


def test_system_info_returns_expected_state(client: TestClient) -> None:
    response = client.get("/api/v1/system/info")

    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "Personal AI Workspace"
    assert data["local_only"] is True
    assert data["api_prefix"] == "/api/v1"
    assert data["configured_providers_count"] == 0
    assert data["planned_providers_count"] == 10
    assert data["storage"]["database_connected"] is True
    assert len(data["planned_providers"]) == 10


def test_database_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/system/database")

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["database_type"] == "SQLite"
    assert data["database_size_bytes"] > 0
    assert data["table_count"] >= 9
    assert data["migration_status"]["is_up_to_date"] is True
    assert data["migration_status"]["current_revision"] == "0006_productivity_prompts_analytics"
    # Should not leak full OS drive/user paths
    assert ":\\" not in data["relative_location"]


def test_security_status_endpoint_never_exposes_key(client: TestClient) -> None:
    response = client.get("/api/v1/system/security")

    assert response.status_code == 200
    data = response.json()
    assert "Fernet" in data["encryption_algorithm"]
    assert data["secrets_stored_outside_database"] is True
    assert "master_key" not in str(data).lower() or "master.key" in str(data).lower()
    assert "gAAAAA" not in str(data)


def test_cors_allows_local_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
