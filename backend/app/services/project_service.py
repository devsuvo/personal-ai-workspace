from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.artifact import Artifact
from app.models.attachment import Attachment
from app.models.conversation import Conversation
from app.models.project import Project
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectSummaryResponse,
    ProjectUpdateRequest,
)


def _load_counts(
    db: Session, project_ids: list[str]
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    if not project_ids:
        return {}, {}, {}

    conv_rows = db.execute(
        select(Conversation.project_id, func.count(Conversation.id))
        .where(Conversation.project_id.in_(project_ids))
        .group_by(Conversation.project_id)
    ).all()
    file_rows = db.execute(
        select(Attachment.project_id, func.count(Attachment.id))
        .where(Attachment.project_id.in_(project_ids))
        .group_by(Attachment.project_id)
    ).all()
    art_rows = db.execute(
        select(Artifact.project_id, func.count(Artifact.id))
        .where(Artifact.project_id.in_(project_ids))
        .group_by(Artifact.project_id)
    ).all()

    return (
        {pid: int(cnt) for pid, cnt in conv_rows if pid},
        {pid: int(cnt) for pid, cnt in file_rows if pid},
        {pid: int(cnt) for pid, cnt in art_rows if pid},
    )


def _to_summary(
    project: Project,
    convs: int = 0,
    files: int = 0,
    arts: int = 0,
) -> ProjectSummaryResponse:
    return ProjectSummaryResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        instructions=project.instructions,
        icon=project.icon,
        color=project.color,
        is_archived=project.is_archived,
        conversations_count=convs,
        files_count=files,
        artifacts_count=arts,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _get_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return project


def list_projects(
    db: Session,
    search: str | None = None,
    include_archived: bool = False,
) -> ProjectListResponse:
    query = select(Project)
    if not include_archived:
        query = query.where(Project.is_archived.is_(False))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Project.name.ilike(pattern),
                Project.description.ilike(pattern),
            )
        )

    rows = db.execute(query.order_by(Project.updated_at.desc())).scalars().all()
    ids = [p.id for p in rows]
    c_map, f_map, a_map = _load_counts(db, ids)

    return ProjectListResponse(
        projects=[
            _to_summary(
                p,
                convs=c_map.get(p.id, 0),
                files=f_map.get(p.id, 0),
                arts=a_map.get(p.id, 0),
            )
            for p in rows
        ],
        total=len(rows),
    )


def get_project(db: Session, project_id: str) -> ProjectSummaryResponse:
    project = _get_or_404(db, project_id)
    c_map, f_map, a_map = _load_counts(db, [project.id])
    return _to_summary(
        project,
        convs=c_map.get(project.id, 0),
        files=f_map.get(project.id, 0),
        arts=a_map.get(project.id, 0),
    )


def create_project(
    db: Session, payload: ProjectCreateRequest
) -> ProjectSummaryResponse:
    project = Project(
        name=payload.name.strip(),
        description=payload.description.strip(),
        instructions=payload.instructions.strip(),
        icon=payload.icon.strip() or "folder",
        color=payload.color.strip() or "terracotta",
        is_archived=False,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_summary(project)


def update_project(
    db: Session, project_id: str, payload: ProjectUpdateRequest
) -> ProjectSummaryResponse:
    project = _get_or_404(db, project_id)
    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description.strip()
    if payload.instructions is not None:
        project.instructions = payload.instructions.strip()
    if payload.icon is not None:
        project.icon = payload.icon.strip() or "folder"
    if payload.color is not None:
        project.color = payload.color.strip() or "terracotta"
    db.commit()
    db.refresh(project)
    return get_project(db, project.id)


def archive_project(db: Session, project_id: str) -> ProjectSummaryResponse:
    project = _get_or_404(db, project_id)
    project.is_archived = True
    db.commit()
    return get_project(db, project.id)


def restore_project(db: Session, project_id: str) -> ProjectSummaryResponse:
    project = _get_or_404(db, project_id)
    project.is_archived = False
    db.commit()
    return get_project(db, project.id)


def delete_project(db: Session, project_id: str) -> None:
    """Delete a project; associated conversations, files, and artifacts are preserved (project_id set to NULL)."""
    project = _get_or_404(db, project_id)
    db.delete(project)
    db.commit()
