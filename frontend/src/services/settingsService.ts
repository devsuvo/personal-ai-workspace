import type {
  BackupCreateResponse,
  BackupListResponse,
  BackupRestoreResponse,
  BackupValidationResponse,
  SettingDeleteResponse,
  SettingItem,
  SettingsListResponse,
} from '../types/settings';
import type {
  DatabaseStatusResponse,
  SecurityStatusResponse,
} from '../types/system';
import { apiRequest } from './apiClient';

export function fetchAllSettings(): Promise<SettingsListResponse> {
  return apiRequest<SettingsListResponse>('/settings');
}

export function updateSetting(
  key: string,
  value: unknown
): Promise<SettingItem> {
  return apiRequest<SettingItem>(`/settings/${encodeURIComponent(key)}`, {
    method: 'PUT',
    body: JSON.stringify({ value }),
  });
}

export function resetSetting(key: string): Promise<SettingDeleteResponse> {
  return apiRequest<SettingDeleteResponse>(
    `/settings/${encodeURIComponent(key)}`,
    { method: 'DELETE' }
  );
}

export function fetchDatabaseStatus(): Promise<DatabaseStatusResponse> {
  return apiRequest<DatabaseStatusResponse>('/system/database');
}

export function fetchSecurityStatus(): Promise<SecurityStatusResponse> {
  return apiRequest<SecurityStatusResponse>('/system/security');
}

export function listBackups(): Promise<BackupListResponse> {
  return apiRequest<BackupListResponse>('/system/backups');
}

export function createBackup(): Promise<BackupCreateResponse> {
  return apiRequest<BackupCreateResponse>('/system/backups', {
    method: 'POST',
  });
}

export function validateBackup(
  filename: string
): Promise<BackupValidationResponse> {
  return apiRequest<BackupValidationResponse>(
    `/system/backups/${encodeURIComponent(filename)}/validate`,
    { method: 'POST' }
  );
}

export function restoreBackup(
  filename: string,
  confirm: boolean
): Promise<BackupRestoreResponse> {
  return apiRequest<BackupRestoreResponse>(
    `/system/backups/${encodeURIComponent(filename)}/restore`,
    {
      method: 'POST',
      body: JSON.stringify({ confirm }),
    }
  );
}

export function clearLocalData(
  scope: 'conversations' | 'usage_logs' | 'all_workspace_data',
  confirm: boolean
): Promise<{ scope: string; pre_clear_backup: string; message: string }> {
  return apiRequest<{ scope: string; pre_clear_backup: string; message: string }>(
    '/system/backups/clear-data',
    {
      method: 'POST',
      body: JSON.stringify({ scope, confirm }),
    }
  );
}
