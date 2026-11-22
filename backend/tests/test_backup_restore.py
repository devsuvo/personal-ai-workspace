from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings


def test_backup_create_list_validate_and_restore(
    isolated_env: dict[str, object],
) -> None:
    client: TestClient = isolated_env["client"]  # type: ignore[assignment]
    settings: Settings = isolated_env["settings"]  # type: ignore[assignment]

    # 1. Persist a setting before backup
    assert client.put("/api/v1/settings/app_name", json={"value": "Before Backup"}).status_code == 200

    # 2. Create backup
    create_resp = client.post("/api/v1/system/backups")
    assert create_resp.status_code == 201
    backup_filename = create_resp.json()["backup"]["filename"]
    assert backup_filename.endswith(".db")

    # 3. List backups
    list_resp = client.get("/api/v1/system/backups")
    assert list_resp.status_code == 200
    filenames = [b["filename"] for b in list_resp.json()["backups"]]
    assert backup_filename in filenames

    # 4. Validate backup
    val_resp = client.post(f"/api/v1/system/backups/{backup_filename}/validate")
    assert val_resp.status_code == 200
    assert val_resp.json()["is_valid"] is True
    assert val_resp.json()["integrity_check"] == "ok"

    # 5. Modify database after backup
    assert client.put("/api/v1/settings/app_name", json={"value": "After Modification"}).status_code == 200
    assert client.get("/api/v1/settings/app_name").json()["value"] == "After Modification"

    # 6. Restore without confirmation must fail
    unconfirmed = client.post(
        f"/api/v1/system/backups/{backup_filename}/restore",
        json={"confirm": False},
    )
    assert unconfirmed.status_code == 400

    # 7. Restore with explicit confirmation recovers previous state
    restored = client.post(
        f"/api/v1/system/backups/{backup_filename}/restore",
        json={"confirm": True},
    )
    assert restored.status_code == 200
    assert restored.json()["database_connected"] is True
    assert restored.json()["pre_restore_backup"].startswith("pre_restore_")

    # Verify restored value
    after_restore = client.get("/api/v1/settings/app_name")
    assert after_restore.status_code == 200
    assert after_restore.json()["value"] == "Before Backup"

    # 8. Corrupted backup file fails validation
    corrupt_path: Path = settings.backups_dir_path / "corrupt_test.db"
    corrupt_path.write_text("not a sqlite file at all", encoding="utf-8")
    corrupt_val = client.post("/api/v1/system/backups/corrupt_test.db/validate")
    assert corrupt_val.status_code == 200
    assert corrupt_val.json()["is_valid"] is False
