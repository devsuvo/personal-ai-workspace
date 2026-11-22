import { useCallback, useEffect, useState } from 'react';
import { fetchHealth, fetchSystemInfo } from '../services/systemService';
import type { HealthResponse, SystemInfoResponse } from '../types/system';

export interface SystemStatusState {
  health: HealthResponse | null;
  systemInfo: SystemInfoResponse | null;
  loading: boolean;
  error: string | null;
  lastCheckedAt: Date | null;
  refresh: () => Promise<void>;
}

export function useSystemStatus(): SystemStatusState {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, infoData] = await Promise.all([
        fetchHealth(),
        fetchSystemInfo(),
      ]);
      setHealth(healthData);
      setSystemInfo(infoData);
      setLastCheckedAt(new Date());
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to connect to local backend.';
      setError(message);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return {
    health,
    systemInfo,
    loading,
    error,
    lastCheckedAt,
    refresh,
  };
}
