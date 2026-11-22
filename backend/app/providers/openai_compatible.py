from collections.abc import AsyncIterator
import json
import time
from typing import Any

import httpx

from app.core.security import SecurityError, validate_base_url
from app.providers.base import (
    BaseAIProvider,
    ChatRequest,
    ChatResponse,
    ChatUsage,
    ConnectionTestResult,
    DiscoveredModel,
    ProviderAdapterError,
    ProviderCapabilities,
    ProviderDescriptor,
    StreamChunk,
    map_http_status_to_error,
    map_network_exception,
)


class OpenAICompatibleProvider(BaseAIProvider):
    """Reusable adapter for OpenAI & OpenAI-compatible APIs (DeepSeek, Grok, Mistral, Groq, OpenRouter, Custom)."""

    def __init__(self, descriptor: ProviderDescriptor) -> None:
        self.descriptor = descriptor

    def validate_config(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> tuple[str | None, str | None]:
        resolved_url = base_url or self.descriptor.default_base_url
        if not resolved_url:
            raise ProviderAdapterError(
                "INVALID_BASE_URL",
                f"{self.descriptor.name} requires a valid Base URL (e.g. https://api.example.com/v1).",
            )
        try:
            normalized_url = validate_base_url(resolved_url)
        except SecurityError as exc:
            raise ProviderAdapterError("INVALID_BASE_URL", str(exc)) from exc

        cleaned_key = api_key.strip() if api_key else None
        if self.descriptor.requires_api_key and not cleaned_key:
            raise ProviderAdapterError(
                "MISSING_API_KEY",
                f"{self.descriptor.name} requires an active API key.",
            )
        return normalized_url, cleaned_key

    def _headers(self, api_key: str | None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _build_payload(self, request: ChatRequest, stream: bool) -> dict[str, Any]:
        messages: list[dict[str, str]] = []
        if request.system_prompt.strip():
            messages.append({"role": "system", "content": request.system_prompt.strip()})
        for msg in request.messages:
            if msg.role in {"user", "assistant", "system"}:
                messages.append({"role": msg.role, "content": msg.content})

        payload: dict[str, Any] = {
            "model": request.model_id,
            "messages": messages,
            "stream": stream,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    def list_models(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> list[DiscoveredModel]:
        normalized_url, key = self.validate_config(base_url, api_key)
        endpoint = f"{normalized_url}/models"
        try:
            with httpx.Client(timeout=self.request_timeout_seconds) as client:
                response = client.get(endpoint, headers=self._headers(key))
        except httpx.HTTPError as exc:
            raise map_network_exception(exc, self.descriptor.name) from exc

        if response.status_code != 200:
            raise map_http_status_to_error(
                response.status_code, self.descriptor.name, response.text[:300]
            )

        payload = response.json()
        raw_items = payload.get("data", []) if isinstance(payload, dict) else []
        models: list[DiscoveredModel] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            display_name = str(item.get("name") or model_id)
            models.append(
                DiscoveredModel(
                    model_id=model_id,
                    display_name=display_name,
                    capabilities={"streaming": True},
                )
            )
        return models

    def test_connection(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ConnectionTestResult:
        started = time.perf_counter()
        try:
            models = self.list_models(base_url, api_key)
        except ProviderAdapterError as exc:
            return ConnectionTestResult(
                success=False,
                status="error",
                message=exc.message,
                error_code=exc.code,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        return ConnectionTestResult(
            success=True,
            status="connected",
            message=f"Connected to {self.descriptor.name} ({len(models)} models discovered).",
            latency_ms=latency_ms,
            models_found=len(models),
        )

    async def generate_response(
        self,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ChatResponse:
        normalized_url, key = self.validate_config(base_url, api_key)
        endpoint = f"{normalized_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.chat_timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    headers=self._headers(key),
                    json=self._build_payload(request, stream=False),
                )
        except httpx.HTTPError as exc:
            raise map_network_exception(exc, self.descriptor.name) from exc

        if response.status_code != 200:
            raise map_http_status_to_error(
                response.status_code, self.descriptor.name, response.text[:400]
            )

        data = response.json()
        choices = data.get("choices") or []
        content = ""
        finish_reason = None
        if choices and isinstance(choices[0], dict):
            content = str((choices[0].get("message") or {}).get("content") or "")
            finish_reason = choices[0].get("finish_reason")

        usage_raw = data.get("usage") or {}
        usage = None
        if usage_raw:
            usage = ChatUsage(
                input_tokens=usage_raw.get("prompt_tokens"),
                output_tokens=usage_raw.get("completion_tokens"),
                total_tokens=usage_raw.get("total_tokens"),
            )

        return ChatResponse(
            content=content,
            model_id=str(data.get("model") or request.model_id),
            usage=usage,
            finish_reason=finish_reason,
        )

    async def stream_response(
        self,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        normalized_url, key = self.validate_config(base_url, api_key)
        endpoint = f"{normalized_url}/chat/completions"
        payload = self._build_payload(request, stream=True)

        try:
            async with httpx.AsyncClient(timeout=self.chat_timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers=self._headers(key),
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = (await response.aread()).decode("utf-8", errors="ignore")
                        raise map_http_status_to_error(
                            response.status_code, self.descriptor.name, body[:400]
                        )

                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if not raw or raw == "[DONE]":
                            continue
                        try:
                            event = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        delta_text = ""
                        finish_reason = None
                        choices = event.get("choices") or []
                        if choices and isinstance(choices[0], dict):
                            delta_obj = choices[0].get("delta") or {}
                            if delta_obj.get("content"):
                                delta_text = str(delta_obj["content"])
                            finish_reason = choices[0].get("finish_reason")

                        usage_raw = event.get("usage") or {}
                        usage = None
                        if usage_raw:
                            usage = ChatUsage(
                                input_tokens=usage_raw.get("prompt_tokens"),
                                output_tokens=usage_raw.get("completion_tokens"),
                                total_tokens=usage_raw.get("total_tokens"),
                            )

                        if delta_text or usage or finish_reason:
                            yield StreamChunk(
                                delta=delta_text,
                                usage=usage,
                                finish_reason=finish_reason,
                            )
        except httpx.HTTPError as exc:
            raise map_network_exception(exc, self.descriptor.name) from exc

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_model_listing=self.descriptor.supports_model_listing,
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            requires_api_key=self.descriptor.requires_api_key,
            is_local=self.descriptor.is_local,
            allows_custom_base_url=self.descriptor.allows_custom_base_url,
        )
