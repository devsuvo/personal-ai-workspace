from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.usage_log import UsageLog
from app.providers.base import ChatMessageInput, ChatRequest, ProviderAdapterError
from app.schemas.productivity import (
    AIToolDefinition,
    AIToolRunRequest,
    AIToolRunResponse,
)
from app.services.chat_service import _resolve_provider_execution

AI_TOOLS: tuple[AIToolDefinition, ...] = (
    AIToolDefinition(
        id="summarizer",
        name="Text Summarizer",
        description="Distill long articles, notes, or reports into concise key takeaways.",
        category="Writing",
        input_label="Text to summarize",
        input_placeholder="Paste notes, articles, or transcripts to summarize...",
        options=[
            {
                "key": "format",
                "label": "Summary Format",
                "choices": ["Bullet Points", "Executive Summary", "One Paragraph"],
                "default": "Bullet Points",
            }
        ],
    ),
    AIToolDefinition(
        id="rewriter",
        name="Text Rewriter",
        description="Rewrite text for clarity, flow, and target tone without losing meaning.",
        category="Writing",
        input_label="Text to rewrite",
        input_placeholder="Paste text you want rewritten...",
        options=[
            {
                "key": "tone",
                "label": "Target Tone",
                "choices": ["Professional", "Clear & Concise", "Friendly", "Academic"],
                "default": "Professional",
            }
        ],
    ),
    AIToolDefinition(
        id="grammar",
        name="Grammar Corrector",
        description="Fix grammar, spelling, and punctuation while preserving your voice.",
        category="Writing",
        input_label="Text to proofread",
        input_placeholder="Paste text to check and correct...",
        options=[
            {
                "key": "explain",
                "label": "Include Explanations",
                "choices": ["Corrected Only", "Corrected + Key Changes"],
                "default": "Corrected + Key Changes",
            }
        ],
    ),
    AIToolDefinition(
        id="translator",
        name="Translation Tool",
        description="Translate text accurately into your chosen target language.",
        category="Language",
        input_label="Source text",
        input_placeholder="Enter text to translate...",
        options=[
            {
                "key": "target_language",
                "label": "Target Language",
                "choices": [
                    "English",
                    "Bengali",
                    "Spanish",
                    "French",
                    "German",
                    "Japanese",
                    "Arabic",
                    "Hindi",
                ],
                "default": "English",
            }
        ],
    ),
    AIToolDefinition(
        id="code_explainer",
        name="Code Explainer",
        description="Break down code snippets step by step, highlighting logic and edge cases.",
        category="Coding",
        input_label="Code to explain",
        input_placeholder="Paste a function, SQL query, or script...",
        options=[
            {
                "key": "depth",
                "label": "Explanation Level",
                "choices": ["Beginner Friendly", "Senior Engineer", "Line-by-Line"],
                "default": "Senior Engineer",
            }
        ],
    ),
    AIToolDefinition(
        id="code_generator",
        name="Code Generator",
        description="Generate clean, well-structured code from a plain-language specification.",
        category="Coding",
        input_label="What should the code do?",
        input_placeholder="Describe the function, script, or component you need...",
        options=[
            {
                "key": "language",
                "label": "Programming Language",
                "choices": [
                    "Python",
                    "TypeScript",
                    "JavaScript",
                    "SQL",
                    "HTML/CSS",
                    "Bash",
                ],
                "default": "Python",
            }
        ],
    ),
    AIToolDefinition(
        id="content_generator",
        name="Content Generator",
        description="Draft structured blog posts, outlines, documentation, or product copy.",
        category="Content",
        input_label="Topic & key points",
        input_placeholder="Describe the topic, target audience, and key points...",
        options=[
            {
                "key": "content_type",
                "label": "Content Type",
                "choices": ["Blog Post", "Technical Guide", "Outline", "Social Post"],
                "default": "Technical Guide",
            }
        ],
    ),
    AIToolDefinition(
        id="email_writer",
        name="Email Writer",
        description="Compose clear, effective emails tailored to your recipient and tone.",
        category="Communication",
        input_label="Email purpose & details",
        input_placeholder="Describe who you're emailing and what you want to say...",
        options=[
            {
                "key": "tone",
                "label": "Tone",
                "choices": ["Professional", "Warm & Polite", "Direct & Brief", "Follow-up"],
                "default": "Professional",
            }
        ],
    ),
    AIToolDefinition(
        id="custom_runner",
        name="Custom Prompt Runner",
        description="Run any custom instruction template against your input text.",
        category="Custom",
        input_label="Input content",
        input_placeholder="Enter the input data or text to process...",
        options=[
            {
                "key": "instruction",
                "label": "Custom Instruction",
                "type": "text",
                "default": "Analyze the following input and provide structured insights.",
            }
        ],
    ),
)

TOOLS_BY_ID: dict[str, AIToolDefinition] = {t.id: t for t in AI_TOOLS}


def list_tools() -> list[AIToolDefinition]:
    return list(AI_TOOLS)


def _build_tool_prompt(tool_id: str, options: dict[str, str]) -> str:
    if tool_id == "summarizer":
        fmt = options.get("format", "Bullet Points")
        return f"You are an expert editor. Summarize the user's text in '{fmt}' format. Be accurate and concise."
    if tool_id == "rewriter":
        tone = options.get("tone", "Professional")
        return f"Rewrite the user's text in a '{tone}' tone while preserving the original meaning and facts."
    if tool_id == "grammar":
        mode = options.get("explain", "Corrected + Key Changes")
        return f"Correct grammar, spelling, and punctuation in the user's text. Output mode: {mode}."
    if tool_id == "translator":
        lang = options.get("target_language", "English")
        return f"Translate the user's text accurately and naturally into {lang}. Preserve formatting where appropriate."
    if tool_id == "code_explainer":
        depth = options.get("depth", "Senior Engineer")
        return f"Explain the provided code clearly at a '{depth}' level. Highlight key logic, edge cases, and potential issues."
    if tool_id == "code_generator":
        lang = options.get("language", "Python")
        return f"Write clean, production-quality {lang} code matching the user's specification. Include brief usage notes."
    if tool_id == "content_generator":
        ctype = options.get("content_type", "Technical Guide")
        return f"Create a well-structured {ctype} based on the user's topic and points using clean Markdown."
    if tool_id == "email_writer":
        tone = options.get("tone", "Professional")
        return f"Draft a clear email with a '{tone}' tone including a concise Subject line and body."
    instruction = options.get(
        "instruction",
        "Analyze the following input and provide structured insights.",
    ).strip()
    return instruction or "Process the user's input clearly and accurately."


async def run_tool(
    db: Session, payload: AIToolRunRequest
) -> AIToolRunResponse:
    tool = TOOLS_BY_ID.get(payload.tool_id)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown AI tool '{payload.tool_id}'.",
        )

    provider, adapter, api_key, _cred_id, _caps = _resolve_provider_execution(
        db, payload.provider_id, payload.model_id, payload.credential_id
    )

    system_prompt = _build_tool_prompt(tool.id, payload.options)
    chat_req = ChatRequest(
        model_id=payload.model_id.strip(),
        messages=[ChatMessageInput(role="user", content=payload.input_text.strip())],
        system_prompt=system_prompt,
    )

    try:
        resp = await adapter.generate_response(
            chat_req, base_url=provider.base_url, api_key=api_key
        )
    except ProviderAdapterError as exc:
        db.add(
            UsageLog(
                provider_name=provider.display_name,
                model_name=payload.model_id.strip(),
                input_tokens=0,
                output_tokens=0,
                estimated_cost=0.0,
                request_status="error",
                error_message=exc.message,
            )
        )
        db.commit()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    usage_dict = resp.usage.to_dict() if resp.usage else None
    if resp.usage is not None:
        db.add(
            UsageLog(
                provider_name=provider.display_name,
                model_name=resp.model_id,
                input_tokens=resp.usage.input_tokens or 0,
                output_tokens=resp.usage.output_tokens or 0,
                estimated_cost=0.0,
                request_status="success",
            )
        )
        db.commit()

    return AIToolRunResponse(
        tool_id=tool.id,
        output=resp.content,
        provider_name=provider.display_name,
        model_id=resp.model_id,
        token_usage=usage_dict,
    )
