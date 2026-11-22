export interface SettingItem {
  key: string;
  value: unknown;
  default_value: unknown;
  category: string;
  description: string;
  is_custom: boolean;
  updated_at: string | null;
}

export interface SettingsListResponse {
  settings: SettingItem[];
}

export interface SettingDeleteResponse {
  key: string;
  reset_to_default: boolean;
  default_value: unknown;
}

export interface BackupInfo {
  filename: string;
  size_bytes: number;
  created_at: string;
  relative_location: string;
}

export interface BackupListResponse {
  backups: BackupInfo[];
}

export interface BackupCreateResponse {
  backup: BackupInfo;
  message: string;
}

export interface BackupValidationResponse {
  filename: string;
  is_valid: boolean;
  integrity_check: string;
  schema_revision: string | null;
  detail: string;
}

export interface BackupRestoreResponse {
  restored_from: string;
  pre_restore_backup: string;
  database_connected: boolean;
  message: string;
}
