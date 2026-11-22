from pathlib import Path

import pytest

from app.core.logging import redact_secrets
from app.core.security import (
    EncryptionOperationError,
    EncryptionService,
    MasterKeyMissingError,
    PathValidationError,
    mask_api_key,
    sanitize_filename,
    validate_safe_path,
)


def test_encryption_roundtrip_and_key_file_outside_db(tmp_path: Path) -> None:
    key_file = tmp_path / "secrets" / "master.key"
    service = EncryptionService(key_file_path=key_file, env_master_key="")

    assert service.is_key_initialized() is False
    ciphertext = service.encrypt("sk-test-super-secret-key-9876")
    assert key_file.exists()
    assert ciphertext != "sk-test-super-secret-key-9876"
    assert "9876" not in ciphertext

    decrypted = service.decrypt(ciphertext)
    assert decrypted == "sk-test-super-secret-key-9876"


def test_encryption_refuses_regeneration_when_encrypted_data_exists(tmp_path: Path) -> None:
    missing_key_file = tmp_path / "secrets" / "missing.key"
    service = EncryptionService(
        key_file_path=missing_key_file,
        env_master_key="",
        has_encrypted_data_check=lambda: True,
    )

    with pytest.raises(MasterKeyMissingError):
        service.initialize_key()

    assert not missing_key_file.exists()


def test_decryption_fails_with_different_master_key(tmp_path: Path) -> None:
    svc_a = EncryptionService(key_file_path=tmp_path / "key_a.key", env_master_key="")
    svc_b = EncryptionService(key_file_path=tmp_path / "key_b.key", env_master_key="")
    svc_b.initialize_key()

    token = svc_a.encrypt("secret-payload")
    with pytest.raises(EncryptionOperationError):
        svc_b.decrypt(token)


def test_path_validation_blocks_traversal(tmp_path: Path) -> None:
    base = tmp_path / "uploads"
    base.mkdir()

    safe = validate_safe_path(base, "notes.txt")
    assert safe == (base / "notes.txt").resolve()

    with pytest.raises(PathValidationError):
        validate_safe_path(base, "../secrets/master.key")

    assert sanitize_filename("../../evil file!.txt") == "evil_file_.txt"


def test_mask_api_key_and_log_redaction() -> None:
    assert mask_api_key("sk-ant-api03-abcdef1234") == "sk-****1234"
    assert mask_api_key("AIzaSyDummyKeyValue9988") == "****9988"
    assert mask_api_key("123") == "****"

    sample = "Failed calling endpoint with Authorization: Bearer sk-test1234567890abcdef and api_key=mysecretvalue"
    redacted = redact_secrets(sample)
    assert "sk-test1234567890abcdef" not in redacted
    assert "mysecretvalue" not in redacted
