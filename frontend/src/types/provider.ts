export interface ProviderCapabilities {
  supports_model_listing: boolean;
  supports_streaming: boolean;
  supports_tools: boolean;
  supports_vision: boolean;
  requires_api_key: boolean;
  is_local: boolean;
  allows_custom_base_url: boolean;
}

export interface ProviderCatalogItem {
  provider_key: string;
  name: string;
  provider_type: string;
  description: string;
  default_base_url: string | null;
  requires_api_key: boolean;
  is_local: boolean;
  allows_custom_base_url: boolean;
  supports_model_listing: boolean;
  capabilities: ProviderCapabilities;
}

export interface ProviderCredential {
  id: string;
  provider_id: string;
  credential_name: string;
  masked_api_key: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProviderModel {
  id: string;
  provider_id: string;
  model_id: string;
  display_name: string;
  capabilities: Record<string, unknown>;
  is_available: boolean;
  is_manual: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConfiguredProviderSummary {
  id: string;
  provider_key: string;
  display_name: string;
  provider_type: string;
  base_url: string | null;
  enabled: boolean;
  default_model: string | null;
  connection_status: string;
  last_tested_at: string | null;
  last_error: string | null;
  credentials_count: number;
  models_count: number;
  requires_api_key: boolean;
  is_local: boolean;
  supports_model_listing: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConfiguredProviderDetail extends ConfiguredProviderSummary {
  credentials: ProviderCredential[];
  models: ProviderModel[];
  capabilities: ProviderCapabilities;
}

export interface ProviderCreatePayload {
  provider_key: string;
  display_name: string;
  base_url?: string | null;
  enabled?: boolean;
  default_model?: string | null;
  api_key?: string | null;
  credential_name?: string;
}

export interface ProviderUpdatePayload {
  display_name?: string;
  base_url?: string | null;
  enabled?: boolean;
  default_model?: string | null;
}

export interface ProviderTestResult {
  provider_id: string;
  success: boolean;
  connection_status: string;
  message: string;
  error_code: string | null;
  latency_ms: number | null;
  models_found: number | null;
  tested_at: string;
}

export interface ProviderModelsResponse {
  provider_id: string;
  supports_model_listing: boolean;
  models: ProviderModel[];
  discovery_warning: string | null;
}
