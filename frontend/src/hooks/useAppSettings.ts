import { useCallback, useEffect, useState } from 'react';
import {
  fetchAllSettings,
  resetSetting,
  updateSetting,
} from '../services/settingsService';
import type { SettingItem } from '../types/settings';

export interface AppSettingsState {
  items: Record<string, SettingItem>;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  saveSetting: (key: string, value: unknown) => Promise<SettingItem>;
  resetToDefault: (key: string) => Promise<void>;
}

export function useAppSettings(): AppSettingsState {
  const [items, setItems] = useState<Record<string, SettingItem>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAllSettings();
      const map: Record<string, SettingItem> = {};
      for (const item of res.settings) {
        map[item.key] = item;
      }
      setItems(map);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load workspace settings.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const saveSetting = useCallback(
    async (key: string, value: unknown): Promise<SettingItem> => {
      const updated = await updateSetting(key, value);
      setItems((prev) => ({ ...prev, [key]: updated }));
      return updated;
    },
    []
  );

  const resetToDefault = useCallback(
    async (key: string): Promise<void> => {
      await resetSetting(key);
      await reload();
    },
    [reload]
  );

  return {
    items,
    loading,
    error,
    reload,
    saveSetting,
    resetToDefault,
  };
}
