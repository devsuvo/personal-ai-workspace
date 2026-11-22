import logging
import re
import sys

SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Common API key prefixes (OpenAI, Anthropic, Groq, xAI, Google Gemini, OpenRouter)
    (re.compile(r"\b(?:sk|gsk|xai|AIza|or)[-_A-Za-z0-9]{12,}\b"), "[REDACTED_KEY]"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-~+/]+=*", re.IGNORECASE), r"\1[REDACTED]"),
    # Generic key=value or key: value secrets
    (
        re.compile(
            r"((?:api[_-]?key|x-api-key|x-goog-api-key|secret|password|token|master[_-]?key)\s*[:=]\s*['\"]?)([^\s'\",;}{]+)",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]",
    ),
    # Fernet ciphertext tokens
    (re.compile(r"\b(gAAAAA[A-Za-z0-9_\-]{20,}=*)\b"), "[REDACTED_CIPHERTEXT]"),
)


def redact_secrets(text: str) -> str:
    """Mask potential API keys, tokens, and master keys in log messages."""
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


class SecretRedactingFilter(logging.Filter):
    """Logging filter preventing accidental secret leakage in console logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_secrets(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_secrets(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        return True


def configure_logging(log_level: str = "INFO") -> None:
    """Configure clean, secret-safe console logging for the backend."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(SecretRedactingFilter())

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[handler],
        force=True,
    )

    logging.getLogger("uvicorn.access").setLevel(level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
