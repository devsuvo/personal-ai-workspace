import {
  Check,
  Copy,
  Layers,
  Loader2,
  Play,
  Sparkles,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { MarkdownContent } from '../components/chat/MarkdownContent';
import { SaveAsArtifactModal } from '../components/chat/SaveAsArtifactModal';
import type { ThemeMode } from '../hooks/useTheme';
import {
  fetchAITools,
  runAITool,
  type AIToolDefinition,
  type AIToolRunResult,
} from '../services/productivityService';
import {
  fetchConfiguredProviders,
  fetchProviderDetail,
} from '../services/providerService';
import type { PageId } from '../types/navigation';
import type {
  ConfiguredProviderDetail,
  ConfiguredProviderSummary,
} from '../types/provider';

interface AIToolsPageProps {
  theme: ThemeMode;
  onNavigate: (page: PageId) => void;
}

export function AIToolsPage({ theme, onNavigate }: AIToolsPageProps) {
  const [tools, setTools] = useState<AIToolDefinition[]>([]);
  const [selectedToolId, setSelectedToolId] = useState<string>('summarizer');
  const [inputText, setInputText] = useState('');
  const [toolOptions, setToolOptions] = useState<Record<string, string>>({});

  const [providers, setProviders] = useState<ConfiguredProviderSummary[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState('');
  const [providerDetail, setProviderDetail] =
    useState<ConfiguredProviderDetail | null>(null);
  const [selectedModelId, setSelectedModelId] = useState('');

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AIToolRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showSaveArtifact, setShowSaveArtifact] = useState(false);

  useEffect(() => {
    void fetchAITools()
      .then((list) => {
        setTools(list);
        if (list.length > 0) {
          setSelectedToolId(list[0].id);
        }
      })
      .catch(() => {});

    void fetchConfiguredProviders()
      .then((list) => {
        const enabled = list.filter((p) => p.enabled);
        setProviders(enabled);
        if (enabled.length > 0) setSelectedProviderId(enabled[0].id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedProviderId) return;
    void fetchProviderDetail(selectedProviderId)
      .then((detail) => {
        setProviderDetail(detail);
        const available = detail.models.filter((m) => m.is_available);
        setSelectedModelId(
          detail.default_model || available[0]?.model_id || ''
        );
      })
      .catch(() => {});
  }, [selectedProviderId]);

  const currentTool = tools.find((t) => t.id === selectedToolId) ?? tools[0];

  useEffect(() => {
    if (!currentTool) return;
    const defaults: Record<string, string> = {};
    for (const opt of currentTool.options) {
      if (opt.default) defaults[opt.key] = opt.default;
    }
    setToolOptions(defaults);
    setResult(null);
    setError(null);
  }, [currentTool]);

  const handleRun = async () => {
    if (!currentTool || !inputText.trim()) return;
    if (!selectedProviderId || !selectedModelId.trim()) {
      setError('Configure an AI provider and select a model first.');
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const res = await runAITool({
        tool_id: currentTool.id,
        input_text: inputText,
        provider_id: selectedProviderId,
        model_id: selectedModelId.trim(),
        options: toolOptions,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Tool execution failed.');
    } finally {
      setRunning(false);
    }
  };

  const handleCopy = async () => {
    if (!result?.output) return;
    await navigator.clipboard.writeText(result.output);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const availableModels = (providerDetail?.models ?? []).filter(
    (m) => m.is_available
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-ink-primary">AI Tools</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            Purpose-built productivity tools powered by your configured local or
            cloud AI providers.
          </p>
        </div>

        {/* Provider & Model Switcher */}
        <div className="flex flex-wrap items-center gap-2">
          {providers.length === 0 ? (
            <button
              type="button"
              onClick={() => onNavigate('providers')}
              className="rounded-xl bg-accent px-3.5 py-2 text-xs font-medium text-white hover:bg-accent-hover"
            >
              Connect AI Provider
            </button>
          ) : (
            <>
              <select
                value={selectedProviderId}
                onChange={(e) => setSelectedProviderId(e.target.value)}
                className="rounded-xl border border-border bg-surface-elevated px-3 py-2 text-xs font-medium text-ink-primary focus:outline-none"
              >
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.display_name}
                  </option>
                ))}
              </select>

              {availableModels.length > 0 ? (
                <select
                  value={selectedModelId}
                  onChange={(e) => setSelectedModelId(e.target.value)}
                  className="rounded-xl border border-border bg-surface-elevated px-3 py-2 font-mono text-xs text-ink-primary focus:outline-none"
                >
                  {availableModels.map((m) => (
                    <option key={m.id} value={m.model_id}>
                      {m.display_name}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={selectedModelId}
                  onChange={(e) => setSelectedModelId(e.target.value)}
                  placeholder="Model ID"
                  className="w-40 rounded-xl border border-border bg-surface-elevated px-3 py-2 font-mono text-xs text-ink-primary focus:outline-none"
                />
              )}
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Tool selector rail */}
        <div className="space-y-1.5 lg:col-span-4">
          {tools.map((tool) => {
            const active = tool.id === selectedToolId;
            return (
              <button
                key={tool.id}
                type="button"
                onClick={() => setSelectedToolId(tool.id)}
                className={`w-full rounded-xl border p-3.5 text-left transition-colors ${
                  active
                    ? 'border-accent bg-surface-elevated shadow-sm'
                    : 'border-border bg-surface-elevated/60 hover:border-border-strong'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-ink-primary">
                    {tool.name}
                  </span>
                  <span className="text-[10px] uppercase tracking-wider text-ink-muted">
                    {tool.category}
                  </span>
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-ink-secondary">
                  {tool.description}
                </p>
              </button>
            );
          })}
        </div>

        {/* Active tool runner */}
        <div className="space-y-5 lg:col-span-8">
          {currentTool && (
            <div className="rounded-2xl border border-border bg-surface-elevated p-5 space-y-4">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-accent" />
                <h3 className="text-sm font-semibold text-ink-primary">
                  {currentTool.name}
                </h3>
              </div>

              {/* Tool-specific options */}
              {currentTool.options.length > 0 && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {currentTool.options.map((opt) => (
                    <div
                      key={opt.key}
                      className={opt.type === 'text' ? 'sm:col-span-2' : ''}
                    >
                      <label className="mb-1 block text-xs font-medium text-ink-secondary">
                        {opt.label}
                      </label>
                      {opt.choices ? (
                        <select
                          value={toolOptions[opt.key] ?? opt.default ?? ''}
                          onChange={(e) =>
                            setToolOptions((prev) => ({
                              ...prev,
                              [opt.key]: e.target.value,
                            }))
                          }
                          className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
                        >
                          {opt.choices.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="text"
                          value={toolOptions[opt.key] ?? opt.default ?? ''}
                          onChange={(e) =>
                            setToolOptions((prev) => ({
                              ...prev,
                              [opt.key]: e.target.value,
                            }))
                          }
                          className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  {currentTool.input_label}
                </label>
                <textarea
                  rows={7}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder={currentTool.input_placeholder}
                  className="w-full rounded-xl border border-border bg-canvas p-3 text-sm leading-relaxed text-ink-primary focus:border-border-strong focus:outline-none"
                />
              </div>

              {error && (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300">
                  {error}
                </div>
              )}

              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={running || !inputText.trim()}
                  onClick={() => void handleRun()}
                  className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-50"
                >
                  {running ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Play className="h-3.5 w-3.5" />
                  )}
                  <span>{running ? 'Running...' : `Run ${currentTool.name}`}</span>
                </button>
              </div>
            </div>
          )}

          {/* Output Panel */}
          {result && (
            <div className="rounded-2xl border border-border bg-surface-elevated p-5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-3">
                <div className="text-xs text-ink-secondary">
                  Output from <strong>{result.provider_name}</strong> ·{' '}
                  <code className="rounded bg-surface px-1 py-0.5 font-mono text-[11px]">
                    {result.model_id}
                  </code>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => void handleCopy()}
                    className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1 text-xs text-ink-secondary hover:text-ink-primary"
                  >
                    {copied ? (
                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowSaveArtifact(true)}
                    className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1 text-xs text-ink-secondary hover:text-ink-primary"
                  >
                    <Layers className="h-3.5 w-3.5" />
                    <span>Save as Artifact</span>
                  </button>
                </div>
              </div>

              <MarkdownContent content={result.output} theme={theme} />
            </div>
          )}
        </div>
      </div>

      {showSaveArtifact && result && (
        <SaveAsArtifactModal
          initialContent={result.output}
          onClose={() => setShowSaveArtifact(false)}
          onSaved={() => {
            setShowSaveArtifact(false);
            onNavigate('artifacts');
          }}
        />
      )}
    </div>
  );
}
