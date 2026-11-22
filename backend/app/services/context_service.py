from dataclasses import dataclass
from typing import Any

from app.models.message import Message
from app.providers.base import ChatMessageInput

# Conservative default character budget (~24k tokens assuming ~4 chars/token)
DEFAULT_CONTEXT_CHAR_BUDGET = 96_000
MIN_CONTEXT_CHAR_BUDGET = 4_000


@dataclass(frozen=True)
class ContextBuildResult:
    messages: list[ChatMessageInput]
    truncated: bool
    excluded_count: int


def compute_char_budget(model_capabilities: dict[str, Any] | None) -> int:
    """Compute a conservative character budget from known model input token limits.

    We reserve ~25% headroom for system prompt, formatting overhead, and reply tokens,
    and never claim this heuristic is an exact token count.
    """
    if model_capabilities:
        input_limit = model_capabilities.get("input_token_limit") or model_capabilities.get(
            "context_window"
        )
        if isinstance(input_limit, int) and input_limit > 0:
            usable_tokens = int(input_limit * 0.75)
            return max(MIN_CONTEXT_CHAR_BUDGET, usable_tokens * 3)
    return DEFAULT_CONTEXT_CHAR_BUDGET


def build_conversation_context(
    history: list[Message],
    system_prompt: str = "",
    model_capabilities: dict[str, Any] | None = None,
    char_budget_override: int | None = None,
) -> ContextBuildResult:
    """Select the most recent valid user/assistant messages that fit within the model budget."""
    budget = (
        char_budget_override
        if char_budget_override is not None
        else compute_char_budget(model_capabilities)
    )
    remaining = max(MIN_CONTEXT_CHAR_BUDGET, budget - len(system_prompt))

    eligible: list[Message] = [
        m
        for m in history
        if m.role in {"user", "assistant"}
        and m.status != "error"
        and (m.content or "").strip() != ""
    ]

    if not eligible:
        return ContextBuildResult(messages=[], truncated=False, excluded_count=0)

    selected_reversed: list[ChatMessageInput] = []
    used = 0
    for idx, msg in enumerate(reversed(eligible)):
        msg_len = len(msg.content)
        # Always include the latest message even if it is very long
        if idx > 0 and used + msg_len > remaining:
            break
        selected_reversed.append(ChatMessageInput(role=msg.role, content=msg.content))
        used += msg_len

    selected = list(reversed(selected_reversed))
    excluded = len(eligible) - len(selected)
    return ContextBuildResult(
        messages=selected,
        truncated=excluded > 0,
        excluded_count=excluded,
    )
