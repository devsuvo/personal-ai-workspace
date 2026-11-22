from fastapi.testclient import TestClient


def test_clear_local_data_requires_confirmation_and_creates_backup(
    client: TestClient,
) -> None:
    client.post("/api/v1/conversations", json={"title": "Temp Chat"})
    assert client.get("/api/v1/conversations").json()["total"] == 1

    # Unconfirmed clear must be rejected
    unconfirmed = client.post(
        "/api/v1/system/backups/clear-data",
        json={"confirm": False, "scope": "conversations"},
    )
    assert unconfirmed.status_code == 400
    assert client.get("/api/v1/conversations").json()["total"] == 1

    # Confirmed clear creates pre_clear safety backup and clears conversations
    confirmed = client.post(
        "/api/v1/system/backups/clear-data",
        json={"confirm": True, "scope": "conversations"},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["pre_clear_backup"].startswith("pre_clear_")
    assert client.get("/api/v1/conversations").json()["total"] == 0


def test_version_is_production_1_0_0(client: TestClient) -> None:
    info = client.get("/api/v1/system/info").json()
    assert info["version"] == "1.0.0"
    assert "v1.0.0" in info["phase"]
