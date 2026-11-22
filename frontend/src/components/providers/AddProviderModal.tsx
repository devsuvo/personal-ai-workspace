import { Cpu, HardDrive, KeyRound, X } from 'lucide-react';
import { useState } from 'react';
import { createProvider } from '../../services/providerService';
import type {
  ConfiguredProviderDetail,
  ProviderCatalogItem,
} from '../../types/provider';

interface AddProviderModalProps {
  catalog: ProviderCatalogItem[];
  onClose: () => void;
  onCreated: (provider: ConfiguredProviderDetail) => void;
}

export function AddProviderModal({
  catalog,
  onClose,
  onCreated,
}: AddProviderModalProps) {
  const [selectedKey, setSelectedKey] = useState<string>(
    catalog[0]?.provider_key ?? 'anthropic'
  );
  const selectedItem =
    catalog.find((c) => c.provider_key === selectedKey) ?? catalog[0];

  const [displayName, setDisplayName] = useState<string>(
    selectedItem?.name ?? ''
  );
  const [baseUrl, setBaseUrl] = useState<string>(
    selectedItem?.default_base_url ?? ''
  );
  const [apiKey, setApiKey] = useState<string>('');
  const [credentialName, setCredentialName] = useState<string>('Default Key');
  const [defaultModel, setDefaultModel] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectProvider = (key: string) => {
    setSelectedKey(key);
    const match = catalog.find((c) => c.provider_key === key);
    if (match) {
      setDisplayName(match.name);
      setBaseUrl(match.default_base_url ?? '');
    }
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!displayName.trim()) {
      setError('Display name is required.');
      return;
    }
    if (selectedItem?.requires_api_key && !apiKey.trim()) {
      setError(`${selectedItem.name} requires an API key.`);
      return;
    }
    if (selectedKey === 'custom_openai' && !baseUrl.trim()) {
      setError('Custom OpenAI-Compatible API requires a Base URL.');
      return;
    }

    setSaving(true);
    try {
      const created = await createProvider({
        provider_key: selectedKey,
        display_name: displayName.trim(),
        base_url: baseUrl.trim() || null,
        api_key: apiKey.trim() || null,
        credential_name: credentialName.trim() || 'Default Key',
        default_model: defaultModel.trim() || null,
        enabled: true,
      });
      onCreated(created);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to create provider.'
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-[1px]">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-surface-elevated shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-ink-primary">
              Add AI Provider
            </h2>
            <p className="mt-0.5 text-xs text-ink-secondary">
              API keys are encrypted locally using Fernet before saving to SQLite.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-ink-secondary hover:bg-surface hover:text-ink-primary"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="overflow-y-auto p-6 space-y-5">
          {/* Provider Type Selector */}
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Select Provider
            </label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {catalog.map((item) => {
                const active = item.provider_key === selectedKey;
                return (
                  <button
                    key={item.provider_key}
                    type="button"
                    onClick={() => handleSelectProvider(item.provider_key)}
                    className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-xs font-medium transition-colors ${
                      active
                        ? 'border-accent bg-accent/10 text-ink-primary'
                        : 'border-border bg-surface/60 text-ink-secondary hover:border-border-strong hover:text-ink-primary'
                    }`}
                  >
                    {item.is_local ? (
                      <HardDrive className="h-3.5 w-3.5 shrink-0 text-accent" />
                    ) : (
                      <Cpu className="h-3.5 w-3.5 shrink-0 text-ink-muted" />
                    )}
                    <span className="truncate">{item.name}</span>
                  </button>
                );
              })}
            </div>
            {selectedItem && (
              <p className="mt-2 text-xs text-ink-secondary">
                {selectedItem.description}
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="provider-display-name"
                className="mb-1.5 block text-xs font-medium text-ink-primary"
              >
                Display Name *
              </label>
              <input
                id="provider-display-name"
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. My Anthropic Account"
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:border-border-strong focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="provider-default-model"
                className="mb-1.5 block text-xs font-medium text-ink-primary"
              >
                Default Model (Optional)
              </label>
              <input
                id="provider-default-model"
                type="text"
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
                placeholder="e.g. claude-3-7-sonnet-20250219"
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:border-border-strong focus:outline-none"
              />
            </div>
          </div>

          {selectedItem?.allows_custom_base_url && (
            <div>
              <label
                htmlFor="provider-base-url"
                className="mb-1.5 block text-xs font-medium text-ink-primary"
              >
                Base URL {selectedKey === 'custom_openai' ? '*' : '(Optional override)'}
              </label>
              <input
                id="provider-base-url"
                type="url"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={
                  selectedItem.default_base_url || 'https://api.example.com/v1'
                }
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 font-mono text-xs text-ink-primary focus:border-border-strong focus:outline-none"
              />
            </div>
          )}

          {/* API Key Section */}
          <div className="rounded-xl border border-border bg-surface/50 p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-ink-primary">
              <KeyRound className="h-3.5 w-3.5 text-accent" />
              <span>
                API Credential{' '}
                {selectedItem?.requires_api_key ? '(Required)' : '(Optional)'}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="credential-name"
                  className="mb-1 block text-xs text-ink-secondary"
                >
                  Credential Label
                </label>
                <input
                  id="credential-name"
                  type="text"
                  value={credentialName}
                  onChange={(e) => setCredentialName(e.target.value)}
                  placeholder="Default Key"
                  className="w-full rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:border-border-strong focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="provider-api-key"
                  className="mb-1 block text-xs text-ink-secondary"
                >
                  API Key
                </label>
                <input
                  id="provider-api-key"
                  type="password"
                  autoComplete="new-password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={
                    selectedItem?.is_local
                      ? 'Not required for local Ollama'
                      : 'Paste your API key'
                  }
                  className="w-full rounded-lg border border-border bg-canvas px-3 py-2 font-mono text-xs text-ink-primary focus:border-border-strong focus:outline-none"
                />
              </div>
            </div>

            <p className="text-[11px] text-ink-muted">
              Your API key is encrypted before storage and will never be shown in
              full again after saving.
            </p>
          </div>

          {error && (
            <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2.5 text-xs text-rose-700 dark:text-rose-300">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-medium text-ink-secondary hover:bg-surface-hover hover:text-ink-primary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-60"
            >
              {saving ? 'Saving...' : 'Save Provider'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
