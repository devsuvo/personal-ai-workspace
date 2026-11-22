import {
  Archive,
  CheckCircle2,
  Database,
  HardDrive,
  Laptop,
  MessageSquare,
  Moon,
  RefreshCw,
  RotateCcw,
  Save,
  Shield,
  Sliders,
  Sun,
  XCircle,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { StatusBadge } from '../components/common/StatusBadge';
import type { AppSettingsState } from '../hooks/useAppSettings';
import type { SystemStatusState } from '../hooks/useSystemStatus';
import type { ThemePreference } from '../hooks/useTheme';
import {
  clearLocalData,
  createBackup,
  fetchDatabaseStatus,
  fetchSecurityStatus,
  listBackups,
  restoreBackup,
  validateBackup,
} from '../services/settingsService';
import type { BackupInfo, BackupValidationResponse } from '../types/settings';
import type {
  DatabaseStatusResponse,
  SecurityStatusResponse,
} from '../types/system';

type SettingsSection =
  | 'general'
  | 'appearance'
  | 'chat'
  | 'storage'
  | 'backup'
  | 'security';

interface SettingsPageProps {
  themePreference: ThemePreference;
  onChangeThemePreference: (pref: ThemePreference) => void;
  sidebarCollapsed: boolean;
  onChangeSidebarCollapsed: (collapsed: boolean) => void;
  appSettings: AppSettingsState;
  systemStatus: SystemStatusState;
}

const SECTIONS: { id: SettingsSection; label: string }[] = [
  { id: 'general', label: 'General' },
  { id: 'appearance', label: 'Appearance' },
  { id: 'chat', label: 'Chat Preferences' },
  { id: 'storage', label: 'Storage' },
  { id: 'backup', label: 'Data Backup' },
  { id: 'security', label: 'Security' },
];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function SettingsPage({
  themePreference,
  onChangeThemePreference,
  sidebarCollapsed,
  onChangeSidebarCollapsed,
  appSettings,
  systemStatus,
}: SettingsPageProps) {
  const [activeSection, setActiveSection] = useState<SettingsSection>('general');

  // Local form states synchronized from backend settings
  const [appName, setAppName] = useState('Personal AI Workspace');
  const [defaultProvider, setDefaultProvider] = useState('');
  const [defaultModel, setDefaultModel] = useState('');
  const [sendOnEnter, setSendOnEnter] = useState(true);
  const [streamResponses, setStreamResponses] = useState(true);
  const [showTokenUsage, setShowTokenUsage] = useState(true);
  const [defaultSystemPrompt, setDefaultSystemPrompt] = useState('');
  const [maxUploadMb, setMaxUploadMb] = useState(25);

  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  // Database, security, and backup diagnostics
  const [dbStatus, setDbStatus] = useState<DatabaseStatusResponse | null>(null);
  const [secStatus, setSecStatus] = useState<SecurityStatusResponse | null>(null);
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [validationMap, setValidationMap] = useState<
    Record<string, BackupValidationResponse>
  >({});
  const [confirmRestoreFile, setConfirmRestoreFile] = useState<string | null>(
    null
  );
  const [confirmClearScope, setConfirmClearScope] = useState<
    'conversations' | 'usage_logs' | 'all_workspace_data' | null
  >(null);
  const [backupBusy, setBackupBusy] = useState(false);

  useEffect(() => {
    const items = appSettings.items;
    if (items.app_name) setAppName(String(items.app_name.value ?? 'Personal AI Workspace'));
    if (items.default_provider) setDefaultProvider(String(items.default_provider.value ?? ''));
    if (items.default_model) setDefaultModel(String(items.default_model.value ?? ''));
    if (items.chat_send_on_enter) setSendOnEnter(Boolean(items.chat_send_on_enter.value));
    if (items.chat_stream_responses) setStreamResponses(Boolean(items.chat_stream_responses.value));
    if (items.chat_show_token_usage) setShowTokenUsage(Boolean(items.chat_show_token_usage.value));
    if (items.chat_default_system_prompt) {
      setDefaultSystemPrompt(String(items.chat_default_system_prompt.value ?? ''));
    }
    if (items.max_upload_size_mb) setMaxUploadMb(Number(items.max_upload_size_mb.value ?? 25));
  }, [appSettings.items]);

  const loadDiagnostics = useCallback(async () => {
    try {
      const [db, sec, bkp] = await Promise.all([
        fetchDatabaseStatus(),
        fetchSecurityStatus(),
        listBackups(),
      ]);
      setDbStatus(db);
      setSecStatus(sec);
      setBackups(bkp.backups);
    } catch {
      // Handled by systemStatus banner if backend is unreachable
    }
  }, []);

  useEffect(() => {
    void loadDiagnostics();
  }, [loadDiagnostics]);

  const saveEntries = async (entries: Array<[string, unknown]>, msg: string) => {
    setSaving(true);
    setFeedback(null);
    try {
      for (const [key, value] of entries) {
        await appSettings.saveSetting(key, value);
      }
      setFeedback({ type: 'success', text: msg });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to save settings.',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCreateBackup = async () => {
    setBackupBusy(true);
    setFeedback(null);
    try {
      const res = await createBackup();
      setFeedback({ type: 'success', text: res.message });
      await loadDiagnostics();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Backup creation failed.',
      });
    } finally {
      setBackupBusy(false);
    }
  };

  const handleValidateBackup = async (filename: string) => {
    setBackupBusy(true);
    try {
      const res = await validateBackup(filename);
      setValidationMap((prev) => ({ ...prev, [filename]: res }));
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Validation failed.',
      });
    } finally {
      setBackupBusy(false);
    }
  };

  const handleConfirmRestore = async (filename: string) => {
    setBackupBusy(true);
    setFeedback(null);
    try {
      const res = await restoreBackup(filename, true);
      setConfirmRestoreFile(null);
      setFeedback({ type: 'success', text: res.message });
      await Promise.all([
        appSettings.reload(),
        systemStatus.refresh(),
        loadDiagnostics(),
      ]);
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Restore failed.',
      });
    } finally {
      setBackupBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-ink-primary">Settings</h2>
        <p className="mt-1 text-sm text-ink-secondary">
          Configure local workspace behavior, appearance, SQLite storage,
          backups, and security.
        </p>
      </div>

      {/* Section tabs */}
      <div className="mb-6 flex flex-wrap gap-1.5 border-b border-border pb-3">
        {SECTIONS.map((sec) => (
          <button
            key={sec.id}
            type="button"
            onClick={() => {
              setActiveSection(sec.id);
              setFeedback(null);
            }}
            className={`rounded-xl px-3.5 py-1.5 text-xs font-medium transition-colors ${
              activeSection === sec.id
                ? 'bg-surface-elevated text-ink-primary shadow-sm ring-1 ring-border'
                : 'text-ink-secondary hover:bg-surface hover:text-ink-primary'
            }`}
          >
            {sec.label}
          </button>
        ))}
      </div>

      {feedback && (
        <div
          className={`mb-5 flex items-center gap-2 rounded-xl border px-4 py-3 text-xs ${
            feedback.type === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300'
          }`}
        >
          {feedback.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <XCircle className="h-4 w-4 shrink-0" />
          )}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* 1. General */}
      {activeSection === 'general' && (
        <section className="rounded-2xl border border-border bg-surface-elevated p-6 space-y-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
            <Sliders className="h-4 w-4 text-accent" />
            <span>General Workspace Settings</span>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink-secondary">
                Application Name
              </label>
              <input
                type="text"
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:border-border-strong focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink-secondary">
                Default Provider Key (Optional)
              </label>
              <input
                type="text"
                value={defaultProvider}
                onChange={(e) => setDefaultProvider(e.target.value)}
                placeholder="e.g. anthropic, openai, ollama"
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:border-border-strong focus:outline-none"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="mb-1.5 block text-xs font-medium text-ink-secondary">
                Default Model Identifier (Optional)
              </label>
              <input
                type="text"
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
                placeholder="e.g. claude-3-7-sonnet-20250219"
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 font-mono text-xs text-ink-primary focus:border-border-strong focus:outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end border-t border-border/70 pt-4">
            <button
              type="button"
              disabled={saving}
              onClick={() =>
                void saveEntries(
                  [
                    ['app_name', appName],
                    ['default_provider', defaultProvider || null],
                    ['default_model', defaultModel || null],
                  ],
                  'General settings saved to SQLite.'
                )
              }
              className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-60"
            >
              <Save className="h-3.5 w-3.5" />
              <span>{saving ? 'Saving...' : 'Save General Settings'}</span>
            </button>
          </div>
        </section>
      )}

      {/* 2. Appearance */}
      {activeSection === 'appearance' && (
        <section className="rounded-2xl border border-border bg-surface-elevated p-6 space-y-5">
          <div>
            <h3 className="text-sm font-semibold text-ink-primary">
              Theme Preference
            </h3>
            <p className="mt-1 text-xs text-ink-secondary">
              Persisted both locally in SQLite and in your browser for instant
              rendering.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 sm:max-w-md">
            {(
              [
                { id: 'light', label: 'Light', icon: Sun },
                { id: 'dark', label: 'Dark', icon: Moon },
                { id: 'system', label: 'System', icon: Laptop },
              ] as const
            ).map((opt) => {
              const Icon = opt.icon;
              const active = themePreference === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => {
                    onChangeThemePreference(opt.id);
                    void saveEntries(
                      [['theme', opt.id]],
                      `Theme updated to ${opt.label}.`
                    );
                  }}
                  className={`flex items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-xs font-medium transition-colors ${
                    active
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border bg-surface text-ink-secondary hover:border-border-strong hover:text-ink-primary'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{opt.label}</span>
                </button>
              );
            })}
          </div>

          <div className="border-t border-border/70 pt-4">
            <label className="flex items-center justify-between gap-4">
              <div>
                <div className="text-xs font-semibold text-ink-primary">
                  Start with collapsed sidebar
                </div>
                <div className="text-xs text-ink-secondary">
                  Keep more horizontal space for conversations on startup.
                </div>
              </div>
              <input
                type="checkbox"
                checked={sidebarCollapsed}
                onChange={(e) => {
                  const next = e.target.checked;
                  onChangeSidebarCollapsed(next);
                  void saveEntries(
                    [['sidebar_collapsed', next]],
                    'Sidebar preference saved.'
                  );
                }}
                className="h-4 w-4 accent-accent"
              />
            </label>
          </div>
        </section>
      )}

      {/* 3. Chat Preferences */}
      {activeSection === 'chat' && (
        <section className="rounded-2xl border border-border bg-surface-elevated p-6 space-y-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
            <MessageSquare className="h-4 w-4 text-accent" />
            <span>Chat Preferences</span>
          </div>

          <div className="space-y-3">
            <label className="flex items-center justify-between gap-4 rounded-xl border border-border bg-canvas/50 p-3.5">
              <div>
                <div className="text-xs font-semibold text-ink-primary">
                  Send message on Enter
                </div>
                <div className="text-xs text-ink-secondary">
                  Press Shift+Enter to insert a newline.
                </div>
              </div>
              <input
                type="checkbox"
                checked={sendOnEnter}
                onChange={(e) => setSendOnEnter(e.target.checked)}
                className="h-4 w-4 accent-accent"
              />
            </label>

            <label className="flex items-center justify-between gap-4 rounded-xl border border-border bg-canvas/50 p-3.5">
              <div>
                <div className="text-xs font-semibold text-ink-primary">
                  Stream AI responses
                </div>
                <div className="text-xs text-ink-secondary">
                  Display tokens progressively when supported by the provider.
                </div>
              </div>
              <input
                type="checkbox"
                checked={streamResponses}
                onChange={(e) => setStreamResponses(e.target.checked)}
                className="h-4 w-4 accent-accent"
              />
            </label>

            <label className="flex items-center justify-between gap-4 rounded-xl border border-border bg-canvas/50 p-3.5">
              <div>
                <div className="text-xs font-semibold text-ink-primary">
                  Show token usage metadata
                </div>
                <div className="text-xs text-ink-secondary">
                  Display input/output token counts on completed turns.
                </div>
              </div>
              <input
                type="checkbox"
                checked={showTokenUsage}
                onChange={(e) => setShowTokenUsage(e.target.checked)}
                className="h-4 w-4 accent-accent"
              />
            </label>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-secondary">
              Default System Prompt
            </label>
            <textarea
              rows={4}
              value={defaultSystemPrompt}
              onChange={(e) => setDefaultSystemPrompt(e.target.value)}
              placeholder="Optional instructions applied to new conversations..."
              className="w-full rounded-xl border border-border bg-canvas p-3 text-xs leading-relaxed text-ink-primary focus:border-border-strong focus:outline-none"
            />
          </div>

          <div className="flex justify-end border-t border-border/70 pt-4">
            <button
              type="button"
              disabled={saving}
              onClick={() =>
                void saveEntries(
                  [
                    ['chat_send_on_enter', sendOnEnter],
                    ['chat_stream_responses', streamResponses],
                    ['chat_show_token_usage', showTokenUsage],
                    ['chat_default_system_prompt', defaultSystemPrompt],
                  ],
                  'Chat preferences saved.'
                )
              }
              className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-60"
            >
              <Save className="h-3.5 w-3.5" />
              <span>{saving ? 'Saving...' : 'Save Chat Preferences'}</span>
            </button>
          </div>
        </section>
      )}

      {/* 4. Storage & Database Status */}
      {activeSection === 'storage' && (
        <section className="space-y-5">
          <div className="rounded-2xl border border-border bg-surface-elevated p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
                <Database className="h-4 w-4 text-accent" />
                <span>Local SQLite Database Status</span>
              </div>
              <button
                type="button"
                onClick={() => void loadDiagnostics()}
                className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs font-medium text-ink-primary hover:bg-surface-hover"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Refresh</span>
              </button>
            </div>

            {dbStatus ? (
              <dl className="divide-y divide-border/70 rounded-xl border border-border bg-canvas/50 text-xs">
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Connection</dt>
                  <dd>
                    <StatusBadge variant={dbStatus.connected ? 'success' : 'error'}>
                      {dbStatus.connected ? 'Connected' : 'Disconnected'}
                    </StatusBadge>
                  </dd>
                </div>
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Database Engine</dt>
                  <dd className="font-medium text-ink-primary">
                    {dbStatus.database_type} ({dbStatus.table_count} tables)
                  </dd>
                </div>
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Database Size</dt>
                  <dd className="font-medium text-ink-primary">
                    {formatBytes(dbStatus.database_size_bytes)}
                  </dd>
                </div>
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Relative Location</dt>
                  <dd className="font-mono text-[11px] text-ink-secondary">
                    {dbStatus.relative_location}
                  </dd>
                </div>
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Schema Migration</dt>
                  <dd className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-ink-secondary">
                      {dbStatus.migration_status.current_revision || 'none'}
                    </span>
                    <StatusBadge
                      variant={
                        dbStatus.migration_status.is_up_to_date
                          ? 'success'
                          : 'warning'
                      }
                    >
                      {dbStatus.migration_status.is_up_to_date
                        ? 'Up to date'
                        : 'Pending'}
                    </StatusBadge>
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-xs text-ink-muted">Loading database status...</p>
            )}
          </div>

          <div className="rounded-2xl border border-border bg-surface-elevated p-6 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
              <HardDrive className="h-4 w-4 text-accent" />
              <span>Upload Limits</span>
            </div>

            <div className="max-w-xs">
              <label className="mb-1.5 block text-xs font-medium text-ink-secondary">
                Maximum Upload Size (MB, 1–500)
              </label>
              <input
                type="number"
                min={1}
                max={500}
                value={maxUploadMb}
                onChange={(e) => setMaxUploadMb(Number(e.target.value))}
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:outline-none"
              />
            </div>

            <div className="flex justify-end border-t border-border/70 pt-4">
              <button
                type="button"
                disabled={saving}
                onClick={() =>
                  void saveEntries(
                    [['max_upload_size_mb', maxUploadMb]],
                    'Storage limit saved.'
                  )
                }
                className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-60"
              >
                <Save className="h-3.5 w-3.5" />
                <span>Save Storage Setting</span>
              </button>
            </div>
          </div>
        </section>
      )}

      {/* 5. Data Backup */}
      {activeSection === 'backup' && (
        <section className="rounded-2xl border border-border bg-surface-elevated p-6 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
                <Archive className="h-4 w-4 text-accent" />
                <span>Local SQLite Backups</span>
              </h3>
              <p className="mt-0.5 text-xs text-ink-secondary">
                Created safely with SQLite&apos;s online backup API and stored under{' '}
                <code className="rounded bg-surface px-1 py-0.5">storage/backups/</code>.
              </p>
            </div>

            <button
              type="button"
              disabled={backupBusy}
              onClick={() => void handleCreateBackup()}
              className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-60"
            >
              <Archive className="h-3.5 w-3.5" />
              <span>{backupBusy ? 'Working...' : 'Create Backup'}</span>
            </button>
          </div>

          {backups.length === 0 ? (
            <p className="rounded-xl border border-dashed border-border bg-canvas/50 p-5 text-center text-xs text-ink-muted">
              No local backups created yet. Click &ldquo;Create Backup&rdquo; to take a
              safe snapshot of your database.
            </p>
          ) : (
            <div className="space-y-2.5">
              {backups.map((b) => {
                const val = validationMap[b.filename];
                const isConfirming = confirmRestoreFile === b.filename;
                return (
                  <div
                    key={b.filename}
                    className="rounded-xl border border-border bg-canvas/60 p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="font-mono text-xs font-semibold text-ink-primary">
                          {b.filename}
                        </div>
                        <div className="mt-0.5 text-[11px] text-ink-muted">
                          {formatBytes(b.size_bytes)} ·{' '}
                          {new Date(b.created_at).toLocaleString()}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          disabled={backupBusy}
                          onClick={() => void handleValidateBackup(b.filename)}
                          className="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs font-medium text-ink-primary hover:bg-surface-hover"
                        >
                          Validate
                        </button>
                        <button
                          type="button"
                          disabled={backupBusy}
                          onClick={() =>
                            setConfirmRestoreFile(isConfirming ? null : b.filename)
                          }
                          className="inline-flex items-center gap-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-2.5 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-500/20 dark:text-amber-300"
                        >
                          <RotateCcw className="h-3 w-3" />
                          <span>Restore</span>
                        </button>
                      </div>
                    </div>

                    {val && (
                      <div className="mt-2.5 flex items-center gap-2 text-xs">
                        <StatusBadge variant={val.is_valid ? 'success' : 'error'}>
                          {val.is_valid ? 'Valid SQLite' : 'Invalid'}
                        </StatusBadge>
                        <span className="text-ink-secondary">{val.detail}</span>
                      </div>
                    )}

                    {isConfirming && (
                      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-900 dark:text-amber-200">
                        <span>
                          Overwrite active database with{' '}
                          <strong>{b.filename}</strong>? A pre-restore safety
                          backup will be created automatically.
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setConfirmRestoreFile(null)}
                            className="rounded-lg border border-border bg-surface px-3 py-1 text-xs text-ink-primary"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            disabled={backupBusy}
                            onClick={() => void handleConfirmRestore(b.filename)}
                            className="rounded-lg bg-amber-600 px-3 py-1 text-xs font-medium text-white hover:bg-amber-700"
                          >
                            Confirm Restore
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Clear Local Data (with automatic pre-clear safety backup) */}
          <div className="border-t border-border/70 pt-5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-700 dark:text-rose-400">
              Clear Local Data
            </h4>
            <p className="mt-1 text-xs text-ink-secondary">
              Safely clear local conversations, usage logs, or workspace content.
              An automatic <code className="rounded bg-surface px-1 py-0.5">pre_clear_*.db</code>{' '}
              backup is created first so nothing is ever lost accidentally. Your
              encrypted API providers and master key remain intact.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(
                [
                  { id: 'conversations', label: 'Clear Conversations' },
                  { id: 'usage_logs', label: 'Clear Usage Logs' },
                  { id: 'all_workspace_data', label: 'Clear All Workspace Data' },
                ] as const
              ).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  disabled={backupBusy}
                  onClick={() => setConfirmClearScope(item.id)}
                  className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-500/20 dark:text-rose-300"
                >
                  {item.label}
                </button>
              ))}
            </div>

            {confirmClearScope && (
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-800 dark:text-rose-200">
                <span>
                  Confirm clearing <strong>{confirmClearScope}</strong>? A
                  safety snapshot will be saved automatically before clearing.
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setConfirmClearScope(null)}
                    className="rounded-lg border border-border bg-surface px-3 py-1 text-ink-primary"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={backupBusy}
                    onClick={async () => {
                      setBackupBusy(true);
                      try {
                        const res = await clearLocalData(confirmClearScope, true);
                        setConfirmClearScope(null);
                        setFeedback({ type: 'success', text: res.message });
                        await loadDiagnostics();
                      } catch (err) {
                        setFeedback({
                          type: 'error',
                          text:
                            err instanceof Error
                              ? err.message
                              : 'Clear operation failed.',
                        });
                      } finally {
                        setBackupBusy(false);
                      }
                    }}
                    className="rounded-lg bg-rose-600 px-3 py-1 font-medium text-white hover:bg-rose-700"
                  >
                    Confirm Clear
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* 6. Security */}
      {activeSection === 'security' && (
        <section className="rounded-2xl border border-border bg-surface-elevated p-6 space-y-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
            <Shield className="h-4 w-4 text-accent" />
            <span>Local Security &amp; Encryption Foundation</span>
          </div>

          {secStatus ? (
            <>
              <dl className="divide-y divide-border/70 rounded-xl border border-border bg-canvas/50 text-xs">
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Encryption Algorithm</dt>
                  <dd className="font-medium text-ink-primary">
                    {secStatus.encryption_algorithm}
                  </dd>
                </div>
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Master Key Status</dt>
                  <dd>
                    <StatusBadge
                      variant={
                        secStatus.master_key_initialized ? 'success' : 'warning'
                      }
                    >
                      {secStatus.master_key_initialized
                        ? `Initialized (${secStatus.key_source})`
                        : 'Generated on first encrypted key'}
                    </StatusBadge>
                  </dd>
                </div>
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Key Storage Location</dt>
                  <dd className="font-mono text-[11px] text-ink-secondary">
                    {secStatus.key_storage_location} (outside SQLite)
                  </dd>
                </div>
                <div className="flex justify-between px-4 py-2.5">
                  <dt className="text-ink-muted">Credential Storage</dt>
                  <dd className="text-ink-primary">
                    {secStatus.credential_management_status}
                  </dd>
                </div>
              </dl>

              <div className="rounded-xl border border-border bg-surface/60 p-4 text-xs leading-relaxed text-ink-secondary">
                <strong className="text-ink-primary">Key Backup Notice: </strong>
                {secStatus.backup_guidance}
              </div>
            </>
          ) : (
            <p className="text-xs text-ink-muted">Loading security status...</p>
          )}
        </section>
      )}
    </div>
  );
}
