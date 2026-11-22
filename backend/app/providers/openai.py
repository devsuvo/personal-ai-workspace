from app.providers.base import ProviderCapabilities, ProviderDescriptor
from app.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """Dedicated adapter for the official OpenAI API."""

    descriptor = ProviderDescriptor(
        id="openai",
        name="OpenAI",
        provider_type="openai",
        description="GPT and reasoning models via the official OpenAI API.",
        default_base_url="https://api.openai.com/v1",
        requires_api_key=True,
        is_local=False,
        allows_custom_base_url=True,
        supports_model_listing=True,
    )

    def __init__(self) -> None:
        super().__init__(descriptor=self.descriptor)

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_model_listing=True,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            requires_api_key=True,
            is_local=False,
            allows_custom_base_url=True,
        )
