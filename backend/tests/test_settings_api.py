from fastapi.testclient import TestClient


def test_list_settings_returns_defaults(client: TestClient) -> None:
    response = client.get("/api/v1/settings")
    assert response.status_code == 200
    items = response.json()["settings"]
    by_key = {item["key"]: item for item in items}

    assert by_key["app_name"]["value"] == "Personal AI Workspace"
    assert by_key["theme"]["value"] == "light"
    assert by_key["max_upload_size_mb"]["value"] == 25
    assert by_key["theme"]["is_custom"] is False


def test_put_get_delete_setting_lifecycle(client: TestClient) -> None:
    put_resp = client.put("/api/v1/settings/theme", json={"value": "dark"})
    assert put_resp.status_code == 200
    assert put_resp.json()["value"] == "dark"
    assert put_resp.json()["is_custom"] is True

    get_resp = client.get("/api/v1/settings/theme")
    assert get_resp.status_code == 200
    assert get_resp.json()["value"] == "dark"

    del_resp = client.delete("/api/v1/settings/theme")
    assert del_resp.status_code == 200
    assert del_resp.json()["reset_to_default"] is True
    assert del_resp.json()["default_value"] == "light"

    after_resp = client.get("/api/v1/settings/theme")
    assert after_resp.json()["value"] == "light"
    assert after_resp.json()["is_custom"] is False


def test_invalid_setting_values_and_keys_rejected(client: TestClient) -> None:
    # Invalid enum
    resp_enum = client.put("/api/v1/settings/theme", json={"value": "neon-pink"})
    assert resp_enum.status_code == 422

    # Out-of-range integer
    resp_int = client.put("/api/v1/settings/max_upload_size_mb", json={"value": 9999})
    assert resp_int.status_code == 422

    # Wrong type
    resp_bool = client.put("/api/v1/settings/chat_send_on_enter", json={"value": "yes"})
    assert resp_bool.status_code == 422

    # Unknown key
    resp_unknown = client.get("/api/v1/settings/non_existent_setting")
    assert resp_unknown.status_code == 404

    # Secret-like key explicitly blocked
    resp_secret = client.put("/api/v1/settings/openai_api_key", json={"value": "sk-secret123456789"})
    assert resp_secret.status_code == 400
