from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.chat import (
    MessageRegenerateRequest,
    MessageResponse,
    MessageUpdateRequest,
)
from app.services import chat_service

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.put(
    "/{message_id}",
    response_model=MessageResponse,
    summary="Edit a message (optionally truncating subsequent messages)",
)
def edit_message(
    message_id: str,
    payload: MessageUpdateRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    return chat_service.update_message(db, message_id, payload)


@router.delete(
    "/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a single message",
)
def remove_message(
    message_id: str,
    db: Session = Depends(get_db),
) -> Response:
    chat_service.delete_message(db, message_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{message_id}/regenerate",
    response_model=MessageResponse,
    summary="Regenerate an AI response (non-streaming)",
)
async def regenerate_message(
    message_id: str,
    payload: MessageRegenerateRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    return await chat_service.regenerate_message_non_streaming(db, message_id, payload)
