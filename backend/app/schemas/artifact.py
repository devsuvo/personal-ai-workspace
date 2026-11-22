from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ArtifactType = Literal[
    "document",
    "markdown",
    "code",
    "html",
    "json",
    "table",
    "csv",
    "text",
]


class ArtifactResponse(BaseModel):
    id: str
    project_id: str | None = None
    conversation_id: str | None = None
    title: str
    artifact_type: str
    content: str
    language: str | None = None
    created_at: datetime
    updated_at: datetime


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactResponse]
    total: int


class ArtifactCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    artifact_type: ArtifactType = Field(default="markdown")
    content: str = Field(default="", max_length=500_000)
    language: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=36)
    conversation_id: str | None = Field(default=None, max_length=36)


class ArtifactUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    artifact_type: ArtifactType | None = None
    content: str | None = Field(default=None, max_length=500_000)
    language: str | None = Field(default=None, max_length=64)
    project_id: str | None = Field(default=None, max_length=36)
