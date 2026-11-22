from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.chat import ChatStreamRequest
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "/stream",
    summary="Stream an AI chat response using Server-Sent Events (SSE)",
)
async def stream_chat(
    payload: ChatStreamRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    # Validate provider/model/credential eagerly before opening SSE stream
    chat_service._resolve_provider_execution(
        db, payload.provider_id, payload.model_id, payload.credential_id
    )
    event_stream = chat_service.stream_chat_events(db, payload, request)
    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
