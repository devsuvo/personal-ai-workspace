import { useEffect, useState } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
export type ThemeMode = 'light' | 'dark';

const STORAGE_KEY = 'paw_theme_mode';

function resolveEffectiveTheme(pref: ThemePreference): ThemeMode {
  if (pref === 'light' || pref === 'dark') {
    return pref;
  }
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }
  return 'light';
}

function getInitialPreference(): ThemePreference {
  if (typeof window === 'undefined') {
    return 'light';
  }
  const saved = window.localStorage.getItem(STORAGE_KEY);
  if (saved === 'light' || saved === 'dark' || saved === 'system') {
    return saved;
  }
  return 'light';
}

export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(getInitialPreference);
  const [effectiveTheme, setEffectiveTheme] = useState<ThemeMode>(() =>
    resolveEffectiveTheme(getInitialPreference())
  );

  useEffect(() => {
    const apply = (pref: ThemePreference) => {
      const resolved = resolveEffectiveTheme(pref);
      setEffectiveTheme(resolved);
      const root = document.documentElement;
      if (resolved === 'dark') {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    };

    apply(preference);
    window.localStorage.setItem(STORAGE_KEY, preference);

    if (preference === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      const listener = () => apply('system');
      media.addEventListener('change', listener);
      return () => media.removeEventListener('change', listener);
    }
    return undefined;
  }, [preference]);

  const toggleTheme = (): ThemePreference => {
    const next: ThemePreference = effectiveTheme === 'dark' ? 'light' : 'dark';
    setPreference(next);
    return next;
  };

  return {
    theme: effectiveTheme,
    preference,
    setThemePreference: setPreference,
    toggleTheme,
  };
}
