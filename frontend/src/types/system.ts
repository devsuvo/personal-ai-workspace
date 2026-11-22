export interface ComponentCheck {
  status: 'ok' | 'error';
  detail: string | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
  uptime_seconds: number;
  configured_providers: number;
  checks: {
    database: ComponentCheck;
    storage: ComponentCheck;
  };
}

export interface ProviderSummary {
  id: string;
  name: string;
  description: string;
  requires_api_key: boolean;
  is_local: boolean;
  configured: boolean;
  implemented: boolean;
}

export interface RuntimeInfo {
  os: string;
  os_release: string;
  machine: string;
  python_version: string;
}

export interface StorageInfo {
  storage_dir: string;
  database_path: string;
  uploads_dir: string;
  exports_dir: string;
  backups_dir: string;
  database_connected: boolean;
}

export interface SystemInfoResponse {
  app_name: string;
  version: string;
  environment: string;
  phase: string;
  api_prefix: string;
  local_only: boolean;
  configured_providers_count: number;
  planned_providers_count: number;
  runtime: RuntimeInfo;
  storage: StorageInfo;
  planned_providers: ProviderSummary[];
}

export interface MigrationStatus {
  current_revision: string | null;
  head_revision: string | null;
  is_up_to_date: boolean;
}

export interface DatabaseStatusResponse {
  connected: boolean;
  database_type: string;
  database_size_bytes: number;
  relative_location: string;
  table_count: number;
  migration_status: MigrationStatus;
}

export interface SecurityStatusResponse {
  encryption_algorithm: string;
  master_key_initialized: boolean;
  key_source: string;
  key_storage_location: string;
  secrets_stored_outside_database: boolean;
  credential_management_status: string;
  backup_guidance: string;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
