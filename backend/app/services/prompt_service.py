from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.prompt_template import PromptTemplate
from app.schemas.productivity import (
    PromptTemplateCreateRequest,
    PromptTemplateListResponse,
    PromptTemplateResponse,
    PromptTemplateUpdateRequest,
)


def _to_response(item: PromptTemplate) -> PromptTemplateResponse:
    return PromptTemplateResponse(
        id=item.id,
        title=item.title,
        category=item.category,
        description=item.description,
        content=item.content,
        is_favorite=item.is_favorite,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _get_or_404(db: Session, prompt_id: str) -> PromptTemplate:
    item = db.get(PromptTemplate, prompt_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found.",
        )
    return item


def list_prompts(
    db: Session,
    search: str | None = None,
    category: str | None = None,
    favorites_only: bool = False,
) -> PromptTemplateListResponse:
    query = select(PromptTemplate)
    if favorites_only:
        query = query.where(PromptTemplate.is_favorite.is_(True))
    if category and category.strip():
        query = query.where(PromptTemplate.category == category.strip())
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                PromptTemplate.title.ilike(pattern),
                PromptTemplate.description.ilike(pattern),
                PromptTemplate.content.ilike(pattern),
            )
        )

    rows = (
        db.execute(
            query.order_by(
                PromptTemplate.is_favorite.desc(), PromptTemplate.updated_at.desc()
            )
        )
        .scalars()
        .all()
    )

    all_categories = (
        db.execute(
            select(PromptTemplate.category)
            .distinct()
            .order_by(PromptTemplate.category.asc())
        )
        .scalars()
        .all()
    )

    return PromptTemplateListResponse(
        prompts=[_to_response(r) for r in rows],
        categories=list(all_categories),
        total=len(rows),
    )


def create_prompt(
    db: Session, payload: PromptTemplateCreateRequest
) -> PromptTemplateResponse:
    item = PromptTemplate(
        title=payload.title.strip(),
        category=payload.category.strip() or "General",
        description=payload.description.strip(),
        content=payload.content.strip(),
        is_favorite=payload.is_favorite,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_response(item)


def update_prompt(
    db: Session, prompt_id: str, payload: PromptTemplateUpdateRequest
) -> PromptTemplateResponse:
    item = _get_or_404(db, prompt_id)
    if payload.title is not None:
        item.title = payload.title.strip()
    if payload.category is not None:
        item.category = payload.category.strip() or "General"
    if payload.description is not None:
        item.description = payload.description.strip()
    if payload.content is not None:
        item.content = payload.content.strip()
    if payload.is_favorite is not None:
        item.is_favorite = payload.is_favorite
    db.commit()
    db.refresh(item)
    return _to_response(item)


def delete_prompt(db: Session, prompt_id: str) -> None:
    item = _get_or_404(db, prompt_id)
    db.delete(item)
    db.commit()
