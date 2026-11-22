from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectSummaryResponse,
    ProjectUpdateRequest,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse, summary="List local projects")
def list_projects(
    search: str | None = Query(default=None, max_length=200),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    return project_service.list_projects(
        db, search=search, include_archived=include_archived
    )


@router.post(
    "",
    response_model=ProjectSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
) -> ProjectSummaryResponse:
    return project_service.create_project(db, payload)


@router.get(
    "/{project_id}",
    response_model=ProjectSummaryResponse,
    summary="Get project details and activity counts",
)
def read_project(
    project_id: str, db: Session = Depends(get_db)
) -> ProjectSummaryResponse:
    return project_service.get_project(db, project_id)


@router.put(
    "/{project_id}",
    response_model=ProjectSummaryResponse,
    summary="Update project name, description, icon, color, or AI instructions",
)
def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    db: Session = Depends(get_db),
) -> ProjectSummaryResponse:
    return project_service.update_project(db, project_id, payload)


@router.post(
    "/{project_id}/archive",
    response_model=ProjectSummaryResponse,
    summary="Archive a project",
)
def archive_project(
    project_id: str, db: Session = Depends(get_db)
) -> ProjectSummaryResponse:
    return project_service.archive_project(db, project_id)


@router.post(
    "/{project_id}/restore",
    response_model=ProjectSummaryResponse,
    summary="Restore an archived project",
)
def restore_project(
    project_id: str, db: Session = Depends(get_db)
) -> ProjectSummaryResponse:
    return project_service.restore_project(db, project_id)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project (conversations, files, and artifacts are preserved)",
)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> Response:
    project_service.delete_project(db, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
