from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.schemas.file import (
    FileDetailResponse,
    FileListResponse,
    FileUpdateRequest,
)
from app.services import file_service

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("", response_model=FileListResponse, summary="List locally uploaded files")
def list_files(
    project_id: str | None = Query(default=None),
    conversation_id: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
) -> FileListResponse:
    return file_service.list_files(
        db,
        project_id=project_id,
        conversation_id=conversation_id,
        search=search,
    )


@router.post(
    "/upload",
    response_model=FileDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file to local storage and extract text when supported",
)
async def upload_file(
    file: UploadFile = File(...),
    project_id: str | None = Form(default=None),
    conversation_id: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> FileDetailResponse:
    return await file_service.upload_file(
        db,
        settings,
        file,
        project_id=project_id,
        conversation_id=conversation_id,
    )


@router.get(
    "/{file_id}",
    response_model=FileDetailResponse,
    summary="Get file metadata and extracted text preview",
)
def read_file_detail(
    file_id: str,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> FileDetailResponse:
    return file_service.get_file_detail(db, settings, file_id)


@router.put(
    "/{file_id}",
    response_model=FileDetailResponse,
    summary="Rename a file or associate it with a project/conversation",
)
def update_file(
    file_id: str,
    payload: FileUpdateRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> FileDetailResponse:
    return file_service.update_file(db, settings, file_id, payload)


@router.get(
    "/{file_id}/download",
    summary="Download the original uploaded file safely",
)
def download_file(
    file_id: str,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> FileResponse:
    att = file_service._get_or_404(db, file_id)
    stored_path = file_service.resolve_stored_file_path(settings, att)
    return FileResponse(
        path=str(stored_path),
        media_type=att.mime_type,
        filename=att.original_filename,
    )


@router.post(
    "/{file_id}/extract",
    response_model=FileDetailResponse,
    summary="Run or re-run text extraction for an uploaded file",
)
def extract_file_text(
    file_id: str,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> FileDetailResponse:
    att = file_service._get_or_404(db, file_id)
    file_service.run_extraction_for_attachment(db, settings, att)
    return file_service.get_file_detail(db, settings, file_id)


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a local file and its extracted text",
)
def remove_file(
    file_id: str,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> Response:
    file_service.delete_file(db, settings, file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
