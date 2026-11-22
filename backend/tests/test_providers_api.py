from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.provider import ProviderCredential
from app.providers.base import ConnectionTestResult, DiscoveredModel


def test_provider_registry_returns_ten_providers(client: TestClient) -> None:
    resp = client.get("/api/v1/providers/registry")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    keys = {p["provider_key"] for p in providers}
    assert len(providers) == 10
    assert {
        "anthropic",
        "google_gemini",
        "openai",
        "deepseek",
        "grok",
        "mistral",
        "groq",
        "openrouter",
        "ollama",
        "custom_openai",
    } == keys


def test_provider_crud_and_encrypted_credentials_never_exposed(
    client: TestClient,
    db_session: Session,
) -> None:
    raw_secret = "sk-ant-test-secret-value-9942"
    create_resp = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "anthropic",
            "display_name": "My Claude Workspace",
            "api_key": raw_secret,
            "credential_name": "Primary Key",
            "default_model": "claude-3-7-sonnet-20250219",
        },
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    provider_id = data["id"]

    # Raw API key must NEVER appear in API response
    assert raw_secret not in create_resp.text
    assert len(data["credentials"]) == 1
    assert data["credentials"][0]["masked_api_key"] == "sk-****9942"
    assert data["default_model"] == "claude-3-7-sonnet-20250219"

    # Verify stored value in SQLite is encrypted, NOT plaintext
    stored_cred = db_session.execute(select(ProviderCredential)).scalar_one()
    assert stored_cred.encrypted_api_key != raw_secret
    assert raw_secret not in stored_cred.encrypted_api_key
    assert stored_cred.key_fingerprint == "sk-****9942"

    # Add second credential and rotate first
    add_cred = client.post(
        f"/api/v1/providers/{provider_id}/credentials",
        json={
            "credential_name": "Backup Key",
            "api_key": "sk-ant-backup-key-7711",
            "is_active": True,
        },
    )
    assert add_cred.status_code == 201
    assert "sk-ant-backup-key-7711" not in add_cred.text
    assert add_cred.json()["masked_api_key"] == "sk-****7711"
    cred2_id = add_cred.json()["id"]

    # Update credential
    rot_cred = client.put(
        f"/api/v1/providers/{provider_id}/credentials/{cred2_id}",
        json={"api_key": "sk-ant-rotated-key-5500", "credential_name": "Rotated Key"},
    )
    assert rot_cred.status_code == 200
    assert rot_cred.json()["masked_api_key"] == "sk-****5500"
    assert "sk-ant-rotated-key-5500" not in rot_cred.text

    # Delete credential
    del_cred = client.delete(f"/api/v1/providers/{provider_id}/credentials/{cred2_id}")
    assert del_cred.status_code == 204

    # Delete provider
    del_prov = client.delete(f"/api/v1/providers/{provider_id}")
    assert del_prov.status_code == 204
    assert client.get(f"/api/v1/providers/{provider_id}").status_code == 404


def test_provider_config_validation(client: TestClient) -> None:
    # Invalid Base URL
    bad_url = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "ollama",
            "display_name": "Bad Ollama",
            "base_url": "ftp://invalid-scheme",
        },
    )
    assert bad_url.status_code == 422

    # Custom OpenAI requires base_url
    missing_url = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "custom_openai",
            "display_name": "Custom Endpoint",
        },
    )
    assert missing_url.status_code == 422


def test_mocked_connection_test_and_model_management(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_resp = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "ollama",
            "display_name": "Local Ollama",
            "base_url": "http://127.0.0.1:11434",
        },
    )
    assert create_resp.status_code == 201
    provider_id = create_resp.json()["id"]

    # Mock Ollama adapter test_connection & list_models (no real network call)
    from app.providers.ollama import OllamaProvider

    monkeypatch.setattr(
        OllamaProvider,
        "test_connection",
        lambda self, base_url=None, api_key=None: ConnectionTestResult(
            success=True,
            status="connected",
            message="Connected to local Ollama runtime (2 local models installed).",
            latency_ms=14,
            models_found=2,
        ),
    )
    monkeypatch.setattr(
        OllamaProvider,
        "list_models",
        lambda self, base_url=None, api_key=None: [
            DiscoveredModel("llama3.2:latest", "llama3.2:latest", {"local": True}),
            DiscoveredModel("qwen2.5-coder:7b", "qwen2.5-coder:7b", {"local": True}),
        ],
    )

    # Test connection
    test_resp = client.post(f"/api/v1/providers/{provider_id}/test")
    assert test_resp.status_code == 200
    assert test_resp.json()["success"] is True
    assert test_resp.json()["connection_status"] == "connected"

    # Discover models
    models_resp = client.get(f"/api/v1/providers/{provider_id}/models?refresh=true")
    assert models_resp.status_code == 200
    model_ids = {m["model_id"] for m in models_resp.json()["models"]}
    assert model_ids == {"llama3.2:latest", "qwen2.5-coder:7b"}

    # Register manual model
    manual_resp = client.post(
        f"/api/v1/providers/{provider_id}/models",
        json={"model_id": "deepseek-r1:8b", "display_name": "DeepSeek R1 8B"},
    )
    assert manual_resp.status_code == 201
    manual_id = manual_resp.json()["id"]

    # Toggle model availability
    toggle_resp = client.put(
        f"/api/v1/providers/{provider_id}/models/{manual_id}",
        json={"is_available": False},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_available"] is False

    # Set default model
    default_resp = client.put(
        f"/api/v1/providers/{provider_id}/default-model",
        json={"model_id": "qwen2.5-coder:7b"},
    )
    assert default_resp.status_code == 200
    assert default_resp.json()["default_model"] == "qwen2.5-coder:7b"

    # Simulate connection failure
    monkeypatch.setattr(
        OllamaProvider,
        "test_connection",
        lambda self, base_url=None, api_key=None: ConnectionTestResult(
            success=False,
            status="error",
            message="Could not connect to Ollama (Local).",
            error_code="NETWORK_ERROR",
            latency_ms=5,
        ),
    )
    fail_resp = client.post(f"/api/v1/providers/{provider_id}/test")
    assert fail_resp.status_code == 200
    assert fail_resp.json()["success"] is False
    assert fail_resp.json()["connection_status"] == "error"
    assert fail_resp.json()["error_code"] == "NETWORK_ERROR"
