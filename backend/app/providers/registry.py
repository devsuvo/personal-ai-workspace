from app.providers.anthropic import AnthropicProvider
from app.providers.base import (
    BaseAIProvider,
    ProviderAdapterError,
    ProviderDescriptor,
)
from app.providers.gemini import GeminiProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai import OpenAIProvider
from app.providers.openai_compatible import OpenAICompatibleProvider

PROVIDER_CATALOG: tuple[ProviderDescriptor, ...] = (
    AnthropicProvider.descriptor,
    GeminiProvider.descriptor,
    OpenAIProvider.descriptor,
    ProviderDescriptor(
        id="deepseek",
        name="DeepSeek",
        provider_type="openai_compatible",
        description="DeepSeek chat and reasoning models via OpenAI-compatible API.",
        default_base_url="https://api.deepseek.com/v1",
        requires_api_key=True,
        is_local=False,
        allows_custom_base_url=True,
        supports_model_listing=True,
    ),
    ProviderDescriptor(
        id="grok",
        name="xAI Grok",
        provider_type="openai_compatible",
        description="Grok models via the xAI OpenAI-compatible API.",
        default_base_url="https://api.x.ai/v1",
        requires_api_key=True,
        is_local=False,
        allows_custom_base_url=True,
        supports_model_listing=True,
    ),
    ProviderDescriptor(
        id="mistral",
        name="Mistral AI",
        provider_type="openai_compatible",
        description="Mistral AI models via the Mistral OpenAI-compatible API.",
        default_base_url="https://api.mistral.ai/v1",
        requires_api_key=True,
        is_local=False,
        allows_custom_base_url=True,
        supports_model_listing=True,
    ),
    ProviderDescriptor(
        id="groq",
        name="Groq",
        provider_type="openai_compatible",
        description="Low-latency open-weight models via the Groq API.",
        default_base_url="https://api.groq.com/openai/v1",
        requires_api_key=True,
        is_local=False,
        allows_custom_base_url=True,
        supports_model_listing=True,
    ),
    ProviderDescriptor(
        id="openrouter",
        name="OpenRouter",
        provider_type="openai_compatible",
        description="Unified gateway to hosted models via OpenRouter.",
        default_base_url="https://openrouter.ai/api/v1",
        requires_api_key=True,
        is_local=False,
        allows_custom_base_url=True,
        supports_model_listing=True,
    ),
    OllamaProvider.descriptor,
    ProviderDescriptor(
        id="custom_openai",
        name="Custom OpenAI-Compatible API",
        provider_type="openai_compatible",
        description="Connect any self-hosted or third-party OpenAI-compatible endpoint.",
        default_base_url=None,
        requires_api_key=False,
        is_local=False,
        allows_custom_base_url=True,
        supports_model_listing=True,
    ),
)

_DESCRIPTOR_BY_ID: dict[str, ProviderDescriptor] = {
    item.id: item for item in PROVIDER_CATALOG
}


def list_planned_providers() -> list[ProviderDescriptor]:
    """Return the full catalog of supported AI providers."""
    return list(PROVIDER_CATALOG)


def get_provider_descriptor(provider_key: str) -> ProviderDescriptor:
    """Look up a supported provider descriptor by key."""
    descriptor = _DESCRIPTOR_BY_ID.get(provider_key)
    if not descriptor:
        raise ProviderAdapterError(
            code="UNSUPPORTED_PROVIDER",
            message=f"Unsupported provider '{provider_key}'.",
            status_code=400,
        )
    return descriptor


def get_provider_adapter(provider_key: str) -> BaseAIProvider:
    """Instantiate the dedicated adapter for the given provider key."""
    descriptor = get_provider_descriptor(provider_key)
    if descriptor.id == "anthropic":
        return AnthropicProvider()
    if descriptor.id == "google_gemini":
        return GeminiProvider()
    if descriptor.id == "openai":
        return OpenAIProvider()
    if descriptor.id == "ollama":
        return OllamaProvider()
    return OpenAICompatibleProvider(descriptor=descriptor)
