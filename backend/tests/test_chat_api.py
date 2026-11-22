from collections.abc import AsyncIterator
import json

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.usage_log import UsageLog
from app.providers.base import (
    ChatRequest,
    ChatResponse,
    ChatUsage,
    ProviderAdapterError,
    StreamChunk,
)
from app.providers.ollama import OllamaProvider
from app.providers.openai import OpenAIProvider
from app.services.context_service import build_conversation_context


def _parse_sse(raw_text: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    for block in raw_text.strip().split("\n\n"):
        event_name = ""
        data_line = ""
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_line = line[5:].strip()
        if event_name and data_line:
            events.append((event_name, json.loads(data_line)))
    return events


def test_conversation_crud_and_search(client: TestClient) -> None:
    c1 = client.post("/api/v1/conversations", json={"title": "Python Architecture"}).json()
    c2 = client.post("/api/v1/conversations", json={"title": "React Styling"}).json()

    list_resp = client.get("/api/v1/conversations")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 2

    # Rename
    upd = client.put(f"/api/v1/conversations/{c1['id']}", json={"title": "FastAPI Architecture"})
    assert upd.status_code == 200
    assert upd.json()["title"] == "FastAPI Architecture"

    # Search by title
    search = client.get("/api/v1/conversations?search=FastAPI")
    assert search.status_code == 200
    assert search.json()["total"] == 1
    assert search.json()["conversations"][0]["id"] == c1["id"]

    # Delete
    assert client.delete(f"/api/v1/conversations/{c2['id']}").status_code == 204
    assert client.get("/api/v1/conversations").json()["total"] == 1


def test_non_streaming_chat_regeneration_and_usage_tracking(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_key = "sk-openai-never-leak-this-8821"
    prov = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "openai",
            "display_name": "OpenAI Test",
            "api_key": secret_key,
            "default_model": "gpt-4o-mini",
        },
    ).json()

    async def fake_generate(
        self: OpenAIProvider,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ChatResponse:
        assert api_key == secret_key
        return ChatResponse(
            content=f"Echo ({request.model_id}): {request.messages[-1].content}",
            model_id=request.model_id,
            usage=ChatUsage(input_tokens=15, output_tokens=25, total_tokens=40),
            finish_reason="stop",
        )

    monkeypatch.setattr(OpenAIProvider, "generate_response", fake_generate)

    conv = client.post("/api/v1/conversations", json={}).json()
    send_resp = client.post(
        f"/api/v1/conversations/{conv['id']}/messages",
        json={
            "content": "Explain SQLite WAL mode briefly",
            "provider_id": prov["id"],
            "model_id": "gpt-4o-mini",
        },
    )
    assert send_resp.status_code == 201
    assert secret_key not in send_resp.text
    body = send_resp.json()
    assert body["conversation"]["title"] == "Explain SQLite WAL mode briefly"
    assert body["assistant_message"]["content"] == "Echo (gpt-4o-mini): Explain SQLite WAL mode briefly"
    assert body["assistant_message"]["token_usage"]["total_tokens"] == 40

    # Verify usage log persisted
    logs = db_session.execute(select(UsageLog)).scalars().all()
    assert len(logs) == 1
    assert logs[0].input_tokens == 15
    assert logs[0].output_tokens == 25

    # Search by message content
    search_msg = client.get("/api/v1/conversations?search=WAL%20mode")
    assert search_msg.json()["total"] == 1

    # Regenerate assistant message
    assistant_id = body["assistant_message"]["id"]
    regen = client.post(
        f"/api/v1/messages/{assistant_id}/regenerate",
        json={"provider_id": prov["id"], "model_id": "gpt-4o-mini"},
    )
    assert regen.status_code == 200
    assert regen.json()["status"] == "completed"


def test_sse_streaming_events_and_error_preservation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prov = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "ollama",
            "display_name": "Local Ollama",
            "base_url": "http://127.0.0.1:11434",
            "default_model": "llama3.2",
        },
    ).json()

    async def fake_stream(
        self: OllamaProvider,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(delta="Hello ")
        yield StreamChunk(delta="local world!")
        yield StreamChunk(
            delta="",
            usage=ChatUsage(input_tokens=10, output_tokens=4),
            finish_reason="stop",
        )

    monkeypatch.setattr(OllamaProvider, "stream_response", fake_stream)

    resp = client.post(
        "/api/v1/chat/stream",
        json={
            "content": "Say hello",
            "provider_id": prov["id"],
            "model_id": "llama3.2",
        },
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    names = [name for name, _ in events]
    assert names[0] == "message_start"
    assert names.count("content_delta") == 2
    assert names[-1] == "message_complete"

    conv_id = events[0][1]["conversation_id"]
    final_msg = events[-1][1]["message"]
    assert final_msg["content"] == "Hello local world!"  # type: ignore[index]
    assert final_msg["token_usage"]["total_tokens"] == 14  # type: ignore[index]

    # Now simulate a provider error — existing messages MUST be preserved
    async def failing_stream(
        self: OllamaProvider,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        if False:
            yield StreamChunk()
        raise ProviderAdapterError("RATE_LIMITED", "Rate limit reached.", 429)

    monkeypatch.setattr(OllamaProvider, "stream_response", failing_stream)

    err_resp = client.post(
        "/api/v1/chat/stream",
        json={
            "conversation_id": conv_id,
            "content": "Second prompt",
            "provider_id": prov["id"],
            "model_id": "llama3.2",
        },
    )
    assert err_resp.status_code == 200
    err_events = _parse_sse(err_resp.text)
    assert err_events[-1][0] == "error"
    assert err_events[-1][1]["code"] == "RATE_LIMITED"

    # All 4 messages (previous 2 + new user + error assistant) exist in DB
    history = client.get(f"/api/v1/conversations/{conv_id}/messages").json()
    assert history["total"] == 4
    assert history["messages"][0]["content"] == "Say hello"
    assert history["messages"][2]["content"] == "Second prompt"
    assert history["messages"][3]["status"] == "error"


def test_streaming_cancellation_saves_stopped_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prov = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "ollama",
            "display_name": "Cancel Ollama",
            "base_url": "http://127.0.0.1:11434",
            "default_model": "llama3.2",
        },
    ).json()

    async def slow_stream(
        self: OllamaProvider,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        yield StreamChunk(delta="Part 1 ")
        yield StreamChunk(delta="Part 2")

    monkeypatch.setattr(OllamaProvider, "stream_response", slow_stream)

    # Simulate client disconnect after first chunk
    calls = {"n": 0}

    async def fake_is_disconnected(self: object) -> bool:
        calls["n"] += 1
        return calls["n"] >= 2

    from starlette.requests import Request as StarletteRequest

    monkeypatch.setattr(StarletteRequest, "is_disconnected", fake_is_disconnected)

    resp = client.post(
        "/api/v1/chat/stream",
        json={
            "content": "Stream and cancel",
            "provider_id": prov["id"],
            "model_id": "llama3.2",
        },
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    assert events[-1][0] == "generation_stopped"
    stopped_msg = events[-1][1]["message"]
    assert stopped_msg["status"] == "stopped"  # type: ignore[index]
    assert stopped_msg["content"] == "Part 1 "  # type: ignore[index]


def test_context_builder_truncates_old_messages_safely() -> None:
    history = [
        Message(conversation_id="c1", role="user", content="A" * 2500, status="completed"),
        Message(conversation_id="c1", role="assistant", content="B" * 2500, status="completed"),
        Message(conversation_id="c1", role="user", content="Latest question", status="completed"),
    ]
    result = build_conversation_context(
        history, system_prompt="", char_budget_override=4000
    )
    assert result.truncated is True
    assert result.excluded_count >= 1
    assert result.messages[-1].content == "Latest question"
