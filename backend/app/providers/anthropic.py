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


class AnthropicProvider(BaseAIProvider):
    """Dedicated adapter for the Anthropic Claude Messages & Models API."""

    API_VERSION = "2023-06-01"
    DEFAULT_MAX_TOKENS = 4096

    descriptor = ProviderDescriptor(
        id="anthropic",
        name="Anthropic Claude",
        provider_type="anthropic",
        description="Claude models via the official Anthropic API.",
        default_base_url="https://api.anthropic.com",
        requires_api_key=True,
        is_local=False,
        allows_custom_base_url=True,
        supports_model_listing=True,
    )

    def validate_config(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> tuple[str | None, str | None]:
        resolved_url = base_url or self.descriptor.default_base_url
        try:
            normalized_url = validate_base_url(resolved_url or "")
        except SecurityError as exc:
            raise ProviderAdapterError("INVALID_BASE_URL", str(exc)) from exc

        if not api_key or not api_key.strip():
            raise ProviderAdapterError(
                "MISSING_API_KEY",
                "Anthropic Claude requires an active API key.",
            )
        return normalized_url, api_key.strip()

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": self.API_VERSION,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: ChatRequest, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model_id,
            "max_tokens": request.max_tokens or self.DEFAULT_MAX_TOKENS,
            "stream": stream,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
                if m.role in {"user", "assistant"}
            ],
        }
        if request.system_prompt.strip():
            payload["system"] = request.system_prompt.strip()
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        return payload

    def list_models(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> list[DiscoveredModel]:
        normalized_url, key = self.validate_config(base_url, api_key)
        endpoint = f"{normalized_url}/v1/models"
        try:
            with httpx.Client(timeout=self.request_timeout_seconds) as client:
                response = client.get(endpoint, headers=self._headers(key or ""))
        except httpx.HTTPError as exc:
            raise map_network_exception(exc, self.descriptor.name) from exc

        if response.status_code != 200:
            raise map_http_status_to_error(
                response.status_code, self.descriptor.name, response.text[:300]
            )

        payload = response.json()
        models: list[DiscoveredModel] = []
        for item in payload.get("data", []):
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            models.append(
                DiscoveredModel(
                    model_id=model_id,
                    display_name=str(item.get("display_name") or model_id),
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
            message=f"Connected to Anthropic API ({len(models)} models available).",
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
        endpoint = f"{normalized_url}/v1/messages"
        try:
            async with httpx.AsyncClient(timeout=self.chat_timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    headers=self._headers(key or ""),
                    json=self._build_payload(request, stream=False),
                )
        except httpx.HTTPError as exc:
            raise map_network_exception(exc, self.descriptor.name) from exc

        if response.status_code != 200:
            raise map_http_status_to_error(
                response.status_code, self.descriptor.name, response.text[:400]
            )

        data = response.json()
        parts = [
            str(block.get("text", ""))
            for block in data.get("content", [])
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        usage_raw = data.get("usage") or {}
        usage = None
        if usage_raw:
            in_tok = usage_raw.get("input_tokens")
            out_tok = usage_raw.get("output_tokens")
            usage = ChatUsage(input_tokens=in_tok, output_tokens=out_tok)

        return ChatResponse(
            content="".join(parts),
            model_id=str(data.get("model") or request.model_id),
            usage=usage,
            finish_reason=data.get("stop_reason"),
        )

    async def stream_response(
        self,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        normalized_url, key = self.validate_config(base_url, api_key)
        endpoint = f"{normalized_url}/v1/messages"
        input_tokens: int | None = None
        output_tokens: int | None = None

        try:
            async with httpx.AsyncClient(timeout=self.chat_timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers=self._headers(key or ""),
                    json=self._build_payload(request, stream=True),
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

                        event_type = event.get("type")
                        if event_type == "message_start":
                            msg_usage = (event.get("message") or {}).get("usage") or {}
                            if isinstance(msg_usage.get("input_tokens"), int):
                                input_tokens = msg_usage["input_tokens"]
                        elif event_type == "content_block_delta":
                            delta_obj = event.get("delta") or {}
                            text = delta_obj.get("text")
                            if text:
                                yield StreamChunk(delta=str(text))
                        elif event_type == "message_delta":
                            delta_usage = event.get("usage") or {}
                            if isinstance(delta_usage.get("output_tokens"), int):
                                output_tokens = delta_usage["output_tokens"]
                            stop_reason = (event.get("delta") or {}).get("stop_reason")
                            usage = (
                                ChatUsage(
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                )
                                if (input_tokens is not None or output_tokens is not None)
                                else None
                            )
                            yield StreamChunk(
                                delta="",
                                usage=usage,
                                finish_reason=stop_reason,
                            )
                        elif event_type == "error":
                            err_msg = (event.get("error") or {}).get(
                                "message", "Anthropic streaming error."
                            )
                            raise ProviderAdapterError("STREAM_ERROR", str(err_msg), 502)
        except httpx.HTTPError as exc:
            raise map_network_exception(exc, self.descriptor.name) from exc

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
