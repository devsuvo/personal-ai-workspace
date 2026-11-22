from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- AI Tools ---

class AIToolDefinition(BaseModel):
    id: str
    name: str
    description: str
    category: str
    input_label: str
    input_placeholder: str
    options: list[dict[str, Any]] = Field(default_factory=list)


class AIToolListResponse(BaseModel):
    tools: list[AIToolDefinition]


class AIToolRunRequest(BaseModel):
    tool_id: str = Field(..., min_length=1, max_length=64)
    input_text: str = Field(..., min_length=1, max_length=100_000)
    provider_id: str = Field(..., min_length=1, max_length=64)
    model_id: str = Field(..., min_length=1, max_length=160)
    credential_id: str | None = Field(default=None, max_length=36)
    options: dict[str, str] = Field(default_factory=dict)


class AIToolRunResponse(BaseModel):
    tool_id: str
    output: str
    provider_name: str
    model_id: str
    token_usage: dict[str, Any] | None = None


# --- Prompt Library ---

class PromptTemplateResponse(BaseModel):
    id: str
    title: str
    category: str
    description: str
    content: str
    is_favorite: bool
    created_at: datetime
    updated_at: datetime


class PromptTemplateListResponse(BaseModel):
    prompts: list[PromptTemplateResponse]
    categories: list[str]
    total: int


class PromptTemplateCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    category: str = Field(default="General", min_length=1, max_length=64)
    description: str = Field(default="", max_length=500)
    content: str = Field(..., min_length=1, max_length=20_000)
    is_favorite: bool = Field(default=False)


class PromptTemplateUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=500)
    content: str | None = Field(default=None, min_length=1, max_length=20_000)
    is_favorite: bool | None = None


# --- Analytics & Pricing ---

class ModelPricingResponse(BaseModel):
    id: str
    provider_name: str
    model_name: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    updated_at: datetime


class ModelPricingListResponse(BaseModel):
    pricing: list[ModelPricingResponse]


class ModelPricingUpsertRequest(BaseModel):
    provider_name: str = Field(..., min_length=1, max_length=80)
    model_name: str = Field(..., min_length=1, max_length=160)
    input_cost_per_1m: float = Field(..., ge=0.0, le=10000.0)
    output_cost_per_1m: float = Field(..., ge=0.0, le=10000.0)


class ModelUsageBreakdown(BaseModel):
    provider_name: str
    model_name: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float | None = None


class PeriodUsagePoint(BaseModel):
    period: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int


class AnalyticsOverviewResponse(BaseModel):
    total_conversations: int
    total_messages: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_total_cost: float | None = None
    has_configured_pricing: bool
    top_models: list[ModelUsageBreakdown]
    daily_usage: list[PeriodUsagePoint]
    monthly_usage: list[PeriodUsagePoint]
