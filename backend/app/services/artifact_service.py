from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import sanitize_filename
from app.models.artifact import Artifact
from app.schemas.artifact import (
    ArtifactCreateRequest,
    ArtifactListResponse,
    ArtifactResponse,
    ArtifactUpdateRequest,
)

EXPORT_EXTENSIONS: dict[str, tuple[str, str]] = {
    "document": (".md", "text/markdown; charset=utf-8"),
    "markdown": (".md", "text/markdown; charset=utf-8"),
    "code": (".txt", "text/plain; charset=utf-8"),
    "html": (".html", "text/html; charset=utf-8"),
    "json": (".json", "application/json; charset=utf-8"),
    "table": (".md", "text/markdown; charset=utf-8"),
    "csv": (".csv", "text/csv; charset=utf-8"),
    "text": (".txt", "text/plain; charset=utf-8"),
}

LANGUAGE_EXTENSIONS: dict[str, str] = {
    "python": ".py",
    "py": ".py",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "tsx": ".tsx",
    "html": ".html",
    "css": ".css",
    "sql": ".sql",
    "php": ".php",
    "json": ".json",
    "bash": ".sh",
    "sh": ".sh",
}


def _to_response(art: Artifact) -> ArtifactResponse:
    return ArtifactResponse(
        id=art.id,
        project_id=art.project_id,
        conversation_id=art.conversation_id,
        title=art.title,
        artifact_type=art.artifact_type,
        content=art.content,
        language=art.language,
        created_at=art.created_at,
        updated_at=art.updated_at,
    )


def _get_or_404(db: Session, artifact_id: str) -> Artifact:
    art = db.get(Artifact, artifact_id)
    if art is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found.",
        )
    return art


def list_artifacts(
    db: Session,
    project_id: str | None = None,
    artifact_type: str | None = None,
    search: str | None = None,
) -> ArtifactListResponse:
    query = select(Artifact)
    if project_id:
        query = query.where(Artifact.project_id == project_id)
    if artifact_type:
        query = query.where(Artifact.artifact_type == artifact_type)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Artifact.title.ilike(pattern),
                Artifact.content.ilike(pattern),
            )
        )

    rows = db.execute(query.order_by(Artifact.updated_at.desc())).scalars().all()
    return ArtifactListResponse(
        artifacts=[_to_response(a) for a in rows],
        total=len(rows),
    )


def get_artifact(db: Session, artifact_id: str) -> ArtifactResponse:
    return _to_response(_get_or_404(db, artifact_id))


def create_artifact(
    db: Session, payload: ArtifactCreateRequest
) -> ArtifactResponse:
    art = Artifact(
        title=payload.title.strip(),
        artifact_type=payload.artifact_type,
        content=payload.content,
        language=payload.language.strip() if payload.language else None,
        project_id=payload.project_id.strip() if payload.project_id else None,
        conversation_id=(
            payload.conversation_id.strip() if payload.conversation_id else None
        ),
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    return _to_response(art)


def update_artifact(
    db: Session, artifact_id: str, payload: ArtifactUpdateRequest
) -> ArtifactResponse:
    art = _get_or_404(db, artifact_id)
    if payload.title is not None:
        art.title = payload.title.strip()
    if payload.artifact_type is not None:
        art.artifact_type = payload.artifact_type
    if payload.content is not None:
        art.content = payload.content
    if payload.language is not None:
        art.language = payload.language.strip() or None
    if payload.project_id is not None:
        art.project_id = payload.project_id.strip() or None
    db.commit()
    db.refresh(art)
    return _to_response(art)


def duplicate_artifact(db: Session, artifact_id: str) -> ArtifactResponse:
    source = _get_or_404(db, artifact_id)
    copy_art = Artifact(
        title=f"{source.title} (Copy)",
        artifact_type=source.artifact_type,
        content=source.content,
        language=source.language,
        project_id=source.project_id,
        conversation_id=source.conversation_id,
    )
    db.add(copy_art)
    db.commit()
    db.refresh(copy_art)
    return _to_response(copy_art)


def delete_artifact(db: Session, artifact_id: str) -> None:
    art = _get_or_404(db, artifact_id)
    db.delete(art)
    db.commit()


def build_export_payload(
    db: Session, artifact_id: str
) -> tuple[str, str, str]:
    """Return (safe_filename, media_type, content) for artifact download."""
    art = _get_or_404(db, artifact_id)
    ext, media_type = EXPORT_EXTENSIONS.get(
        art.artifact_type, (".txt", "text/plain; charset=utf-8")
    )
    if art.artifact_type == "code" and art.language:
        ext = LANGUAGE_EXTENSIONS.get(art.language.lower(), ".txt")

    base = sanitize_filename(art.title.replace(" ", "_"))
    filename = base if base.lower().endswith(ext) else f"{base}{ext}"
    return filename, media_type, art.content
