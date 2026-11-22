from datetime import datetime

from pydantic import BaseModel, Field


class FileMetadataResponse(BaseModel):
    id: str
    project_id: str | None = None
    conversation_id: str | None = None
    original_filename: str
    mime_type: str
    file_size: int
    extraction_status: str
    extraction_error: str | None = None
    has_extracted_text: bool = False
    is_image: bool = False
    created_at: datetime


class FileDetailResponse(FileMetadataResponse):
    extracted_text_preview: str | None = None


class FileListResponse(BaseModel):
    files: list[FileMetadataResponse]
    total: int


class FileUpdateRequest(BaseModel):
    original_filename: str | None = Field(default=None, min_length=1, max_length=255)
    project_id: str | None = Field(default=None, max_length=36)
    conversation_id: str | None = Field(default=None, max_length=36)
