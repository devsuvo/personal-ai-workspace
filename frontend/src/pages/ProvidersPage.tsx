import {
  Cpu,
  HardDrive,
  KeyRound,
  Plus,
  RefreshCw,
  Settings2,
  Zap,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { StatusBadge } from '../components/common/StatusBadge';
import { AddProviderModal } from '../components/providers/AddProviderModal';
import { ProviderDetailView } from '../components/providers/ProviderDetailView';
import type { SystemStatusState } from '../hooks/useSystemStatus';
import {
  fetchConfiguredProviders,
  fetchProviderCatalog,
  fetchProviderDetail,
  testProviderConnection,
} from '../services/providerService';
import type {
  ConfiguredProviderDetail,
  ConfiguredProviderSummary,
  ProviderCatalogItem,
} from '../types/provider';

interface ProvidersPageProps {
  systemStatus: SystemStatusState;
}

export function ProvidersPage({ systemStatus }: ProvidersPageProps) {
  const [catalog, setCatalog] = useState<ProviderCatalogItem[]>([]);
  const [providers, setProviders] = useState<ConfiguredProviderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedDetail, setSelectedDetail] =
    useState<ConfiguredProviderDetail | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [inlineNotice, setInlineNotice] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cat, list] = await Promise.all([
        fetchProviderCatalog(),
        fetchConfiguredProviders(),
      ]);
      setCatalog(cat);
      setProviders(list);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load AI providers.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const handleOpenDetail = async (providerId: string) => {
    setInlineNotice(null);
    try {
      const detail = await fetchProviderDetail(providerId);
      setSelectedDetail(detail);
    } catch (err) {
      setInlineNotice({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to load provider.',
      });
    }
  };

  const handleQuickTest = async (providerId: string) => {
    setTestingId(providerId);
    setInlineNotice(null);
    try {
      const result = await testProviderConnection(providerId);
      setInlineNotice({
        type: result.success ? 'success' : 'error',
        text: result.message,
      });
      await loadAll();
      await systemStatus.refresh();
    } catch (err) {
      setInlineNotice({
        type: 'error',
        text: err instanceof Error ? err.message : 'Connection test failed.',
      });
    } finally {
      setTestingId(null);
    }
  };

  if (selectedDetail) {
    return (
      <ProviderDetailView
        provider={selectedDetail}
        onBack={() => {
          setSelectedDetail(null);
          void loadAll();
          void systemStatus.refresh();
        }}
        onUpdated={(updated) => {
          setSelectedDetail(updated);
          void systemStatus.refresh();
        }}
        onDeleted={() => {
          setSelectedDetail(null);
          void loadAll();
          void systemStatus.refresh();
        }}
      />
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-ink-primary">AI Providers</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            Add, test, and manage your local AI providers and encrypted API keys.
            All credentials stay strictly on this machine.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadAll()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface-elevated px-3 py-2 text-xs font-medium text-ink-secondary hover:border-border-strong hover:text-ink-primary disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover"
          >
            <Plus className="h-4 w-4" />
            <span>Add Provider</span>
          </button>
        </div>
      </div>

      {inlineNotice && (
        <div
          className={`mb-5 rounded-xl border px-4 py-3 text-xs ${
            inlineNotice.type === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300'
          }`}
        >
          {inlineNotice.text}
        </div>
      )}

      {error && (
        <div className="mb-5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-700 dark:text-rose-300">
          {error}
        </div>
      )}

      {/* Configured Providers Section */}
      {providers.length === 0 ? (
        <div className="mb-8 rounded-2xl border border-border bg-surface-elevated p-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-surface text-accent">
            <KeyRound className="h-5 w-5" />
          </div>
          <h3 className="text-base font-semibold text-ink-primary">
            No AI providers configured yet
          </h3>
          <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-ink-secondary">
            Add your own API key for Anthropic Claude, Google Gemini, OpenAI,
            DeepSeek, Grok, Mistral, Groq, OpenRouter, a Custom OpenAI-Compatible
            endpoint, or connect local Ollama.
          </p>
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
          >
            <Plus className="h-4 w-4" />
            <span>Add Your First Provider</span>
          </button>
        </div>
      ) : (
        <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2">
          {providers.map((provider) => (
            <div
              key={provider.id}
              className="flex flex-col justify-between rounded-2xl border border-border bg-surface-elevated p-5"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-accent">
                      {provider.is_local ? (
                        <HardDrive className="h-4 w-4" />
                      ) : (
                        <Cpu className="h-4 w-4" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <h3 className="truncate text-sm font-semibold text-ink-primary">
                        {provider.display_name}
                      </h3>
                      <div className="mt-0.5 text-[11px] text-ink-muted">
                        {provider.provider_key}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1">
                    <StatusBadge variant={provider.enabled ? 'success' : 'neutral'}>
                      {provider.enabled ? 'Enabled' : 'Disabled'}
                    </StatusBadge>
                    <StatusBadge
                      variant={
                        provider.connection_status === 'connected'
                          ? 'success'
                          : provider.connection_status === 'error'
                            ? 'error'
                            : 'warning'
                      }
                    >
                      {provider.connection_status}
                    </StatusBadge>
                  </div>
                </div>

                <dl className="mt-4 grid grid-cols-2 gap-2 rounded-xl border border-border/70 bg-canvas/50 p-3 text-xs">
                  <div>
                    <dt className="text-[11px] text-ink-muted">Default Model</dt>
                    <dd className="mt-0.5 truncate font-mono text-[11px] font-medium text-ink-primary">
                      {provider.default_model || 'Not set'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] text-ink-muted">Credentials</dt>
                    <dd className="mt-0.5 text-[11px] font-medium text-ink-primary">
                      {provider.credentials_count} saved
                    </dd>
                  </div>
                </dl>

                {provider.last_error && (
                  <p className="mt-2 line-clamp-2 text-[11px] text-rose-600 dark:text-rose-400">
                    {provider.last_error}
                  </p>
                )}
              </div>

              <div className="mt-4 flex items-center gap-2 border-t border-border/70 pt-3">
                <button
                  type="button"
                  onClick={() => void handleQuickTest(provider.id)}
                  disabled={testingId === provider.id}
                  className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border bg-surface py-2 text-xs font-medium text-ink-primary hover:border-border-strong hover:bg-surface-hover disabled:opacity-60"
                >
                  <Zap className="h-3.5 w-3.5 text-accent" />
                  <span>
                    {testingId === provider.id ? 'Testing...' : 'Test Connection'}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => void handleOpenDetail(provider.id)}
                  className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-border bg-surface-elevated py-2 text-xs font-medium text-ink-primary hover:border-border-strong hover:bg-surface-hover"
                >
                  <Settings2 className="h-3.5 w-3.5" />
                  <span>Manage</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Supported Providers Catalog */}
      <div>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
          Supported Providers ({catalog.length})
        </h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {catalog.map((item) => (
            <div
              key={item.provider_key}
              className="rounded-xl border border-border bg-surface-elevated/60 p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-ink-primary">
                  {item.name}
                </span>
                <StatusBadge variant="neutral">
                  {item.is_local ? 'Local' : item.requires_api_key ? 'API Key' : 'Flexible'}
                </StatusBadge>
              </div>
              <p className="mt-1.5 text-[11px] leading-relaxed text-ink-secondary">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {showAddModal && catalog.length > 0 && (
        <AddProviderModal
          catalog={catalog}
          onClose={() => setShowAddModal(false)}
          onCreated={(created) => {
            setShowAddModal(false);
            setSelectedDetail(created);
            void systemStatus.refresh();
          }}
        />
      )}
    </div>
  );
}
