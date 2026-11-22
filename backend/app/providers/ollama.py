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


class OllamaProvider(BaseAIProvider):
    """Dedicated local adapter for Ollama (no API key required by default)."""

    descriptor = ProviderDescriptor(
        id="ollama",
        name="Ollama (Local)",
        provider_type="ollama",
        description="Run local open-weight models directly on this machine via Ollama.",
        default_base_url="http://127.0.0.1:11434",
        requires_api_key=False,
        is_local=True,
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
        cleaned_key = api_key.strip() if api_key else None
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
            payload["options"] = {"temperature": request.temperature}
        return payload

    def list_models(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> list[DiscoveredModel]:
        normalized_url, key = self.validate_config(base_url, api_key)
        endpoint = f"{normalized_url}/api/tags"
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
        models: list[DiscoveredModel] = []
        for item in payload.get("models", []):
            model_id = str(item.get("name") or item.get("model") or "").strip()
            if not model_id:
                continue
            details = item.get("details") or {}
            models.append(
                DiscoveredModel(
                    model_id=model_id,
                    display_name=model_id,
                    capabilities={
                        "local": True,
                        "streaming": True,
                        "family": details.get("family"),
                        "parameter_size": details.get("parameter_size"),
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
            message=f"Connected to local Ollama runtime ({len(models)} local models installed).",
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
        endpoint = f"{normalized_url}/api/chat"
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
        content = str((data.get("message") or {}).get("content") or "")
        in_tok = data.get("prompt_eval_count")
        out_tok = data.get("eval_count")
        usage = (
            ChatUsage(input_tokens=in_tok, output_tokens=out_tok)
            if (isinstance(in_tok, int) or isinstance(out_tok, int))
            else None
        )
        return ChatResponse(
            content=content,
            model_id=str(data.get("model") or request.model_id),
            usage=usage,
            finish_reason=data.get("done_reason"),
        )

    async def stream_response(
        self,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        normalized_url, key = self.validate_config(base_url, api_key)
        endpoint = f"{normalized_url}/api/chat"

        try:
            async with httpx.AsyncClient(timeout=self.chat_timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers=self._headers(key),
                    json=self._build_payload(request, stream=True),
                ) as response:
                    if response.status_code != 200:
                        body = (await response.aread()).decode("utf-8", errors="ignore")
                        raise map_http_status_to_error(
                            response.status_code, self.descriptor.name, body[:400]
                        )

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        delta = str((event.get("message") or {}).get("content") or "")
                        usage = None
                        finish_reason = None
                        if event.get("done"):
                            in_tok = event.get("prompt_eval_count")
                            out_tok = event.get("eval_count")
                            if isinstance(in_tok, int) or isinstance(out_tok, int):
                                usage = ChatUsage(
                                    input_tokens=in_tok,
                                    output_tokens=out_tok,
                                )
                            finish_reason = event.get("done_reason") or "stop"

                        if delta or usage or finish_reason:
                            yield StreamChunk(
                                delta=delta,
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
            requires_api_key=False,
            is_local=True,
            allows_custom_base_url=True,
        )
