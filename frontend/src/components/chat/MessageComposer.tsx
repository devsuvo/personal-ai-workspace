import {
  ArrowUp,
  Cpu,
  FileText,
  KeyRound,
  Paperclip,
  Plug,
  Square,
  X,
} from 'lucide-react';
import { useEffect, useRef } from 'react';
import type {
  ConfiguredProviderDetail,
  ConfiguredProviderSummary,
} from '../../types/provider';
import type { UploadedFileMetadata } from '../../types/workspace';

interface MessageComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (message: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  sendOnEnter: boolean;
  providers: ConfiguredProviderSummary[];
  selectedProviderId: string;
  onSelectProvider: (providerId: string) => void;
  selectedProviderDetail: ConfiguredProviderDetail | null;
  selectedModelId: string;
  onSelectModel: (modelId: string) => void;
  selectedCredentialId: string;
  onSelectCredential: (credentialId: string) => void;
  attachedFiles: UploadedFileMetadata[];
  onAttachFiles: (files: FileList) => void;
  onRemoveAttachedFile: (fileId: string) => void;
  uploadingFile: boolean;
  onOpenProviders: () => void;
}

export function MessageComposer({
  value,
  onChange,
  onSend,
  onStop,
  isStreaming,
  sendOnEnter,
  providers,
  selectedProviderId,
  onSelectProvider,
  selectedProviderDetail,
  selectedModelId,
  onSelectModel,
  selectedCredentialId,
  onSelectCredential,
  attachedFiles,
  onAttachFiles,
  onRemoveAttachedFile,
  uploadingFile,
  onOpenProviders,
}: MessageComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const enabledProviders = providers.filter((p) => p.enabled);
  const availableModels = (selectedProviderDetail?.models ?? []).filter(
    (m) => m.is_available
  );
  const credentials = selectedProviderDetail?.credentials ?? [];

  const handleSubmit = () => {
    if (isStreaming) return;
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (sendOnEnter && event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full">
      {attachedFiles.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {attachedFiles.map((f) => (
            <span
              key={f.id}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface-elevated px-2.5 py-1 text-xs text-ink-primary"
            >
              <FileText className="h-3 w-3 text-accent" />
              <span className="max-w-[180px] truncate">{f.original_filename}</span>
              <span className="text-[10px] text-ink-muted">
                ({f.extraction_status})
              </span>
              <button
                type="button"
                onClick={() => onRemoveAttachedFile(f.id)}
                aria-label="Remove attached file"
                className="text-ink-muted hover:text-rose-600"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="rounded-2xl border border-border bg-surface-elevated p-3 shadow-composer transition-colors focus-within:border-border-strong dark:shadow-composer-dark">
        <textarea
          ref={textareaRef}
          rows={2}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          placeholder="Message Personal AI Workspace..."
          aria-label="Message input"
          className="w-full resize-none bg-transparent px-1.5 py-1 text-[15px] leading-relaxed text-ink-primary placeholder:text-ink-muted focus:outline-none disabled:opacity-60"
        />

        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-border/70 pt-2.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  onAttachFiles(e.target.files);
                  e.target.value = '';
                }
              }}
            />
            <button
              type="button"
              disabled={uploadingFile || isStreaming}
              onClick={() => fileInputRef.current?.click()}
              title="Attach local files as context"
              className="inline-flex items-center gap-1.5 rounded-lg border border-transparent px-2.5 py-1.5 text-xs font-medium text-ink-secondary transition-colors hover:border-border hover:bg-surface hover:text-ink-primary disabled:opacity-50"
            >
              <Paperclip className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">
                {uploadingFile ? 'Uploading...' : 'Attach'}
              </span>
            </button>

            {enabledProviders.length === 0 ? (
              <button
                type="button"
                onClick={onOpenProviders}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface/70 px-2.5 py-1.5 text-xs font-medium text-ink-secondary transition-colors hover:border-border-strong hover:text-ink-primary"
              >
                <Plug className="h-3.5 w-3.5 text-accent" />
                <span>Configure AI Provider</span>
              </button>
            ) : (
              <>
                {/* Provider selector */}
                <label className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface/70 px-2 py-1 text-xs text-ink-secondary">
                  <Plug className="h-3.5 w-3.5 shrink-0 text-accent" />
                  <select
                    aria-label="Select AI Provider"
                    value={selectedProviderId}
                    onChange={(e) => onSelectProvider(e.target.value)}
                    disabled={isStreaming}
                    className="max-w-[140px] bg-transparent text-xs font-medium text-ink-primary focus:outline-none"
                  >
                    {enabledProviders.map((p) => (
                      <option key={p.id} value={p.id} className="bg-surface-elevated">
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </label>

                {/* Model selector */}
                <label className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface/70 px-2 py-1 text-xs text-ink-secondary">
                  <Cpu className="h-3.5 w-3.5 shrink-0 text-ink-muted" />
                  {availableModels.length > 0 ? (
                    <select
                      aria-label="Select Model"
                      value={selectedModelId}
                      onChange={(e) => onSelectModel(e.target.value)}
                      disabled={isStreaming}
                      className="max-w-[180px] bg-transparent font-mono text-[11px] font-medium text-ink-primary focus:outline-none"
                    >
                      {!availableModels.some((m) => m.model_id === selectedModelId) &&
                        selectedModelId && (
                          <option
                            value={selectedModelId}
                            className="bg-surface-elevated"
                          >
                            {selectedModelId}
                          </option>
                        )}
                      {availableModels.map((m) => (
                        <option
                          key={m.id}
                          value={m.model_id}
                          className="bg-surface-elevated"
                        >
                          {m.display_name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      aria-label="Model ID"
                      value={selectedModelId}
                      onChange={(e) => onSelectModel(e.target.value)}
                      disabled={isStreaming}
                      placeholder="Enter model ID"
                      className="w-36 bg-transparent font-mono text-[11px] text-ink-primary placeholder:text-ink-muted focus:outline-none"
                    />
                  )}
                </label>

                {/* Credential selector (shown when provider has multiple credentials) */}
                {credentials.length > 1 && (
                  <label className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-surface/70 px-2 py-1 text-xs text-ink-secondary">
                    <KeyRound className="h-3 w-3 shrink-0 text-ink-muted" />
                    <select
                      aria-label="Select API Credential"
                      value={selectedCredentialId}
                      onChange={(e) => onSelectCredential(e.target.value)}
                      disabled={isStreaming}
                      className="max-w-[120px] bg-transparent text-[11px] text-ink-primary focus:outline-none"
                    >
                      {credentials.map((c) => (
                        <option
                          key={c.id}
                          value={c.id}
                          className="bg-surface-elevated"
                        >
                          {c.credential_name} ({c.masked_api_key})
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </>
            )}
          </div>

          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Stop generation"
              title="Stop generation"
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-rose-600 px-3 text-xs font-medium text-white transition-colors hover:bg-rose-700"
            >
              <Square className="h-3 w-3 fill-current" />
              <span>Stop</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!value.trim()}
              aria-label="Send message"
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-surface-hover disabled:text-ink-muted"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
