from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import httpx


class ProviderAdapterError(Exception):
    """Safe, structured error raised by provider adapters (never includes secrets)."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_model_listing: bool = True
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    requires_api_key: bool = True
    is_local: bool = False
    allows_custom_base_url: bool = False


@dataclass(frozen=True)
class ProviderDescriptor:
    """Static catalog descriptor for a supported AI provider."""

    id: str
    name: str
    provider_type: str
    description: str
    default_base_url: str | None
    requires_api_key: bool
    is_local: bool
    allows_custom_base_url: bool
    supports_model_listing: bool = True
    configured: bool = False
    implemented: bool = True


@dataclass(frozen=True)
class DiscoveredModel:
    model_id: str
    display_name: str
    capabilities: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectionTestResult:
    success: bool
    status: str  # "connected" | "error"
    message: str
    error_code: str | None = None
    latency_ms: int | None = None
    models_found: int | None = None


@dataclass(frozen=True)
class ChatMessageInput:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass(frozen=True)
class ChatRequest:
    model_id: str
    messages: list[ChatMessageInput]
    system_prompt: str = ""
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ChatUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    def to_dict(self) -> dict[str, int] | None:
        data: dict[str, int] = {}
        if self.input_tokens is not None:
            data["input_tokens"] = self.input_tokens
        if self.output_tokens is not None:
            data["output_tokens"] = self.output_tokens
        if self.total_tokens is not None:
            data["total_tokens"] = self.total_tokens
        elif self.input_tokens is not None and self.output_tokens is not None:
            data["total_tokens"] = self.input_tokens + self.output_tokens
        return data or None


@dataclass(frozen=True)
class ChatResponse:
    content: str
    model_id: str
    usage: ChatUsage | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class StreamChunk:
    delta: str = ""
    usage: ChatUsage | None = None
    finish_reason: str | None = None


def map_http_status_to_error(
    status_code: int,
    provider_name: str,
    body_text: str = "",
) -> ProviderAdapterError:
    """Map upstream provider HTTP status codes to safe, user-friendly errors."""
    lower = body_text.lower()
    if status_code in (401, 403):
        return ProviderAdapterError(
            code="INVALID_API_KEY",
            message=f"{provider_name} rejected the API key. Verify the key is valid and active.",
            status_code=400,
        )
    if status_code == 402 or "insufficient_quota" in lower or "credit" in lower or "billing" in lower:
        return ProviderAdapterError(
            code="INSUFFICIENT_CREDITS",
            message=f"{provider_name} reported insufficient credits or quota for this API key.",
            status_code=400,
        )
    if status_code == 429:
        return ProviderAdapterError(
            code="RATE_LIMITED",
            message=f"{provider_name} rate limit reached. Wait a moment and try again.",
            status_code=429,
        )
    if (
        "context_length" in lower
        or "maximum context" in lower
        or "too many tokens" in lower
        or "prompt is too long" in lower
    ):
        return ProviderAdapterError(
            code="CONTEXT_LENGTH_EXCEEDED",
            message=f"{provider_name} rejected the request because the conversation exceeded the model's context length.",
            status_code=400,
        )
    if status_code == 404 or "model_not_found" in lower or "not found for api version" in lower:
        return ProviderAdapterError(
            code="UNSUPPORTED_MODEL",
            message=f"{provider_name} reported the requested model or endpoint is unavailable. Select another model.",
            status_code=400,
        )
    if status_code >= 500:
        return ProviderAdapterError(
            code="SERVICE_UNAVAILABLE",
            message=f"{provider_name} service is currently unavailable (HTTP {status_code}).",
            status_code=503,
        )
    return ProviderAdapterError(
        code="PROVIDER_REQUEST_FAILED",
        message=f"{provider_name} returned HTTP {status_code}. Verify your model and configuration.",
        status_code=400,
    )


def map_network_exception(exc: Exception, provider_name: str) -> ProviderAdapterError:
    """Map httpx network/timeout exceptions to safe error responses."""
    if isinstance(exc, httpx.TimeoutException):
        return ProviderAdapterError(
            code="NETWORK_TIMEOUT",
            message=f"Connection to {provider_name} timed out. Check network connectivity and Base URL.",
            status_code=504,
        )
    return ProviderAdapterError(
        code="NETWORK_ERROR",
        message=f"Could not connect to {provider_name}. Verify the server is reachable and Base URL is correct.",
        status_code=502,
    )


class BaseAIProvider(ABC):
    """Common interface for all AI provider adapters."""

    descriptor: ProviderDescriptor
    request_timeout_seconds: float = 15.0
    chat_timeout_seconds: float = 120.0

    @abstractmethod
    def validate_config(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Validate and normalize (base_url, api_key). Raises ProviderAdapterError if invalid."""

    @abstractmethod
    def test_connection(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ConnectionTestResult:
        """Perform a lightweight, zero-generation connection & authentication test."""

    @abstractmethod
    def list_models(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> list[DiscoveredModel]:
        """Return available models if supported by the provider, or raise ProviderAdapterError."""

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Return known static capabilities of this provider adapter."""

    def supports_streaming(self) -> bool:
        return self.get_capabilities().supports_streaming

    def get_model_capabilities(self, _model_id: str) -> dict[str, Any]:
        caps = self.get_capabilities()
        return {
            "streaming": caps.supports_streaming,
            "tools": caps.supports_tools,
            "vision": caps.supports_vision,
        }

    def count_tokens(
        self,
        _messages: list[ChatMessageInput],
        _model_id: str,
    ) -> int | None:
        """Optional token counter. Returns None unless exact measurement is available."""
        return None

    @abstractmethod
    async def generate_response(
        self,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ChatResponse:
        """Send a non-streaming chat completion request and return normalized output."""

    @abstractmethod
    async def stream_response(
        self,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream normalized text deltas and optional usage metadata from the provider."""
        if False:  # pragma: no cover
            yield StreamChunk()
