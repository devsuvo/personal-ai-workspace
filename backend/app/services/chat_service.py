import asyncio
from collections.abc import AsyncIterator
from datetime import datetime, timezone
import json
import logging
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core import config as app_config
from app.core.security import (
    EncryptionOperationError,
    MasterKeyError,
    get_encryption_service,
    sanitize_filename,
)
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.project import Project
from app.models.provider import Provider, ProviderCredential, ProviderModel
from app.models.usage_log import UsageLog
from app.providers.base import (
    BaseAIProvider,
    ChatRequest,
    ChatUsage,
    ProviderAdapterError,
)
from app.providers.registry import get_provider_adapter
from app.schemas.chat import (
    ChatStreamRequest,
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationSummaryResponse,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageListResponse,
    MessageRegenerateRequest,
    MessageResponse,
    MessageSendResponse,
    MessageUpdateRequest,
)
from app.services import settings_service
from app.services.context_service import build_conversation_context
from app.services.file_context_service import build_file_context

logger = logging.getLogger("workspace.chat")


def generate_fallback_title(prompt: str) -> str:
    """Derive a clean, concise local title from the first user prompt."""
    collapsed = " ".join(prompt.strip().split())
    if not collapsed:
        return "New Conversation"
    if len(collapsed) <= 64:
        return collapsed
    truncated = collapsed[:61].rsplit(" ", 1)[0]
    return f"{truncated}..."


def _to_message_response(msg: Message) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        provider_id=msg.provider_id,
        provider_name=msg.provider_name,
        model_id=msg.model_id or msg.model_name,
        model_name=msg.model_name or msg.model_id,
        credential_id=msg.credential_id,
        status=msg.status,
        error_message=msg.error_message,
        token_usage=msg.token_usage,
        created_at=msg.created_at,
    )


def _to_conversation_summary(
    conv: Conversation, message_count: int = 0
) -> ConversationSummaryResponse:
    return ConversationSummaryResponse(
        id=conv.id,
        title=conv.title,
        project_id=conv.project_id,
        provider_id=conv.provider_id,
        model_name=conv.model_name,
        system_prompt=conv.system_prompt,
        is_pinned=conv.is_pinned,
        message_count=message_count,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def _format_sse(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, default=str)}\n\n"


def _resolve_provider_execution(
    db: Session,
    provider_id: str,
    model_id: str,
    credential_id: str | None = None,
) -> tuple[Provider, BaseAIProvider, str | None, str | None, dict[str, Any] | None]:
    """Validate provider, model, and credential references, decrypting key only in backend."""
    provider = db.execute(
        select(Provider)
        .options(
            selectinload(Provider.credentials),
            selectinload(Provider.models),
        )
        .where(Provider.id == provider_id)
    ).scalar_one_or_none()

    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected AI provider was not found. Configure a provider first.",
        )
    if not provider.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider.display_name}' is currently disabled.",
        )

    cleaned_model = model_id.strip()
    if not cleaned_model:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A model identifier must be selected.",
        )

    model_record: ProviderModel | None = next(
        (m for m in provider.models if m.model_id == cleaned_model), None
    )
    if model_record is not None and not model_record.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{cleaned_model}' is disabled for '{provider.display_name}'. Select another model.",
        )

    selected_cred: ProviderCredential | None = None
    if credential_id:
        selected_cred = next(
            (c for c in provider.credentials if c.id == credential_id), None
        )
        if selected_cred is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected API credential does not belong to this provider.",
            )
    else:
        selected_cred = next(
            (c for c in provider.credentials if c.is_active), None
        )

    adapter = get_provider_adapter(provider.provider_key)
    api_key: str | None = None
    if selected_cred is not None:
        encryption = get_encryption_service()
        try:
            api_key = encryption.decrypt(selected_cred.encrypted_api_key)
        except (MasterKeyError, EncryptionOperationError) as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc

    try:
        adapter.validate_config(base_url=provider.base_url, api_key=api_key)
    except ProviderAdapterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    model_caps = model_record.capabilities if model_record else None
    return (
        provider,
        adapter,
        api_key,
        selected_cred.id if selected_cred else None,
        model_caps,
    )


def _record_usage_log(
    db: Session,
    conversation_id: str,
    message_id: str,
    provider_name: str,
    model_name: str,
    usage: ChatUsage | None,
    request_status: str,
    error_message: str | None = None,
) -> None:
    """Record real usage when provider returns token counts or when logging a failed request."""
    if usage is None and request_status == "success":
        return
    in_tok = usage.input_tokens if (usage and usage.input_tokens is not None) else 0
    out_tok = usage.output_tokens if (usage and usage.output_tokens is not None) else 0
    log = UsageLog(
        conversation_id=conversation_id,
        message_id=message_id,
        provider_name=provider_name,
        model_name=model_name,
        input_tokens=in_tok,
        output_tokens=out_tok,
        estimated_cost=0.0,
        request_status=request_status,
        error_message=error_message,
    )
    db.add(log)


def _get_effective_system_prompt(
    db: Session,
    conversation: Conversation,
    attachment_ids: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Compose layered instructions without overwriting global settings.

    Precedence (highest to lowest):
    1. Conversation-specific system prompt
    2. Project-specific AI instructions (when conversation belongs to a project)
    3. Global workspace default system prompt
    Plus optional attached file context.
    """
    sections: list[str] = []

    try:
        global_prompt = settings_service.get_setting(
            db, "chat_default_system_prompt"
        ).value
        if global_prompt and str(global_prompt).strip():
            sections.append(f"[Workspace Default Instructions]\n{str(global_prompt).strip()}")
    except Exception:
        pass

    if conversation.project_id:
        project = db.get(Project, conversation.project_id)
        if project and project.instructions.strip():
            sections.append(
                f"[Project Instructions: {project.name} — overrides workspace defaults if conflicting]\n"
                f"{project.instructions.strip()}"
            )

    if conversation.system_prompt and conversation.system_prompt.strip():
        sections.append(
            f"[Conversation Instructions — highest priority]\n{conversation.system_prompt.strip()}"
        )

    included_files: list[str] = []
    if attachment_ids:
        file_ctx = build_file_context(db, app_config.get_settings(), attachment_ids)
        included_files = file_ctx.included_files
        if file_ctx.context_text:
            sections.append(
                "[Attached Local File Context — use to answer the user's request]\n"
                f"{file_ctx.context_text}"
            )

    return "\n\n".join(sections), included_files


def _load_conversation_or_404(db: Session, conversation_id: str) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    return conv


def list_conversations(
    db: Session,
    search: str | None = None,
    project_id: str | None = None,
    model_name: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ConversationListResponse:
    base_query = select(Conversation)
    if project_id:
        base_query = base_query.where(Conversation.project_id == project_id)
    if model_name and model_name.strip():
        base_query = base_query.where(
            Conversation.model_name.ilike(f"%{model_name.strip()}%")
        )
    if date_from and date_from.strip():
        try:
            dt_from = datetime.fromisoformat(date_from.strip())
            base_query = base_query.where(Conversation.created_at >= dt_from)
        except ValueError:
            pass
    if date_to and date_to.strip():
        try:
            dt_to = datetime.fromisoformat(date_to.strip())
            base_query = base_query.where(Conversation.created_at <= dt_to)
        except ValueError:
            pass
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        matching_conv_ids = select(Message.conversation_id).where(
            Message.content.ilike(pattern)
        )
        base_query = base_query.where(
            or_(
                Conversation.title.ilike(pattern),
                Conversation.id.in_(matching_conv_ids),
            )
        )

    total = db.execute(
        select(func.count()).select_from(base_query.subquery())
    ).scalar_one()

    rows = (
        db.execute(
            base_query.order_by(
                Conversation.is_pinned.desc(), Conversation.updated_at.desc()
            )
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    conv_ids = [c.id for c in rows]
    counts: dict[str, int] = {}
    if conv_ids:
        count_rows = db.execute(
            select(Message.conversation_id, func.count(Message.id))
            .where(Message.conversation_id.in_(conv_ids))
            .group_by(Message.conversation_id)
        ).all()
        counts = {cid: int(cnt) for cid, cnt in count_rows}

    return ConversationListResponse(
        conversations=[
            _to_conversation_summary(c, counts.get(c.id, 0)) for c in rows
        ],
        total=int(total),
        limit=limit,
        offset=offset,
    )


def create_conversation(
    db: Session, payload: ConversationCreateRequest
) -> ConversationSummaryResponse:
    conv = Conversation(
        title=(payload.title or "New Conversation").strip() or "New Conversation",
        project_id=payload.project_id,
        provider_id=payload.provider_id,
        model_name=payload.model_name,
        system_prompt=payload.system_prompt or "",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return _to_conversation_summary(conv, message_count=0)


def get_conversation(db: Session, conversation_id: str) -> ConversationSummaryResponse:
    conv = _load_conversation_or_404(db, conversation_id)
    msg_count = db.execute(
        select(func.count(Message.id)).where(Message.conversation_id == conv.id)
    ).scalar_one()
    return _to_conversation_summary(conv, message_count=int(msg_count))


def update_conversation(
    db: Session, conversation_id: str, payload: ConversationUpdateRequest
) -> ConversationSummaryResponse:
    conv = _load_conversation_or_404(db, conversation_id)
    if payload.title is not None:
        conv.title = payload.title.strip()
    if payload.project_id is not None:
        conv.project_id = payload.project_id.strip() or None
    if payload.provider_id is not None:
        conv.provider_id = payload.provider_id.strip() or None
    if payload.model_name is not None:
        conv.model_name = payload.model_name.strip() or None
    if payload.system_prompt is not None:
        conv.system_prompt = payload.system_prompt
    if payload.is_pinned is not None:
        conv.is_pinned = payload.is_pinned
    db.commit()
    db.refresh(conv)
    return get_conversation(db, conv.id)


def clear_conversation_messages(
    db: Session, conversation_id: str
) -> ConversationSummaryResponse:
    conv = _load_conversation_or_404(db, conversation_id)
    msgs = (
        db.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        .scalars()
        .all()
    )
    for m in msgs:
        db.delete(m)
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    return get_conversation(db, conv.id)


def export_conversation(
    db: Session, conversation_id: str, fmt: str = "md"
) -> tuple[str, str, str]:
    conv = _load_conversation_or_404(db, conversation_id)
    msgs = (
        db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        )
        .scalars()
        .all()
    )
    safe_base = sanitize_filename(conv.title.replace(" ", "_"))
    if fmt == "txt":
        lines = [f"{conv.title}", "=" * len(conv.title), ""]
        for m in msgs:
            role_label = m.role.upper()
            meta = f" ({m.provider_name} / {m.model_id or m.model_name})" if m.role == "assistant" and m.provider_name else ""
            lines.append(f"[{role_label}{meta}]")
            lines.append(m.content)
            lines.append("")
        return f"{safe_base}.txt", "text/plain; charset=utf-8", "\n".join(lines)

    lines = [f"# {conv.title}", ""]
    for m in msgs:
        if m.role == "user":
            lines.append("## User")
        else:
            meta = f" — `{m.provider_name} / {m.model_id or m.model_name}`" if m.provider_name else ""
            lines.append(f"## Assistant{meta}")
        lines.append("")
        lines.append(m.content)
        lines.append("")
    return f"{safe_base}.md", "text/markdown; charset=utf-8", "\n".join(lines)


def delete_conversation(db: Session, conversation_id: str) -> None:
    conv = _load_conversation_or_404(db, conversation_id)
    db.delete(conv)
    db.commit()


def list_messages(
    db: Session,
    conversation_id: str,
    limit: int = 100,
    offset: int = 0,
) -> MessageListResponse:
    _load_conversation_or_404(db, conversation_id)
    total = db.execute(
        select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    ).scalar_one()

    rows = (
        db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    return MessageListResponse(
        conversation_id=conversation_id,
        messages=[_to_message_response(m) for m in rows],
        total=int(total),
        limit=limit,
        offset=offset,
    )


def update_message(
    db: Session, message_id: str, payload: MessageUpdateRequest
) -> MessageResponse:
    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found."
        )
    msg.content = payload.content.strip()

    if payload.truncate_after:
        subsequent = (
            db.execute(
                select(Message).where(
                    Message.conversation_id == msg.conversation_id,
                    Message.created_at > msg.created_at,
                )
            )
            .scalars()
            .all()
        )
        for item in subsequent:
            db.delete(item)

    conv = db.get(Conversation, msg.conversation_id)
    if conv is not None:
        conv.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(msg)
    return _to_message_response(msg)


def delete_message(db: Session, message_id: str) -> None:
    msg = db.get(Message, message_id)
    if msg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found."
        )
    db.delete(msg)
    db.commit()


async def send_message_non_streaming(
    db: Session,
    conversation_id: str,
    payload: MessageCreateRequest,
) -> MessageSendResponse:
    conv = _load_conversation_or_404(db, conversation_id)
    provider, adapter, api_key, cred_id, model_caps = _resolve_provider_execution(
        db, payload.provider_id, payload.model_id, payload.credential_id
    )

    # Persist user message first so it is never lost on provider failure
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=payload.content.strip(),
        provider_id=provider.id,
        provider_name=provider.display_name,
        model_id=payload.model_id.strip(),
        model_name=payload.model_id.strip(),
        credential_id=cred_id,
        status="completed",
    )
    db.add(user_msg)
    if conv.title == "New Conversation":
        conv.title = generate_fallback_title(payload.content)
    conv.provider_id = provider.id
    conv.model_name = payload.model_id.strip()
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_msg)

    history = (
        db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        )
        .scalars()
        .all()
    )
    sys_prompt, _included_files = _get_effective_system_prompt(
        db, conv, attachment_ids=payload.attachment_ids
    )
    ctx = build_conversation_context(history, sys_prompt, model_caps)

    chat_req = ChatRequest(
        model_id=payload.model_id.strip(),
        messages=ctx.messages,
        system_prompt=sys_prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    try:
        ai_resp = await adapter.generate_response(
            chat_req, base_url=provider.base_url, api_key=api_key
        )
        usage_dict = ai_resp.usage.to_dict() if ai_resp.usage else None
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=ai_resp.content,
            provider_id=provider.id,
            provider_name=provider.display_name,
            model_id=ai_resp.model_id,
            model_name=ai_resp.model_id,
            credential_id=cred_id,
            status="completed",
            token_usage=usage_dict,
        )
        db.add(assistant_msg)
        db.flush()
        _record_usage_log(
            db,
            conv.id,
            assistant_msg.id,
            provider.display_name,
            ai_resp.model_id,
            ai_resp.usage,
            "success",
        )
    except ProviderAdapterError as exc:
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content="",
            provider_id=provider.id,
            provider_name=provider.display_name,
            model_id=payload.model_id.strip(),
            model_name=payload.model_id.strip(),
            credential_id=cred_id,
            status="error",
            error_message=exc.message,
        )
        db.add(assistant_msg)
        db.flush()
        _record_usage_log(
            db,
            conv.id,
            assistant_msg.id,
            provider.display_name,
            payload.model_id.strip(),
            None,
            "error",
            error_message=exc.message,
        )

    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_msg)

    return MessageSendResponse(
        conversation=get_conversation(db, conv.id),
        user_message=_to_message_response(user_msg),
        assistant_message=_to_message_response(assistant_msg),
        context_truncated=ctx.truncated,
        excluded_messages_count=ctx.excluded_count,
    )


async def regenerate_message_non_streaming(
    db: Session,
    message_id: str,
    payload: MessageRegenerateRequest,
) -> MessageResponse:
    target = db.get(Message, message_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found."
        )
    conv = _load_conversation_or_404(db, target.conversation_id)

    provider_id = payload.provider_id or target.provider_id or conv.provider_id
    model_id = payload.model_id or target.model_id or target.model_name or conv.model_name
    if not provider_id or not model_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider and model must be specified to regenerate this message.",
        )

    provider, adapter, api_key, cred_id, model_caps = _resolve_provider_execution(
        db, provider_id, model_id, payload.credential_id or target.credential_id
    )

    # Gather conversation history up to (and excluding if assistant) target message
    if target.role == "assistant":
        history = (
            db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.created_at < target.created_at,
                )
                .order_by(Message.created_at.asc())
            )
            .scalars()
            .all()
        )
    else:
        history = (
            db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.created_at <= target.created_at,
                )
                .order_by(Message.created_at.asc())
            )
            .scalars()
            .all()
        )

    sys_prompt, _included_files = _get_effective_system_prompt(db, conv)
    ctx = build_conversation_context(history, sys_prompt, model_caps)
    chat_req = ChatRequest(
        model_id=model_id.strip(),
        messages=ctx.messages,
        system_prompt=sys_prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    try:
        ai_resp = await adapter.generate_response(
            chat_req, base_url=provider.base_url, api_key=api_key
        )
        usage_dict = ai_resp.usage.to_dict() if ai_resp.usage else None
        if target.role == "assistant":
            target.content = ai_resp.content
            target.provider_id = provider.id
            target.provider_name = provider.display_name
            target.model_id = ai_resp.model_id
            target.model_name = ai_resp.model_id
            target.credential_id = cred_id
            target.status = "completed"
            target.error_message = None
            target.token_usage = usage_dict
            assistant_msg = target
        else:
            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=ai_resp.content,
                provider_id=provider.id,
                provider_name=provider.display_name,
                model_id=ai_resp.model_id,
                model_name=ai_resp.model_id,
                credential_id=cred_id,
                status="completed",
                token_usage=usage_dict,
            )
            db.add(assistant_msg)
            db.flush()

        _record_usage_log(
            db,
            conv.id,
            assistant_msg.id,
            provider.display_name,
            ai_resp.model_id,
            ai_resp.usage,
            "success",
        )
    except ProviderAdapterError as exc:
        if target.role == "assistant":
            target.status = "error"
            target.error_message = exc.message
            assistant_msg = target
        else:
            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content="",
                provider_id=provider.id,
                provider_name=provider.display_name,
                model_id=model_id.strip(),
                model_name=model_id.strip(),
                credential_id=cred_id,
                status="error",
                error_message=exc.message,
            )
            db.add(assistant_msg)
            db.flush()
        _record_usage_log(
            db,
            conv.id,
            assistant_msg.id,
            provider.display_name,
            model_id.strip(),
            None,
            "error",
            error_message=exc.message,
        )

    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_msg)
    return _to_message_response(assistant_msg)


async def stream_chat_events(
    db: Session,
    payload: ChatStreamRequest,
    http_request: Request,
) -> AsyncIterator[str]:
    """Stream Server-Sent Events for chat generation, edit-and-resend, or regeneration."""
    provider, adapter, api_key, cred_id, model_caps = _resolve_provider_execution(
        db, payload.provider_id, payload.model_id, payload.credential_id
    )
    cleaned_model = payload.model_id.strip()

    # 1. Resolve or create conversation
    if payload.conversation_id:
        conv = _load_conversation_or_404(db, payload.conversation_id)
    else:
        initial_title = generate_fallback_title(payload.content or "")
        conv = Conversation(
            title=initial_title,
            project_id=payload.project_id,
            provider_id=provider.id,
            model_name=cleaned_model,
            system_prompt=payload.system_prompt or "",
        )
        db.add(conv)
        db.flush()

    user_msg: Message | None = None
    assistant_msg: Message | None = None

    # 2. Handle edit-and-resend, regenerate, or new user message
    if payload.regenerate_message_id:
        existing = db.get(Message, payload.regenerate_message_id)
        if existing is None or existing.conversation_id != conv.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message to regenerate was not found in this conversation.",
            )
        if existing.role == "assistant":
            # Remove any messages strictly after this assistant message
            after = (
                db.execute(
                    select(Message).where(
                        Message.conversation_id == conv.id,
                        Message.created_at > existing.created_at,
                    )
                )
                .scalars()
                .all()
            )
            for item in after:
                db.delete(item)
            existing.content = ""
            existing.provider_id = provider.id
            existing.provider_name = provider.display_name
            existing.model_id = cleaned_model
            existing.model_name = cleaned_model
            existing.credential_id = cred_id
            existing.status = "streaming"
            existing.error_message = None
            existing.token_usage = None
            assistant_msg = existing
        else:
            after = (
                db.execute(
                    select(Message).where(
                        Message.conversation_id == conv.id,
                        Message.created_at > existing.created_at,
                    )
                )
                .scalars()
                .all()
            )
            for item in after:
                db.delete(item)
            user_msg = existing
    elif payload.edit_message_id:
        existing = db.get(Message, payload.edit_message_id)
        if existing is None or existing.conversation_id != conv.id or existing.role != "user":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User message to edit was not found in this conversation.",
            )
        if not payload.content or not payload.content.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Edited message content cannot be empty.",
            )
        existing.content = payload.content.strip()
        after = (
            db.execute(
                select(Message).where(
                    Message.conversation_id == conv.id,
                    Message.created_at > existing.created_at,
                )
            )
            .scalars()
            .all()
        )
        for item in after:
            db.delete(item)
        user_msg = existing
    else:
        if not payload.content or not payload.content.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message content cannot be empty.",
            )
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=payload.content.strip(),
            provider_id=provider.id,
            provider_name=provider.display_name,
            model_id=cleaned_model,
            model_name=cleaned_model,
            credential_id=cred_id,
            status="completed",
        )
        db.add(user_msg)
        if conv.title == "New Conversation":
            conv.title = generate_fallback_title(payload.content)

    conv.provider_id = provider.id
    conv.model_name = cleaned_model
    conv.updated_at = datetime.now(timezone.utc)
    db.flush()

    if assistant_msg is None:
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content="",
            provider_id=provider.id,
            provider_name=provider.display_name,
            model_id=cleaned_model,
            model_name=cleaned_model,
            credential_id=cred_id,
            status="streaming",
        )
        db.add(assistant_msg)

    db.commit()
    db.refresh(conv)
    if user_msg is not None:
        db.refresh(user_msg)
    db.refresh(assistant_msg)

    # 3. Build conversation context excluding the new placeholder assistant message
    history = (
        db.execute(
            select(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.id != assistant_msg.id,
            )
            .order_by(Message.created_at.asc())
        )
        .scalars()
        .all()
    )
    sys_prompt, included_files = _get_effective_system_prompt(
        db, conv, attachment_ids=payload.attachment_ids
    )
    ctx = build_conversation_context(history, sys_prompt, model_caps)
    chat_req = ChatRequest(
        model_id=cleaned_model,
        messages=ctx.messages,
        system_prompt=sys_prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    yield _format_sse(
        "message_start",
        {
            "conversation_id": conv.id,
            "conversation_title": conv.title,
            "user_message": _to_message_response(user_msg).model_dump(mode="json")
            if user_msg is not None
            else None,
            "assistant_message_id": assistant_msg.id,
            "provider_id": provider.id,
            "provider_name": provider.display_name,
            "model_id": cleaned_model,
            "context_truncated": ctx.truncated,
            "excluded_messages_count": ctx.excluded_count,
            "attached_files": included_files,
        },
    )

    accumulated: list[str] = []
    final_usage: ChatUsage | None = None
    stopped = False

    try:
        async for chunk in adapter.stream_response(
            chat_req, base_url=provider.base_url, api_key=api_key
        ):
            if await http_request.is_disconnected():
                stopped = True
                break

            if chunk.delta:
                accumulated.append(chunk.delta)
                yield _format_sse(
                    "content_delta",
                    {
                        "message_id": assistant_msg.id,
                        "delta": chunk.delta,
                    },
                )
            if chunk.usage is not None:
                final_usage = chunk.usage

        assistant_msg.content = "".join(accumulated)
        assistant_msg.token_usage = final_usage.to_dict() if final_usage else None
        assistant_msg.status = "stopped" if stopped else "completed"
        assistant_msg.error_message = None
        conv.updated_at = datetime.now(timezone.utc)

        _record_usage_log(
            db,
            conv.id,
            assistant_msg.id,
            provider.display_name,
            cleaned_model,
            final_usage,
            "stopped" if stopped else "success",
        )
        db.commit()
        db.refresh(assistant_msg)

        event_name = "generation_stopped" if stopped else "message_complete"
        yield _format_sse(
            event_name,
            {"message": _to_message_response(assistant_msg).model_dump(mode="json")},
        )
    except asyncio.CancelledError:
        assistant_msg.content = "".join(accumulated)
        assistant_msg.status = "stopped"
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()
        raise
    except ProviderAdapterError as exc:
        assistant_msg.content = "".join(accumulated)
        assistant_msg.status = "error"
        assistant_msg.error_message = exc.message
        conv.updated_at = datetime.now(timezone.utc)
        _record_usage_log(
            db,
            conv.id,
            assistant_msg.id,
            provider.display_name,
            cleaned_model,
            final_usage,
            "error",
            error_message=exc.message,
        )
        db.commit()
        db.refresh(assistant_msg)
        yield _format_sse(
            "error",
            {
                "code": exc.code,
                "message": exc.message,
                "assistant_message_id": assistant_msg.id,
                "message_record": _to_message_response(assistant_msg).model_dump(
                    mode="json"
                ),
            },
        )
    except Exception as exc:
        logger.exception("Unexpected streaming error: %s", exc)
        safe_msg = "An unexpected error interrupted streaming. Your previous messages were preserved."
        assistant_msg.content = "".join(accumulated)
        assistant_msg.status = "error"
        assistant_msg.error_message = safe_msg
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(assistant_msg)
        yield _format_sse(
            "error",
            {
                "code": "STREAM_INTERRUPTED",
                "message": safe_msg,
                "assistant_message_id": assistant_msg.id,
                "message_record": _to_message_response(assistant_msg).model_dump(
                    mode="json"
                ),
            },
        )
