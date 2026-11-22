from datetime import datetime

from pydantic import BaseModel, Field


class ProjectSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    instructions: str
    icon: str
    color: str
    is_archived: bool
    conversations_count: int = 0
    files_count: int = 0
    artifacts_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectSummaryResponse]
    total: int


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    instructions: str = Field(default="", max_length=12000)
    icon: str = Field(default="folder", max_length=40)
    color: str = Field(default="terracotta", max_length=32)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    instructions: str | None = Field(default=None, max_length=12000)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=32)
