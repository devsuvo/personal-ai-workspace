from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.attachment import Attachment
from app.services.file_service import read_extracted_text

DEFAULT_FILE_CONTEXT_CHAR_BUDGET = 32_000


@dataclass(frozen=True)
class FileContextResult:
    context_text: str
    included_files: list[str]
    skipped_files: list[dict[str, str]]
    truncated: bool


def build_file_context(
    db: Session,
    settings: Settings,
    file_ids: list[str],
    char_budget: int = DEFAULT_FILE_CONTEXT_CHAR_BUDGET,
) -> FileContextResult:
    """Build a bounded, transparent text context block from extracted attachment texts."""
    if not file_ids:
        return FileContextResult(
            context_text="",
            included_files=[],
            skipped_files=[],
            truncated=False,
        )

    rows = (
        db.execute(select(Attachment).where(Attachment.id.in_(file_ids)))
        .scalars()
        .all()
    )
    by_id = {row.id: row for row in rows}

    sections: list[str] = []
    included: list[str] = []
    skipped: list[dict[str, str]] = []
    remaining = max(1000, char_budget)
    truncated = False

    for fid in file_ids:
        att = by_id.get(fid)
        if att is None:
            skipped.append({"file": fid, "reason": "File not found"})
            continue

        if att.extraction_status != "completed":
            reason = att.extraction_error or f"Status: {att.extraction_status}"
            skipped.append({"file": att.original_filename, "reason": reason})
            continue

        extracted = read_extracted_text(settings, att)
        if not extracted or not extracted.strip():
            skipped.append(
                {"file": att.original_filename, "reason": "No extracted text available"}
            )
            continue

        header = f"=== Attached File: {att.original_filename} ===\n"
        if remaining <= len(header) + 100:
            truncated = True
            skipped.append(
                {
                    "file": att.original_filename,
                    "reason": "Excluded to stay within context window budget",
                }
            )
            continue

        allowed_body = remaining - len(header)
        body = extracted
        if len(body) > allowed_body:
            body = body[:allowed_body] + "\n... [file content truncated to fit context window]"
            truncated = True

        sections.append(f"{header}{body}")
        included.append(att.original_filename)
        remaining -= len(header) + len(body)

    context_text = "\n\n".join(sections)
    return FileContextResult(
        context_text=context_text,
        included_files=included,
        skipped_files=skipped,
        truncated=truncated,
    )
