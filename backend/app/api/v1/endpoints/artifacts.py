from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.artifact import (
    ArtifactCreateRequest,
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactUpdateRequest,
)
from app.services import artifact_service

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


@router.get("", response_model=ArtifactListResponse, summary="List local artifacts")
def list_artifacts(
    project_id: str | None = Query(default=None),
    artifact_type: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
) -> ArtifactListResponse:
    return artifact_service.list_artifacts(
        db, project_id=project_id, artifact_type=artifact_type, search=search
    )


@router.post(
    "",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new local artifact",
)
def create_artifact(
    payload: ArtifactCreateRequest,
    db: Session = Depends(get_db),
) -> ArtifactResponse:
    return artifact_service.create_artifact(db, payload)


@router.get(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    summary="Get an artifact by ID",
)
def read_artifact(
    artifact_id: str, db: Session = Depends(get_db)
) -> ArtifactResponse:
    return artifact_service.get_artifact(db, artifact_id)


@router.put(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    summary="Update an artifact",
)
def update_artifact(
    artifact_id: str,
    payload: ArtifactUpdateRequest,
    db: Session = Depends(get_db),
) -> ArtifactResponse:
    return artifact_service.update_artifact(db, artifact_id, payload)


@router.post(
    "/{artifact_id}/duplicate",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate an existing artifact",
)
def duplicate_artifact(
    artifact_id: str, db: Session = Depends(get_db)
) -> ArtifactResponse:
    return artifact_service.duplicate_artifact(db, artifact_id)


@router.get(
    "/{artifact_id}/export",
    summary="Export and download an artifact as a file",
)
def export_artifact(
    artifact_id: str, db: Session = Depends(get_db)
) -> Response:
    filename, media_type, content = artifact_service.build_export_payload(
        db, artifact_id
    )
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.delete(
    "/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an artifact",
)
def delete_artifact(artifact_id: str, db: Session = Depends(get_db)) -> Response:
    artifact_service.delete_artifact(db, artifact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
