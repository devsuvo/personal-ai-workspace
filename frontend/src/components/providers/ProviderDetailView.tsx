import {
  ArrowLeft,
  CheckCircle2,
  Cpu,
  KeyRound,
  Plus,
  RefreshCw,
  Star,
  Trash2,
  XCircle,
  Zap,
} from 'lucide-react';
import { useState } from 'react';
import {
  addCredential,
  addProviderModel,
  deleteCredential,
  deleteProvider,
  deleteProviderModel,
  fetchProviderDetail,
  fetchProviderModels,
  setDefaultModel,
  testProviderConnection,
  updateCredential,
  updateProvider,
  updateProviderModel,
} from '../../services/providerService';
import type {
  ConfiguredProviderDetail,
  ProviderTestResult,
} from '../../types/provider';
import { StatusBadge } from '../common/StatusBadge';

interface ProviderDetailViewProps {
  provider: ConfiguredProviderDetail;
  onBack: () => void;
  onUpdated: (provider: ConfiguredProviderDetail) => void;
  onDeleted: () => void;
}

export function ProviderDetailView({
  provider,
  onBack,
  onUpdated,
  onDeleted,
}: ProviderDetailViewProps) {
  const [displayName, setDisplayName] = useState(provider.display_name);
  const [baseUrl, setBaseUrl] = useState(provider.base_url ?? '');
  const [enabled, setEnabled] = useState(provider.enabled);
  const [savingConfig, setSavingConfig] = useState(false);

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<ProviderTestResult | null>(null);

  const [newCredName, setNewCredName] = useState('');
  const [newCredKey, setNewCredKey] = useState('');
  const [addingCred, setAddingCred] = useState(false);

  const [rotatingCredId, setRotatingCredId] = useState<string | null>(null);
  const [rotatedKey, setRotatedKey] = useState('');

  const [refreshingModels, setRefreshingModels] = useState(false);
  const [modelWarning, setModelWarning] = useState<string | null>(null);
  const [manualModelId, setManualModelId] = useState('');
  const [manualModelName, setManualModelName] = useState('');

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const reloadDetail = async () => {
    const fresh = await fetchProviderDetail(provider.id);
    onUpdated(fresh);
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingConfig(true);
    setFeedback(null);
    try {
      const updated = await updateProvider(provider.id, {
        display_name: displayName.trim(),
        base_url: baseUrl.trim() || null,
        enabled,
      });
      onUpdated(updated);
      setFeedback({ type: 'success', text: 'Provider configuration saved.' });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to update provider.',
      });
    } finally {
      setSavingConfig(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setFeedback(null);
    try {
      const res = await testProviderConnection(provider.id);
      setTestResult(res);
      await reloadDetail();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Connection test failed.',
      });
    } finally {
      setTesting(false);
    }
  };

  const handleAddCredential = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCredKey.trim()) return;
    setAddingCred(true);
    setFeedback(null);
    try {
      await addCredential(provider.id, {
        credential_name: newCredName.trim() || 'API Key',
        api_key: newCredKey.trim(),
        is_active: true,
      });
      setNewCredName('');
      setNewCredKey('');
      await reloadDetail();
      setFeedback({
        type: 'success',
        text: 'Encrypted API credential added and activated.',
      });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to add credential.',
      });
    } finally {
      setAddingCred(false);
    }
  };

  const handleRotateCredential = async (credId: string) => {
    if (!rotatedKey.trim()) return;
    setFeedback(null);
    try {
      await updateCredential(provider.id, credId, {
        api_key: rotatedKey.trim(),
      });
      setRotatingCredId(null);
      setRotatedKey('');
      await reloadDetail();
      setFeedback({ type: 'success', text: 'API credential rotated safely.' });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to rotate key.',
      });
    }
  };

  const handleActivateCredential = async (credId: string) => {
    setFeedback(null);
    try {
      await updateCredential(provider.id, credId, { is_active: true });
      await reloadDetail();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to activate key.',
      });
    }
  };

  const handleDeleteCredential = async (credId: string) => {
    setFeedback(null);
    try {
      await deleteCredential(provider.id, credId);
      await reloadDetail();
      setFeedback({ type: 'success', text: 'Credential removed.' });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to remove credential.',
      });
    }
  };

  const handleDiscoverModels = async () => {
    setRefreshingModels(true);
    setModelWarning(null);
    try {
      const res = await fetchProviderModels(provider.id, true);
      if (res.discovery_warning) {
        setModelWarning(res.discovery_warning);
      }
      await reloadDetail();
    } catch (err) {
      setModelWarning(
        err instanceof Error ? err.message : 'Failed to fetch models.'
      );
    } finally {
      setRefreshingModels(false);
    }
  };

  const handleAddManualModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualModelId.trim()) return;
    setFeedback(null);
    try {
      await addProviderModel(provider.id, {
        model_id: manualModelId.trim(),
        display_name: manualModelName.trim() || manualModelId.trim(),
      });
      setManualModelId('');
      setManualModelName('');
      await reloadDetail();
      setFeedback({ type: 'success', text: 'Model added.' });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to add model.',
      });
    }
  };

  const handleToggleModel = async (modelRecordId: string, current: boolean) => {
    try {
      await updateProviderModel(provider.id, modelRecordId, {
        is_available: !current,
      });
      await reloadDetail();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to update model.',
      });
    }
  };

  const handleSetDefaultModel = async (modelId: string) => {
    try {
      const updated = await setDefaultModel(provider.id, modelId);
      onUpdated(updated);
      setFeedback({
        type: 'success',
        text: `Default model set to ${modelId}.`,
      });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to set default model.',
      });
    }
  };

  const handleDeleteModel = async (modelRecordId: string) => {
    try {
      await deleteProviderModel(provider.id, modelRecordId);
      await reloadDetail();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to remove model.',
      });
    }
  };

  const handleDeleteProvider = async () => {
    try {
      await deleteProvider(provider.id);
      onDeleted();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to delete provider.',
      });
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-surface-elevated text-ink-secondary hover:border-border-strong hover:text-ink-primary"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-ink-primary">
                {provider.display_name}
              </h2>
              <StatusBadge
                variant={
                  provider.connection_status === 'connected'
                    ? 'success'
                    : provider.connection_status === 'error'
                      ? 'error'
                      : 'neutral'
                }
              >
                {provider.connection_status}
              </StatusBadge>
            </div>
            <p className="text-xs text-ink-secondary">
              Provider type: <code className="rounded bg-surface px-1 py-0.5">{provider.provider_key}</code>
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => void handleTest()}
          disabled={testing}
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-60"
        >
          <Zap className="h-3.5 w-3.5" />
          <span>{testing ? 'Testing...' : 'Test Connection'}</span>
        </button>
      </div>

      {feedback && (
        <div
          className={`rounded-xl border px-4 py-3 text-xs ${
            feedback.type === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300'
          }`}
        >
          {feedback.text}
        </div>
      )}

      {/* Connection Test Result */}
      {(testResult || provider.last_error) && (
        <div
          className={`flex items-start gap-3 rounded-2xl border p-4 text-xs ${
            testResult?.success
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-800 dark:text-rose-300'
          }`}
        >
          {testResult?.success ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <div>
            <div className="font-semibold">
              {testResult
                ? testResult.message
                : `Last connection error: ${provider.last_error}`}
            </div>
            {testResult?.latency_ms != null && (
              <div className="mt-0.5 opacity-80">
                Latency: {testResult.latency_ms} ms
              </div>
            )}
          </div>
        </div>
      )}

      {/* Configuration */}
      <form
        onSubmit={handleSaveConfig}
        className="rounded-2xl border border-border bg-surface-elevated p-5 space-y-4"
      >
        <h3 className="text-sm font-semibold text-ink-primary">
          Provider Configuration
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-secondary">
              Display Name
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:border-border-strong focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-ink-secondary">
              Base URL
            </label>
            <input
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://..."
              className="w-full rounded-xl border border-border bg-canvas px-3 py-2 font-mono text-xs text-ink-primary focus:border-border-strong focus:outline-none"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <label className="inline-flex items-center gap-2 text-xs font-medium text-ink-primary">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-border accent-accent"
            />
            <span>Provider Enabled</span>
          </label>

          <button
            type="submit"
            disabled={savingConfig}
            className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-medium text-ink-primary hover:border-border-strong hover:bg-surface-hover disabled:opacity-60"
          >
            {savingConfig ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </form>

      {/* Saved Credentials */}
      <section className="rounded-2xl border border-border bg-surface-elevated p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
              <KeyRound className="h-4 w-4 text-accent" />
              <span>Encrypted Credentials ({provider.credentials.length})</span>
            </h3>
            <p className="mt-0.5 text-xs text-ink-secondary">
              Keys are encrypted with Fernet at rest. Only masked fingerprints are
              displayed.
            </p>
          </div>
        </div>

        {provider.credentials.length === 0 ? (
          <p className="rounded-xl border border-dashed border-border bg-canvas/50 p-4 text-xs text-ink-muted">
            {provider.requires_api_key
              ? 'No API key saved yet. Add an API key below to test and use this provider.'
              : 'No API key saved (optional for local Ollama / unauthenticated endpoints).'}
          </p>
        ) : (
          <div className="space-y-2">
            {provider.credentials.map((cred) => (
              <div
                key={cred.id}
                className="rounded-xl border border-border bg-canvas/60 p-3.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-ink-primary">
                        {cred.credential_name}
                      </span>
                      {cred.is_active && (
                        <StatusBadge variant="success">Active</StatusBadge>
                      )}
                    </div>
                    <div className="mt-1 font-mono text-xs text-ink-secondary">
                      {cred.masked_api_key}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {!cred.is_active && (
                      <button
                        type="button"
                        onClick={() => void handleActivateCredential(cred.id)}
                        className="rounded-lg border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink-primary hover:bg-surface-hover"
                      >
                        Set Active
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setRotatingCredId(
                          rotatingCredId === cred.id ? null : cred.id
                        );
                        setRotatedKey('');
                      }}
                      className="rounded-lg border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink-secondary hover:text-ink-primary"
                    >
                      Rotate Key
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteCredential(cred.id)}
                      aria-label="Delete credential"
                      className="rounded-lg border border-border bg-surface p-1.5 text-rose-600 hover:bg-rose-500/10"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>

                {rotatingCredId === cred.id && (
                  <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border/70 pt-3">
                    <input
                      type="password"
                      autoComplete="new-password"
                      value={rotatedKey}
                      onChange={(e) => setRotatedKey(e.target.value)}
                      placeholder="Enter new replacement API key"
                      className="min-w-[220px] flex-1 rounded-lg border border-border bg-surface-elevated px-3 py-1.5 font-mono text-xs text-ink-primary focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => void handleRotateCredential(cred.id)}
                      className="rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-hover"
                    >
                      Save New Key
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <form
          onSubmit={handleAddCredential}
          className="grid grid-cols-1 gap-2 border-t border-border/70 pt-4 sm:grid-cols-3"
        >
          <input
            type="text"
            value={newCredName}
            onChange={(e) => setNewCredName(e.target.value)}
            placeholder="Credential label (e.g. Work Key)"
            className="rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
          />
          <input
            type="password"
            autoComplete="new-password"
            value={newCredKey}
            onChange={(e) => setNewCredKey(e.target.value)}
            placeholder="Paste new API key"
            className="rounded-xl border border-border bg-canvas px-3 py-2 font-mono text-xs text-ink-primary focus:outline-none"
          />
          <button
            type="submit"
            disabled={addingCred || !newCredKey.trim()}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-xs font-medium text-ink-primary hover:border-border-strong hover:bg-surface-hover disabled:opacity-50"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>{addingCred ? 'Encrypting...' : 'Add Credential'}</span>
          </button>
        </form>
      </section>

      {/* Model Management */}
      <section className="rounded-2xl border border-border bg-surface-elevated p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
              <Cpu className="h-4 w-4 text-accent" />
              <span>Models ({provider.models.length})</span>
            </h3>
            <p className="mt-0.5 text-xs text-ink-secondary">
              Fetch models from the provider or register custom model IDs manually.
            </p>
          </div>

          {provider.supports_model_listing && (
            <button
              type="button"
              onClick={() => void handleDiscoverModels()}
              disabled={refreshingModels}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs font-medium text-ink-primary hover:border-border-strong hover:bg-surface-hover disabled:opacity-60"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${refreshingModels ? 'animate-spin' : ''}`}
              />
              <span>Fetch Available Models</span>
            </button>
          )}
        </div>

        {modelWarning && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3.5 py-2.5 text-xs text-amber-800 dark:text-amber-300">
            {modelWarning}
          </div>
        )}

        {provider.models.length === 0 ? (
          <p className="rounded-xl border border-dashed border-border bg-canvas/50 p-4 text-xs text-ink-muted">
            No models registered yet. Click &ldquo;Fetch Available Models&rdquo; or add a
            model identifier manually below.
          </p>
        ) : (
          <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
            {provider.models.map((m) => {
              const isDefault = provider.default_model === m.model_id;
              return (
                <div
                  key={m.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-canvas/60 px-3.5 py-2.5"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-mono text-xs font-semibold text-ink-primary">
                        {m.model_id}
                      </span>
                      {isDefault && (
                        <StatusBadge variant="accent">Default</StatusBadge>
                      )}
                      {m.is_manual && (
                        <StatusBadge variant="neutral">Manual</StatusBadge>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {!isDefault && (
                      <button
                        type="button"
                        onClick={() => void handleSetDefaultModel(m.model_id)}
                        className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1 text-xs font-medium text-ink-secondary hover:text-ink-primary"
                      >
                        <Star className="h-3 w-3" />
                        <span>Set Default</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => void handleToggleModel(m.id, m.is_available)}
                      className={`rounded-lg border px-2.5 py-1 text-xs font-medium ${
                        m.is_available
                          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                          : 'border-border bg-surface text-ink-muted'
                      }`}
                    >
                      {m.is_available ? 'Enabled' : 'Disabled'}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDeleteModel(m.id)}
                      aria-label="Remove model"
                      className="rounded-lg border border-border bg-surface p-1.5 text-rose-600 hover:bg-rose-500/10"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <form
          onSubmit={handleAddManualModel}
          className="grid grid-cols-1 gap-2 border-t border-border/70 pt-4 sm:grid-cols-3"
        >
          <input
            type="text"
            value={manualModelId}
            onChange={(e) => setManualModelId(e.target.value)}
            placeholder="Model ID (e.g. gpt-4o-mini)"
            className="rounded-xl border border-border bg-canvas px-3 py-2 font-mono text-xs text-ink-primary focus:outline-none"
          />
          <input
            type="text"
            value={manualModelName}
            onChange={(e) => setManualModelName(e.target.value)}
            placeholder="Display name (optional)"
            className="rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
          />
          <button
            type="submit"
            disabled={!manualModelId.trim()}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-xs font-medium text-ink-primary hover:border-border-strong hover:bg-surface-hover disabled:opacity-50"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Model Manually</span>
          </button>
        </form>
      </section>

      {/* Danger Zone */}
      <section className="rounded-2xl border border-rose-500/25 bg-surface-elevated p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-rose-700 dark:text-rose-400">
              Remove Provider
            </h3>
            <p className="mt-0.5 text-xs text-ink-secondary">
              Permanently removes this provider, all encrypted credentials, and
              registered models from your local SQLite database.
            </p>
          </div>
          {!confirmDelete ? (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-xs font-medium text-rose-700 hover:bg-rose-500/20 dark:text-rose-300"
            >
              Delete Provider
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="rounded-xl border border-border bg-surface px-3 py-2 text-xs font-medium text-ink-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleDeleteProvider()}
                className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-medium text-white hover:bg-rose-700"
              >
                Confirm Delete
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
