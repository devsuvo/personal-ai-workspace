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


class GeminiProvider(BaseAIProvider):
    """Dedicated adapter for the Google Gemini Developer API (API key authentication)."""

    descriptor = ProviderDescriptor(
        id="google_gemini",
        name="Google Gemini",
        provider_type="gemini",
        description="Gemini models via the Google Gemini Developer API using an API key.",
        default_base_url="https://generativelanguage.googleapis.com",
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
                "Google Gemini Developer API requires an active API key.",
            )
        return normalized_url, api_key.strip()

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "x-goog-api-key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: ChatRequest) -> dict[str, Any]:
        contents: list[dict[str, Any]] = []
        for msg in request.messages:
            if msg.role not in {"user", "assistant"}:
                continue
            gemini_role = "model" if msg.role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": msg.content}]})

        payload: dict[str, Any] = {"contents": contents}
        if request.system_prompt.strip():
            payload["systemInstruction"] = {
                "parts": [{"text": request.system_prompt.strip()}]
            }

        gen_config: dict[str, Any] = {}
        if request.temperature is not None:
            gen_config["temperature"] = request.temperature
        if request.max_tokens is not None:
            gen_config["maxOutputTokens"] = request.max_tokens
        thinking = self._fast_thinking_config(request.model_id)
        if thinking:
            gen_config["thinkingConfig"] = thinking
        if gen_config:
            payload["generationConfig"] = gen_config
        return payload

    def list_models(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> list[DiscoveredModel]:
        normalized_url, key = self.validate_config(base_url, api_key)
        endpoint = f"{normalized_url}/v1beta/models"
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
        for item in payload.get("models", []):
            raw_name = str(item.get("name", "")).strip()
            if not raw_name:
                continue
            model_id = raw_name.removeprefix("models/")
            methods = item.get("supportedGenerationMethods") or []
            if methods and "generateContent" not in methods:
                continue
            models.append(
                DiscoveredModel(
                    model_id=model_id,
                    display_name=str(item.get("displayName") or model_id),
                    capabilities={
                        "streaming": "streamGenerateContent" in methods or True,
                        "input_token_limit": item.get("inputTokenLimit"),
                        "output_token_limit": item.get("outputTokenLimit"),
                    },
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
            message=f"Connected to Google Gemini Developer API ({len(models)} models available).",
            latency_ms=latency_ms,
            models_found=len(models),
        )

    @staticmethod
    def _fast_thinking_config(model_id: str) -> dict[str, Any] | None:
        """Flash models think a lot by default, which makes chat feel slow.

        Keep thinking low for flash models; leave pro models at their default.
        """
        mid = model_id.removeprefix("models/").lower()
        if "flash" not in mid or any(x in mid for x in ("image", "tts", "transcribe")):
            return None
        if mid.startswith("gemini-2.5"):
            return {"thinkingBudget": 0}
        return {"thinkingLevel": "low"}

    @staticmethod
    def _extract_text_and_usage(data: dict[str, Any]) -> tuple[str, ChatUsage | None, str | None]:
        candidates = data.get("candidates") or []
        text_parts: list[str] = []
        finish_reason: str | None = None
        if candidates and isinstance(candidates[0], dict):
            finish_reason = candidates[0].get("finishReason")
            content_obj = candidates[0].get("content") or {}
            for part in content_obj.get("parts") or []:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(str(part["text"]))

        usage_meta = data.get("usageMetadata") or {}
        usage = None
        if usage_meta:
            usage = ChatUsage(
                input_tokens=usage_meta.get("promptTokenCount"),
                output_tokens=usage_meta.get("candidatesTokenCount"),
                total_tokens=usage_meta.get("totalTokenCount"),
            )
        return "".join(text_parts), usage, finish_reason

    async def generate_response(
        self,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ChatResponse:
        normalized_url, key = self.validate_config(base_url, api_key)
        model_id = request.model_id.removeprefix("models/")
        endpoint = f"{normalized_url}/v1beta/models/{model_id}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=self.chat_timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    headers=self._headers(key or ""),
                    json=self._build_payload(request),
                )
        except httpx.HTTPError as exc:
            raise map_network_exception(exc, self.descriptor.name) from exc

        if response.status_code != 200:
            raise map_http_status_to_error(
                response.status_code, self.descriptor.name, response.text[:400]
            )

        text, usage, finish_reason = self._extract_text_and_usage(response.json())
        return ChatResponse(
            content=text,
            model_id=model_id,
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
        model_id = request.model_id.removeprefix("models/")
        endpoint = f"{normalized_url}/v1beta/models/{model_id}:streamGenerateContent?alt=sse"

        try:
            async with httpx.AsyncClient(timeout=self.chat_timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers=self._headers(key or ""),
                    json=self._build_payload(request),
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

                        text, usage, finish_reason = self._extract_text_and_usage(event)
                        if text or usage or finish_reason:
                            yield StreamChunk(
                                delta=text,
                                usage=usage,
                                finish_reason=finish_reason,
                            )
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
