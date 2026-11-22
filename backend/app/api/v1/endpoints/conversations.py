from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.chat import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationSummaryResponse,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageListResponse,
    MessageSendResponse,
)
from app.services import chat_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List and search local conversations with pagination",
)
def list_conversations(
    search: str | None = Query(default=None, max_length=200),
    project_id: str | None = Query(default=None),
    model: str | None = Query(default=None, max_length=160),
    date_from: str | None = Query(default=None, max_length=64),
    date_to: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    return chat_service.list_conversations(
        db,
        search=search,
        project_id=project_id,
        model_name=model,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ConversationSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new local conversation",
)
def create_conversation(
    payload: ConversationCreateRequest,
    db: Session = Depends(get_db),
) -> ConversationSummaryResponse:
    return chat_service.create_conversation(db, payload)


@router.get(
    "/{conversation_id}",
    response_model=ConversationSummaryResponse,
    summary="Get conversation details",
)
def read_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationSummaryResponse:
    return chat_service.get_conversation(db, conversation_id)


@router.put(
    "/{conversation_id}",
    response_model=ConversationSummaryResponse,
    summary="Update conversation title, model, or system prompt",
)
def update_conversation(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    db: Session = Depends(get_db),
) -> ConversationSummaryResponse:
    return chat_service.update_conversation(db, conversation_id, payload)


@router.post(
    "/{conversation_id}/clear",
    response_model=ConversationSummaryResponse,
    summary="Clear all messages inside a conversation",
)
def clear_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationSummaryResponse:
    return chat_service.clear_conversation_messages(db, conversation_id)


@router.get(
    "/{conversation_id}/export",
    summary="Export a conversation as Markdown (.md) or plain text (.txt)",
)
def export_conversation(
    conversation_id: str,
    format: str = Query(default="md", pattern="^(md|txt)$"),
    db: Session = Depends(get_db),
) -> Response:
    filename, media_type, content = chat_service.export_conversation(
        db, conversation_id, fmt=format
    )
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation and all its messages",
)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> Response:
    chat_service.delete_conversation(db, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="Get paginated message history for a conversation",
)
def read_conversation_messages(
    conversation_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    return chat_service.list_messages(db, conversation_id, limit=limit, offset=offset)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageSendResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message and receive a non-streaming AI response",
)
async def create_conversation_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    db: Session = Depends(get_db),
) -> MessageSendResponse:
    return await chat_service.send_message_non_streaming(db, conversation_id, payload)
