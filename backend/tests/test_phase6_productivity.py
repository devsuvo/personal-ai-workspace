from fastapi.testclient import TestClient
import pytest

from app.providers.base import ChatRequest, ChatResponse, ChatUsage
from app.providers.ollama import OllamaProvider


def test_ai_tools_catalog_and_execution(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    list_resp = client.get("/api/v1/tools")
    assert list_resp.status_code == 200
    tool_ids = {t["id"] for t in list_resp.json()["tools"]}
    assert {
        "summarizer",
        "rewriter",
        "grammar",
        "translator",
        "code_explainer",
        "code_generator",
        "content_generator",
        "email_writer",
        "custom_runner",
    } == tool_ids

    prov = client.post(
        "/api/v1/providers",
        json={
            "provider_key": "ollama",
            "display_name": "Local Ollama",
            "base_url": "http://127.0.0.1:11434",
            "default_model": "llama3.2",
        },
    ).json()

    async def fake_generate(
        self: OllamaProvider,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ChatResponse:
        return ChatResponse(
            content="- Concise summary bullet",
            model_id=request.model_id,
            usage=ChatUsage(input_tokens=100, output_tokens=20, total_tokens=120),
        )

    monkeypatch.setattr(OllamaProvider, "generate_response", fake_generate)

    run_resp = client.post(
        "/api/v1/tools/run",
        json={
            "tool_id": "summarizer",
            "input_text": "Long report text about local-first AI architecture.",
            "provider_id": prov["id"],
            "model_id": "llama3.2",
            "options": {"format": "Bullet Points"},
        },
    )
    assert run_resp.status_code == 200
    assert run_resp.json()["output"] == "- Concise summary bullet"
    assert run_resp.json()["token_usage"]["total_tokens"] == 120


def test_prompt_library_crud_favorites_and_search(client: TestClient) -> None:
    created = client.post(
        "/api/v1/prompts",
        json={
            "title": "Code Review Checklist",
            "category": "Coding",
            "description": "Thorough architecture review",
            "content": "Review this diff for bugs, security issues, and clarity.",
            "is_favorite": True,
        },
    )
    assert created.status_code == 201
    pid = created.json()["id"]

    listed = client.get("/api/v1/prompts?favorites_only=true&search=Checklist")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert "Coding" in listed.json()["categories"]

    upd = client.put(f"/api/v1/prompts/{pid}", json={"title": "Senior Code Review"})
    assert upd.status_code == 200
    assert upd.json()["title"] == "Senior Code Review"

    assert client.delete(f"/api/v1/prompts/{pid}").status_code == 204
    assert client.get("/api/v1/prompts").json()["total"] == 0


def test_conversation_pin_export_clear_and_analytics_pricing(
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

    async def fake_generate(
        self: OllamaProvider,
        request: ChatRequest,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> ChatResponse:
        return ChatResponse(
            content="Pinned chat reply.",
            model_id=request.model_id,
            usage=ChatUsage(input_tokens=500_000, output_tokens=250_000, total_tokens=750_000),
        )

    monkeypatch.setattr(OllamaProvider, "generate_response", fake_generate)

    c1 = client.post("/api/v1/conversations", json={"title": "First Chat"}).json()
    c2 = client.post("/api/v1/conversations", json={"title": "Second Chat"}).json()

    # Pin c1 so it sorts ahead of c2
    pin_resp = client.put(f"/api/v1/conversations/{c1['id']}", json={"is_pinned": True})
    assert pin_resp.status_code == 200
    assert pin_resp.json()["is_pinned"] is True

    ordered = client.get("/api/v1/conversations").json()["conversations"]
    assert ordered[0]["id"] == c1["id"]

    # Send message so export & analytics have real data
    client.post(
        f"/api/v1/conversations/{c1['id']}/messages",
        json={"content": "Hello", "provider_id": prov["id"], "model_id": "llama3.2"},
    )

    # Export Markdown & TXT
    md = client.get(f"/api/v1/conversations/{c1['id']}/export?format=md")
    assert md.status_code == 200
    assert b"# First Chat" in md.content
    assert b"Pinned chat reply." in md.content

    txt = client.get(f"/api/v1/conversations/{c1['id']}/export?format=txt")
    assert txt.status_code == 200
    assert b"Pinned chat reply." in txt.content

    # Analytics without pricing -> estimated_total_cost is None
    an_before = client.get("/api/v1/analytics/overview").json()
    assert an_before["total_conversations"] == 2
    assert an_before["total_requests"] == 1
    assert an_before["total_tokens"] == 750_000
    assert an_before["estimated_total_cost"] is None

    # Configure pricing -> estimated cost computed accurately ($2/1M in, $4/1M out => $1 + $1 = $2.0)
    client.put(
        "/api/v1/analytics/pricing",
        json={
            "provider_name": "Local Ollama",
            "model_name": "llama3.2",
            "input_cost_per_1m": 2.0,
            "output_cost_per_1m": 4.0,
        },
    )
    an_after = client.get("/api/v1/analytics/overview").json()
    assert an_after["estimated_total_cost"] == 2.0
    assert len(an_after["daily_usage"]) >= 1
    assert len(an_after["monthly_usage"]) >= 1

    # Clear conversation messages
    cleared = client.post(f"/api/v1/conversations/{c1['id']}/clear")
    assert cleared.status_code == 200
    assert cleared.json()["message_count"] == 0
    assert c2["id"] is not None
