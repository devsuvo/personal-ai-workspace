from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.productivity import (
    AIToolListResponse,
    AIToolRunRequest,
    AIToolRunResponse,
)
from app.services import tools_service

router = APIRouter(prefix="/tools", tags=["AI Tools"])


@router.get("", response_model=AIToolListResponse, summary="List built-in AI productivity tools")
def list_ai_tools() -> AIToolListResponse:
    return AIToolListResponse(tools=tools_service.list_tools())


@router.post(
    "/run",
    response_model=AIToolRunResponse,
    summary="Execute an AI productivity tool using a configured provider and model",
)
async def execute_ai_tool(
    payload: AIToolRunRequest,
    db: Session = Depends(get_db),
) -> AIToolRunResponse:
    return await tools_service.run_tool(db, payload)
