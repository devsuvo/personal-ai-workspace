import type { HealthResponse, SystemInfoResponse } from '../types/system';
import { apiRequest } from './apiClient';

export function fetchHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>('/health');
}

export function fetchSystemInfo(): Promise<SystemInfoResponse> {
  return apiRequest<SystemInfoResponse>('/system/info');
}
