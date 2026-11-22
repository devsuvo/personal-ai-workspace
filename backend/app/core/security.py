from collections.abc import Callable
import logging
import os
from pathlib import Path
import re
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken

try:
    import keyring
    from keyring.errors import KeyringError
except Exception:  # pragma: no cover
    keyring = None  # type: ignore[assignment]
    KeyringError = Exception  # type: ignore[misc, assignment]

from app.core.config import Settings, get_settings

logger = logging.getLogger("workspace.security")

KEYRING_SERVICE_NAME = "PersonalAIWorkspace"
KEYRING_USERNAME = "fernet_master_key"

FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._\-]")


class SecurityError(Exception):
    """Base exception for local security errors."""


class PathValidationError(SecurityError):
    """Raised when a file path fails traversal or safety validation."""


class MasterKeyError(SecurityError):
    """Base error for encryption master key issues."""


class MasterKeyExistsError(MasterKeyError):
    """Raised when attempting to regenerate an existing master key."""


class MasterKeyMissingError(MasterKeyError):
    """Raised when a master key is missing while encrypted data exists."""


class EncryptionOperationError(SecurityError):
    """Raised when encryption or decryption fails safely."""


def mask_api_key(api_key: str) -> str:
    """Return a safe masked representation of an API key (e.g. sk-****abcd)."""
    stripped = api_key.strip()
    if len(stripped) <= 4:
        return "****"
    last_four = stripped[-4:]
    if "-" in stripped[:8]:
        prefix = stripped.split("-", 1)[0]
        if 1 <= len(prefix) <= 6:
            return f"{prefix}-****{last_four}"
    return f"****{last_four}"


def validate_base_url(url: str) -> str:
    """Validate that a provider base URL uses http(s) and includes a host."""
    cleaned = url.strip().rstrip("/")
    if not cleaned:
        raise SecurityError("Base URL cannot be empty.")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SecurityError(
            "Base URL must be a valid http:// or https:// URL including a hostname."
        )
    return cleaned


def sanitize_filename(filename: str) -> str:
    """Normalize an untrusted filename to a safe single-segment basename."""
    if not filename or "\x00" in filename:
        raise PathValidationError("Filename is empty or contains null bytes.")

    basename = filename.replace("\\", "/").split("/")[-1].strip()
    if basename in {"", ".", ".."}:
        raise PathValidationError("Invalid filename.")

    cleaned = FILENAME_SAFE_PATTERN.sub("_", basename)
    if not cleaned or cleaned in {".", ".."}:
        raise PathValidationError("Filename contains no valid characters.")

    return cleaned[:180]


def validate_safe_path(base_dir: Path, target: str | Path) -> Path:
    """Resolve `target` inside `base_dir` and block directory traversal."""
    if isinstance(target, str) and ("\x00" in target or not target.strip()):
        raise PathValidationError("Target path is empty or contains null bytes.")

    base_resolved = base_dir.resolve()
    target_path = Path(target)
    if target_path.is_absolute():
        candidate = target_path.resolve()
    else:
        candidate = (base_resolved / target_path).resolve()

    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise PathValidationError(
            "Requested file path escapes the allowed local storage directory."
        ) from exc

    return candidate


class EncryptionService:
    """Authenticated local encryption service built on Fernet (AES-128-CBC + HMAC-SHA256).

    Design guarantees:
    - Master key is stored outside the SQLite database (env var or local key file).
    - Master key is never returned by any API endpoint or logged.
    - Master key is never automatically regenerated if a key file already exists
      or if encrypted credentials already exist.
    """

    ALGORITHM = "Fernet (AES-128-CBC + HMAC-SHA256)"

    def __init__(
        self,
        key_file_path: Path | None = None,
        env_master_key: str | None = None,
        has_encrypted_data_check: Callable[[], bool] | None = None,
    ) -> None:
        settings = get_settings()
        self._key_file_path = (key_file_path or settings.master_key_path).resolve()
        self._env_master_key = (
            env_master_key
            if env_master_key is not None
            else settings.encryption_master_key
        ).strip()
        self._has_encrypted_data_check = has_encrypted_data_check

    @property
    def key_file_path(self) -> Path:
        return self._key_file_path

    def _validate_fernet_key(self, raw_key: bytes) -> Fernet:
        try:
            return Fernet(raw_key)
        except Exception as exc:
            raise MasterKeyError(
                "Configured encryption master key is not a valid Fernet key."
            ) from exc

    def is_key_initialized(self) -> bool:
        if self._env_master_key:
            return True
        return self._key_file_path.exists() and self._key_file_path.is_file()

    def get_key_source(self) -> str:
        if self._env_master_key:
            return "environment"
        if self._key_file_path.exists():
            return "key_file"
        return "not_initialized"

    def initialize_key(self) -> bool:
        """Generate and store a new master key file if none exists.

        Returns True if a new key was created, False if an existing key is already
        configured via environment variable or key file.
        Refuses to generate a new key if encrypted credentials already exist without a key.
        """
        if self._env_master_key:
            self._validate_fernet_key(self._env_master_key.encode("utf-8"))
            return False

        if self._key_file_path.exists():
            return False

        if self._has_encrypted_data_check and self._has_encrypted_data_check():
            raise MasterKeyMissingError(
                "Encrypted credentials exist in the database, but the local master key "
                "file is missing. Restore your backed-up master.key file instead of "
                "generating a new key."
            )

        self._key_file_path.parent.mkdir(parents=True, exist_ok=True)
        new_key = Fernet.generate_key()

        try:
            with open(self._key_file_path, "xb") as key_file:
                key_file.write(new_key)
        except FileExistsError as exc:
            raise MasterKeyExistsError(
                "Master key file already exists and will not be overwritten."
            ) from exc

        if os.name != "nt":
            try:
                os.chmod(self._key_file_path, 0o600)
            except OSError:
                logger.warning("Could not apply 0600 permissions to master key file.")

        logger.info("Initialized local encryption master key outside SQLite database.")
        return True

    def _load_fernet(self, auto_initialize: bool = False) -> Fernet:
        if self._env_master_key:
            return self._validate_fernet_key(self._env_master_key.encode("utf-8"))

        if not self._key_file_path.exists():
            if auto_initialize:
                self.initialize_key()
            else:
                raise MasterKeyMissingError(
                    "Local encryption master key is missing or not initialized."
                )

        raw_key = self._key_file_path.read_bytes().strip()
        return self._validate_fernet_key(raw_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a UTF-8 string and return a URL-safe base64 ciphertext string."""
        if not isinstance(plaintext, str):
            raise EncryptionOperationError("Plaintext must be a string.")
        fernet = self._load_fernet(auto_initialize=True)
        try:
            token = fernet.encrypt(plaintext.encode("utf-8"))
            return token.decode("utf-8")
        except Exception as exc:
            raise EncryptionOperationError("Failed to encrypt secret payload.") from exc

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a Fernet ciphertext string back to UTF-8 plaintext."""
        if not isinstance(ciphertext, str) or not ciphertext.strip():
            raise EncryptionOperationError("Ciphertext must be a non-empty string.")
        fernet = self._load_fernet(auto_initialize=False)
        try:
            plaintext_bytes = fernet.decrypt(ciphertext.encode("utf-8"))
            return plaintext_bytes.decode("utf-8")
        except InvalidToken as exc:
            raise EncryptionOperationError(
                "Decryption failed: invalid ciphertext or mismatched master key."
            ) from exc
        except Exception as exc:
            raise EncryptionOperationError("Failed to decrypt secret payload.") from exc

    def get_status(self, settings: Settings | None = None) -> dict[str, object]:
        """Return safe, non-sensitive encryption status metadata."""
        cfg = settings or get_settings()
        os_keyring_ready = keyring is not None
        return {
            "encryption_algorithm": self.ALGORITHM,
            "master_key_initialized": self.is_key_initialized(),
            "key_source": self.get_key_source(),
            "key_storage_location": cfg.relative_storage_label(self._key_file_path),
            "secrets_stored_outside_database": True,
            "credential_management_status": (
                "Active (Fernet encryption + OS Keyring support ready)"
                if os_keyring_ready
                else "Active (Fernet encryption with local key file)"
            ),
            "backup_guidance": (
                "Keep a secure offline copy of storage/secrets/master.key (or your "
                "ENCRYPTION_MASTER_KEY). Never commit it to Git. If lost, previously "
                "encrypted API credentials cannot be decrypted."
            ),
        }


def get_encryption_service(
    has_encrypted_data_check: Callable[[], bool] | None = None,
) -> EncryptionService:
    """Factory returning an EncryptionService bound to current application settings."""
    settings = get_settings()
    return EncryptionService(
        key_file_path=settings.master_key_path,
        env_master_key=settings.encryption_master_key,
        has_encrypted_data_check=has_encrypted_data_check,
    )
