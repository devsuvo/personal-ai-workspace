import type {
  ConfiguredProviderDetail,
  ConfiguredProviderSummary,
  ProviderCatalogItem,
  ProviderCreatePayload,
  ProviderCredential,
  ProviderModel,
  ProviderModelsResponse,
  ProviderTestResult,
  ProviderUpdatePayload,
} from '../types/provider';
import { apiRequest } from './apiClient';

export async function fetchProviderCatalog(): Promise<ProviderCatalogItem[]> {
  const res = await apiRequest<{ providers: ProviderCatalogItem[] }>(
    '/providers/registry'
  );
  return res.providers;
}

export async function fetchConfiguredProviders(): Promise<
  ConfiguredProviderSummary[]
> {
  const res = await apiRequest<{ providers: ConfiguredProviderSummary[] }>(
    '/providers'
  );
  return res.providers;
}

export function fetchProviderDetail(
  providerId: string
): Promise<ConfiguredProviderDetail> {
  return apiRequest<ConfiguredProviderDetail>(
    `/providers/${encodeURIComponent(providerId)}`
  );
}

export function createProvider(
  payload: ProviderCreatePayload
): Promise<ConfiguredProviderDetail> {
  return apiRequest<ConfiguredProviderDetail>('/providers', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateProvider(
  providerId: string,
  payload: ProviderUpdatePayload
): Promise<ConfiguredProviderDetail> {
  return apiRequest<ConfiguredProviderDetail>(
    `/providers/${encodeURIComponent(providerId)}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteProvider(providerId: string): Promise<void> {
  const res = await fetch(
    `${(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/+$/, '')}/providers/${encodeURIComponent(providerId)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) {
    throw new Error(`Failed to delete provider (HTTP ${res.status})`);
  }
}

export function addCredential(
  providerId: string,
  payload: { credential_name: string; api_key: string; is_active?: boolean }
): Promise<ProviderCredential> {
  return apiRequest<ProviderCredential>(
    `/providers/${encodeURIComponent(providerId)}/credentials`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  );
}

export function updateCredential(
  providerId: string,
  credentialId: string,
  payload: { credential_name?: string; api_key?: string; is_active?: boolean }
): Promise<ProviderCredential> {
  return apiRequest<ProviderCredential>(
    `/providers/${encodeURIComponent(providerId)}/credentials/${encodeURIComponent(credentialId)}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteCredential(
  providerId: string,
  credentialId: string
): Promise<void> {
  const res = await fetch(
    `${(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/+$/, '')}/providers/${encodeURIComponent(providerId)}/credentials/${encodeURIComponent(credentialId)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) {
    throw new Error(`Failed to delete credential (HTTP ${res.status})`);
  }
}

export function testProviderConnection(
  providerId: string
): Promise<ProviderTestResult> {
  return apiRequest<ProviderTestResult>(
    `/providers/${encodeURIComponent(providerId)}/test`,
    { method: 'POST' }
  );
}

export function fetchProviderModels(
  providerId: string,
  refresh = false
): Promise<ProviderModelsResponse> {
  return apiRequest<ProviderModelsResponse>(
    `/providers/${encodeURIComponent(providerId)}/models?refresh=${refresh ? 'true' : 'false'}`
  );
}

export function addProviderModel(
  providerId: string,
  payload: { model_id: string; display_name?: string }
): Promise<ProviderModel> {
  return apiRequest<ProviderModel>(
    `/providers/${encodeURIComponent(providerId)}/models`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  );
}

export function updateProviderModel(
  providerId: string,
  modelRecordId: string,
  payload: { display_name?: string; is_available?: boolean }
): Promise<ProviderModel> {
  return apiRequest<ProviderModel>(
    `/providers/${encodeURIComponent(providerId)}/models/${encodeURIComponent(modelRecordId)}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteProviderModel(
  providerId: string,
  modelRecordId: string
): Promise<void> {
  const res = await fetch(
    `${(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/+$/, '')}/providers/${encodeURIComponent(providerId)}/models/${encodeURIComponent(modelRecordId)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) {
    throw new Error(`Failed to delete model (HTTP ${res.status})`);
  }
}

export function setDefaultModel(
  providerId: string,
  modelId: string | null
): Promise<ConfiguredProviderDetail> {
  return apiRequest<ConfiguredProviderDetail>(
    `/providers/${encodeURIComponent(providerId)}/default-model`,
    {
      method: 'PUT',
      body: JSON.stringify({ model_id: modelId }),
    }
  );
}
