from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.productivity import (
    PromptTemplateCreateRequest,
    PromptTemplateListResponse,
    PromptTemplateResponse,
    PromptTemplateUpdateRequest,
)
from app.services import prompt_service

router = APIRouter(prefix="/prompts", tags=["Prompt Library"])


@router.get("", response_model=PromptTemplateListResponse, summary="List saved prompts")
def list_prompts(
    search: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=64),
    favorites_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> PromptTemplateListResponse:
    return prompt_service.list_prompts(
        db, search=search, category=category, favorites_only=favorites_only
    )


@router.post(
    "",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a saved prompt template",
)
def create_prompt(
    payload: PromptTemplateCreateRequest,
    db: Session = Depends(get_db),
) -> PromptTemplateResponse:
    return prompt_service.create_prompt(db, payload)


@router.put(
    "/{prompt_id}",
    response_model=PromptTemplateResponse,
    summary="Update a saved prompt template",
)
def update_prompt(
    prompt_id: str,
    payload: PromptTemplateUpdateRequest,
    db: Session = Depends(get_db),
) -> PromptTemplateResponse:
    return prompt_service.update_prompt(db, prompt_id, payload)


@router.delete(
    "/{prompt_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved prompt template",
)
def delete_prompt(prompt_id: str, db: Session = Depends(get_db)) -> Response:
    prompt_service.delete_prompt(db, prompt_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
