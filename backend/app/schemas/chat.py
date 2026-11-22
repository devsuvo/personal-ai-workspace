from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationSummaryResponse(BaseModel):
    id: str
    title: str
    project_id: str | None = None
    provider_id: str | None = None
    model_name: str | None = None
    system_prompt: str
    is_pinned: bool = False
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummaryResponse]
    total: int
    limit: int
    offset: int


class ConversationCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    project_id: str | None = Field(default=None, max_length=36)
    provider_id: str | None = Field(default=None, max_length=64)
    model_name: str | None = Field(default=None, max_length=160)
    system_prompt: str = Field(default="", max_length=8000)


class ConversationUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    project_id: str | None = Field(default=None, max_length=36)
    provider_id: str | None = Field(default=None, max_length=64)
    model_name: str | None = Field(default=None, max_length=160)
    system_prompt: str | None = Field(default=None, max_length=8000)
    is_pinned: bool | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    provider_id: str | None = None
    provider_name: str | None = None
    model_id: str | None = None
    model_name: str | None = None
    credential_id: str | None = None
    status: str
    error_message: str | None = None
    token_usage: dict[str, Any] | None = None
    created_at: datetime


class MessageListResponse(BaseModel):
    conversation_id: str
    messages: list[MessageResponse]
    total: int
    limit: int
    offset: int


class MessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100_000)
    provider_id: str = Field(..., min_length=1, max_length=64)
    model_id: str = Field(..., min_length=1, max_length=160)
    credential_id: str | None = Field(default=None, max_length=36)
    attachment_ids: list[str] = Field(default_factory=list)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=200_000)


class MessageSendResponse(BaseModel):
    conversation: ConversationSummaryResponse
    user_message: MessageResponse
    assistant_message: MessageResponse
    context_truncated: bool = False
    excluded_messages_count: int = 0


class MessageUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=100_000)
    truncate_after: bool = Field(default=False)


class MessageRegenerateRequest(BaseModel):
    provider_id: str | None = Field(default=None, max_length=64)
    model_id: str | None = Field(default=None, max_length=160)
    credential_id: str | None = Field(default=None, max_length=36)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=200_000)


class ChatStreamRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=36)
    content: str | None = Field(default=None, max_length=100_000)
    provider_id: str = Field(..., min_length=1, max_length=64)
    model_id: str = Field(..., min_length=1, max_length=160)
    credential_id: str | None = Field(default=None, max_length=36)
    project_id: str | None = Field(default=None, max_length=36)
    attachment_ids: list[str] = Field(default_factory=list)
    system_prompt: str | None = Field(default=None, max_length=8000)
    regenerate_message_id: str | None = Field(default=None, max_length=36)
    edit_message_id: str | None = Field(default=None, max_length=36)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=200_000)
