import logging
from pathlib import Path
from uuid import uuid4

import docx
import fitz  # PyMuPDF
from fastapi import HTTPException, UploadFile, status
import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    PathValidationError,
    sanitize_filename,
    validate_safe_path,
)
from app.models.attachment import Attachment
from app.schemas.file import (
    FileDetailResponse,
    FileListResponse,
    FileMetadataResponse,
    FileUpdateRequest,
)
from app.services import settings_service

logger = logging.getLogger("workspace.files")

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".php",
    ".sql",
}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".xlsx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_EXTENSIONS = TEXT_EXTENSIONS | DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

PREVIEW_CHAR_LIMIT = 24_000


def _extracted_dir(settings: Settings) -> Path:
    path = settings.uploads_dir_path / "extracted"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_image(filename: str, mime_type: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in IMAGE_EXTENSIONS or mime_type.startswith("image/")


def _to_metadata(att: Attachment) -> FileMetadataResponse:
    return FileMetadataResponse(
        id=att.id,
        project_id=att.project_id,
        conversation_id=att.conversation_id,
        original_filename=att.original_filename,
        mime_type=att.mime_type,
        file_size=att.file_size,
        extraction_status=att.extraction_status,
        extraction_error=att.extraction_error,
        has_extracted_text=bool(att.extracted_text_reference),
        is_image=_is_image(att.original_filename, att.mime_type),
        created_at=att.created_at,
    )


def _get_or_404(db: Session, file_id: str) -> Attachment:
    att = db.get(Attachment, file_id)
    if att is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
    return att


def resolve_stored_file_path(settings: Settings, att: Attachment) -> Path:
    """Safely resolve the original uploaded file inside storage/uploads/."""
    try:
        return validate_safe_path(settings.uploads_dir_path, att.stored_filename)
    except PathValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def read_extracted_text(settings: Settings, att: Attachment) -> str | None:
    """Safely read extracted UTF-8 text for an attachment if present."""
    if not att.extracted_text_reference:
        return None
    try:
        extracted_path = validate_safe_path(
            _extracted_dir(settings), Path(att.extracted_text_reference).name
        )
    except PathValidationError:
        return None
    if not extracted_path.exists():
        return None
    return extracted_path.read_text(encoding="utf-8", errors="replace")


def _extract_pdf_text(file_path: Path) -> tuple[str, str, str | None]:
    doc = fitz.open(str(file_path))
    try:
        pages_text: list[str] = []
        for idx, page in enumerate(doc, start=1):
            text = (page.get_text("text") or "").strip()
            if text:
                pages_text.append(f"--- Page {idx} ---\n{text}")
        if not pages_text:
            return (
                "ocr_required",
                "",
                "No selectable text was found in this PDF. It appears to be scanned/image-based and requires OCR.",
            )
        return "completed", "\n\n".join(pages_text), None
    finally:
        doc.close()


def _extract_docx_text(file_path: Path) -> tuple[str, str, str | None]:
    document = docx.Document(str(file_path))
    parts: list[str] = []
    for p in document.paragraphs:
        if p.text.strip():
            parts.append(p.text.strip())
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "completed", "\n\n".join(parts), None


def _extract_xlsx_text(file_path: Path) -> tuple[str, str, str | None]:
    wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
    try:
        sheets: list[str] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            lines = [f"### Sheet: {sheet_name}"]
            for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                if row_idx > 2000:
                    lines.append("... (truncated after 2,000 rows)")
                    break
                values = ["" if v is None else str(v) for v in row]
                if any(v.strip() for v in values):
                    lines.append(" | ".join(values))
            sheets.append("\n".join(lines))
        return "completed", "\n\n".join(sheets), None
    finally:
        wb.close()


def run_extraction_for_attachment(
    db: Session, settings: Settings, att: Attachment
) -> Attachment:
    """Extract text from a locally stored attachment without modifying the original file."""
    file_path = resolve_stored_file_path(settings, att)
    if not file_path.exists():
        att.extraction_status = "failed"
        att.extraction_error = "Stored file is missing from local storage."
        db.commit()
        return att

    ext = Path(att.original_filename).suffix.lower()

    try:
        if ext in IMAGE_EXTENSIONS:
            att.extraction_status = "unsupported"
            att.extraction_error = (
                "Image files support visual preview; text extraction/OCR is not enabled."
            )
            att.extracted_text_reference = None
        elif ext in TEXT_EXTENSIONS:
            extracted = file_path.read_text(encoding="utf-8", errors="replace")
            out_file = _extracted_dir(settings) / f"{att.id}.txt"
            out_file.write_text(extracted, encoding="utf-8")
            att.extraction_status = "completed"
            att.extracted_text_reference = settings.relative_storage_label(out_file)
            att.extraction_error = None
        elif ext == ".pdf":
            status_val, extracted, err = _extract_pdf_text(file_path)
            att.extraction_status = status_val
            att.extraction_error = err
            if status_val == "completed":
                out_file = _extracted_dir(settings) / f"{att.id}.txt"
                out_file.write_text(extracted, encoding="utf-8")
                att.extracted_text_reference = settings.relative_storage_label(out_file)
            else:
                att.extracted_text_reference = None
        elif ext == ".docx":
            status_val, extracted, err = _extract_docx_text(file_path)
            att.extraction_status = status_val
            att.extraction_error = err
            out_file = _extracted_dir(settings) / f"{att.id}.txt"
            out_file.write_text(extracted, encoding="utf-8")
            att.extracted_text_reference = settings.relative_storage_label(out_file)
        elif ext == ".xlsx":
            status_val, extracted, err = _extract_xlsx_text(file_path)
            att.extraction_status = status_val
            att.extraction_error = err
            out_file = _extracted_dir(settings) / f"{att.id}.txt"
            out_file.write_text(extracted, encoding="utf-8")
            att.extracted_text_reference = settings.relative_storage_label(out_file)
        else:
            att.extraction_status = "unsupported"
            att.extraction_error = f"Text extraction is not supported for '{ext}' files."
            att.extracted_text_reference = None
    except Exception as exc:
        logger.exception("Document extraction failed for %s: %s", att.id, exc)
        att.extraction_status = "failed"
        att.extraction_error = "Text extraction failed due to an unreadable or malformed file."
        att.extracted_text_reference = None

    db.commit()
    db.refresh(att)
    return att


async def upload_file(
    db: Session,
    settings: Settings,
    file: UploadFile,
    project_id: str | None = None,
    conversation_id: str | None = None,
) -> FileDetailResponse:
    settings.ensure_storage_directories()
    raw_name = file.filename or ""
    try:
        clean_original = sanitize_filename(raw_name)
    except PathValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    ext = Path(clean_original).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext or 'unknown'}' is not supported for upload.",
        )

    max_mb = int(settings_service.get_setting(db, "max_upload_size_mb").value or 25)
    max_bytes = max_mb * 1024 * 1024

    content_bytes = await file.read()
    file_size = len(content_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the configured upload limit of {max_mb} MB.",
        )

    stored_name = f"{uuid4().hex}_{clean_original}"
    destination = validate_safe_path(settings.uploads_dir_path, stored_name)
    destination.write_bytes(content_bytes)

    att = Attachment(
        project_id=project_id.strip() if project_id else None,
        conversation_id=conversation_id.strip() if conversation_id else None,
        original_filename=clean_original,
        stored_filename=stored_name,
        mime_type=file.content_type or "application/octet-stream",
        file_size=file_size,
        storage_path=settings.relative_storage_label(destination),
        extraction_status="pending",
    )
    db.add(att)
    db.commit()
    db.refresh(att)

    # Extract text immediately for supported formats
    att = run_extraction_for_attachment(db, settings, att)
    return get_file_detail(db, settings, att.id)


def list_files(
    db: Session,
    project_id: str | None = None,
    conversation_id: str | None = None,
    search: str | None = None,
) -> FileListResponse:
    query = select(Attachment)
    if project_id:
        query = query.where(Attachment.project_id == project_id)
    if conversation_id:
        query = query.where(Attachment.conversation_id == conversation_id)
    if search and search.strip():
        query = query.where(
            Attachment.original_filename.ilike(f"%{search.strip()}%")
        )

    rows = db.execute(query.order_by(Attachment.created_at.desc())).scalars().all()
    return FileListResponse(
        files=[_to_metadata(a) for a in rows],
        total=len(rows),
    )


def get_file_detail(
    db: Session, settings: Settings, file_id: str
) -> FileDetailResponse:
    att = _get_or_404(db, file_id)
    meta = _to_metadata(att)
    text = read_extracted_text(settings, att)
    preview = text[:PREVIEW_CHAR_LIMIT] if text is not None else None
    return FileDetailResponse(
        **meta.model_dump(),
        extracted_text_preview=preview,
    )


def update_file(
    db: Session,
    settings: Settings,
    file_id: str,
    payload: FileUpdateRequest,
) -> FileDetailResponse:
    att = _get_or_404(db, file_id)
    if payload.original_filename is not None:
        try:
            att.original_filename = sanitize_filename(payload.original_filename)
        except PathValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
    if payload.project_id is not None:
        att.project_id = payload.project_id.strip() or None
    if payload.conversation_id is not None:
        att.conversation_id = payload.conversation_id.strip() or None
    db.commit()
    db.refresh(att)
    return get_file_detail(db, settings, att.id)


def delete_file(db: Session, settings: Settings, file_id: str) -> None:
    att = _get_or_404(db, file_id)
    stored_path = resolve_stored_file_path(settings, att)
    if stored_path.exists():
        stored_path.unlink(missing_ok=True)
    if att.extracted_text_reference:
        try:
            extracted_path = validate_safe_path(
                _extracted_dir(settings), Path(att.extracted_text_reference).name
            )
            extracted_path.unlink(missing_ok=True)
        except PathValidationError:
            pass
    db.delete(att)
    db.commit()
