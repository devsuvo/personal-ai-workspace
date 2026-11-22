from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProviderCapabilitiesSchema(BaseModel):
    supports_model_listing: bool
    supports_streaming: bool
    supports_tools: bool
    supports_vision: bool
    requires_api_key: bool
    is_local: bool
    allows_custom_base_url: bool


class ProviderCatalogItem(BaseModel):
    provider_key: str
    name: str
    provider_type: str
    description: str
    default_base_url: str | None
    requires_api_key: bool
    is_local: bool
    allows_custom_base_url: bool
    supports_model_listing: bool
    capabilities: ProviderCapabilitiesSchema


class ProviderCatalogResponse(BaseModel):
    providers: list[ProviderCatalogItem]


class CredentialResponse(BaseModel):
    """Safe credential representation — NEVER includes plaintext or encrypted API keys."""

    id: str
    provider_id: str
    credential_name: str
    masked_api_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProviderModelResponse(BaseModel):
    id: str
    provider_id: str
    model_id: str
    display_name: str
    capabilities: dict[str, Any]
    is_available: bool
    is_manual: bool
    created_at: datetime
    updated_at: datetime


class ProviderSummaryResponse(BaseModel):
    id: str
    provider_key: str
    display_name: str
    provider_type: str
    base_url: str | None
    enabled: bool
    default_model: str | None
    connection_status: str
    last_tested_at: datetime | None
    last_error: str | None
    credentials_count: int
    models_count: int
    requires_api_key: bool
    is_local: bool
    supports_model_listing: bool
    created_at: datetime
    updated_at: datetime


class ProviderDetailResponse(ProviderSummaryResponse):
    credentials: list[CredentialResponse]
    models: list[ProviderModelResponse]
    capabilities: ProviderCapabilitiesSchema


class ProviderListResponse(BaseModel):
    providers: list[ProviderSummaryResponse]


class ProviderCreateRequest(BaseModel):
    provider_key: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=512)
    enabled: bool = Field(default=True)
    default_model: str | None = Field(default=None, max_length=160)
    api_key: str | None = Field(default=None, max_length=1024)
    credential_name: str = Field(default="Default Key", min_length=1, max_length=120)


class ProviderUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=512)
    enabled: bool | None = None
    default_model: str | None = Field(default=None, max_length=160)


class CredentialCreateRequest(BaseModel):
    credential_name: str = Field(default="Default Key", min_length=1, max_length=120)
    api_key: str = Field(..., min_length=1, max_length=1024)
    is_active: bool = Field(default=True)


class CredentialUpdateRequest(BaseModel):
    credential_name: str | None = Field(default=None, min_length=1, max_length=120)
    api_key: str | None = Field(default=None, min_length=1, max_length=1024)
    is_active: bool | None = None


class ProviderTestResponse(BaseModel):
    provider_id: str
    success: bool
    connection_status: str
    message: str
    error_code: str | None = None
    latency_ms: int | None = None
    models_found: int | None = None
    tested_at: datetime


class ProviderModelsListResponse(BaseModel):
    provider_id: str
    supports_model_listing: bool
    models: list[ProviderModelResponse]
    discovery_warning: str | None = None


class ProviderModelCreateRequest(BaseModel):
    model_id: str = Field(..., min_length=1, max_length=160)
    display_name: str | None = Field(default=None, max_length=160)
    capabilities: dict[str, Any] | None = None
    is_available: bool = Field(default=True)


class ProviderModelUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    is_available: bool | None = None


class DefaultModelUpdateRequest(BaseModel):
    model_id: str | None = Field(default=None, max_length=160)
