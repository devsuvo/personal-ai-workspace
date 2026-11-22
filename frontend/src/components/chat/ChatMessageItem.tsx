import {
  AlertCircle,
  Check,
  Copy,
  Layers,
  Pencil,
  RefreshCw,
  RotateCcw,
} from 'lucide-react';
import { useState } from 'react';
import { BrandMark } from '../../assets/BrandMark';
import type { ThemeMode } from '../../hooks/useTheme';
import type { ChatMessage } from '../../types/chat';
import { MarkdownContent } from './MarkdownContent';

interface ChatMessageItemProps {
  message: ChatMessage;
  theme: ThemeMode;
  showTokenUsage: boolean;
  isStreaming: boolean;
  onRegenerate: (messageId: string) => void;
  onEditAndResend: (messageId: string, newContent: string) => void;
  onSaveAsArtifact?: (content: string) => void;
}

export function ChatMessageItem({
  message,
  theme,
  showTokenUsage,
  isStreaming,
  onRegenerate,
  onEditAndResend,
  onSaveAsArtifact,
}: ChatMessageItemProps) {
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);

  const isUser = message.role === 'user';
  const isError = message.status === 'error';
  const isStopped = message.status === 'stopped';
  const isGenerating = message.status === 'streaming';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const handleSaveEdit = () => {
    const trimmed = editText.trim();
    if (!trimmed) return;
    setEditing(false);
    onEditAndResend(message.id, trimmed);
  };

  if (isUser) {
    return (
      <div className="group flex justify-end">
        <div className="max-w-[85%] space-y-1.5 sm:max-w-[75%]">
          {editing ? (
            <div className="rounded-2xl border border-border-strong bg-surface-elevated p-3">
              <textarea
                rows={3}
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                className="w-full resize-none bg-transparent text-sm text-ink-primary focus:outline-none"
              />
              <div className="mt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setEditing(false);
                    setEditText(message.content);
                  }}
                  className="rounded-lg border border-border bg-surface px-2.5 py-1 text-xs text-ink-secondary"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveEdit}
                  disabled={!editText.trim()}
                  className="rounded-lg bg-accent px-3 py-1 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-50"
                >
                  Save &amp; Resend
                </button>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-border bg-surface px-4 py-3 text-[15px] leading-relaxed text-ink-primary whitespace-pre-wrap">
              {message.content}
            </div>
          )}

          {!editing && !isStreaming && (
            <div className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
              <button
                type="button"
                onClick={() => {
                  setEditText(message.content);
                  setEditing(true);
                }}
                title="Edit and resend"
                className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-ink-muted hover:bg-surface hover:text-ink-primary"
              >
                <Pencil className="h-3 w-3" />
                <span>Edit</span>
              </button>
              <button
                type="button"
                onClick={() => void handleCopy()}
                title="Copy message"
                className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-ink-muted hover:bg-surface hover:text-ink-primary"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="group flex items-start gap-3">
      <div className="mt-0.5 shrink-0">
        <BrandMark className="h-7 w-7" />
      </div>

      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
          <span className="font-semibold text-ink-secondary">
            {message.provider_name || 'AI Assistant'}
          </span>
          {(message.model_id || message.model_name) && (
            <code className="rounded bg-surface px-1.5 py-0.5 font-mono text-[10px]">
              {message.model_id || message.model_name}
            </code>
          )}
          {isGenerating && (
            <span className="inline-flex items-center gap-1 text-accent">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
              Generating...
            </span>
          )}
          {isStopped && (
            <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] text-amber-700 dark:text-amber-300">
              Stopped
            </span>
          )}
        </div>

        {message.content ? (
          <MarkdownContent content={message.content} theme={theme} />
        ) : isGenerating ? (
          <div className="flex items-center gap-1.5 py-1 text-xs text-ink-muted">
            <span className="h-2 w-2 animate-bounce rounded-full bg-ink-muted/60" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-ink-muted/60 [animation-delay:120ms]" />
            <span className="h-2 w-2 animate-bounce rounded-full bg-ink-muted/60 [animation-delay:240ms]" />
          </div>
        ) : null}

        {isError && (
          <div className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="flex-1">
              {message.error_message || 'Response generation failed.'}
            </div>
            {!isStreaming && (
              <button
                type="button"
                onClick={() => onRegenerate(message.id)}
                className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-rose-500/40 bg-rose-500/10 px-2.5 py-1 text-xs font-medium hover:bg-rose-500/20"
              >
                <RotateCcw className="h-3 w-3" />
                <span>Retry</span>
              </button>
            )}
          </div>
        )}

        {/* Footer actions & real token usage */}
        {!isGenerating && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex items-center gap-1">
              {message.content && (
                <button
                  type="button"
                  onClick={() => void handleCopy()}
                  className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-ink-muted transition-colors hover:bg-surface hover:text-ink-primary"
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-emerald-500" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
              )}

              {message.content && onSaveAsArtifact && (
                <button
                  type="button"
                  onClick={() => onSaveAsArtifact(message.content)}
                  className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-ink-muted transition-colors hover:bg-surface hover:text-ink-primary"
                >
                  <Layers className="h-3 w-3" />
                  <span>Save as Artifact</span>
                </button>
              )}

              {!isStreaming && (
                <button
                  type="button"
                  onClick={() => onRegenerate(message.id)}
                  className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] text-ink-muted transition-colors hover:bg-surface hover:text-ink-primary"
                >
                  <RefreshCw className="h-3 w-3" />
                  <span>{isError || isStopped ? 'Retry' : 'Regenerate'}</span>
                </button>
              )}
            </div>

            {showTokenUsage && message.token_usage && (
              <div className="text-[11px] text-ink-muted">
                {message.token_usage.input_tokens != null && (
                  <span>In: {message.token_usage.input_tokens}</span>
                )}
                {message.token_usage.output_tokens != null && (
                  <span className="ml-2">
                    Out: {message.token_usage.output_tokens}
                  </span>
                )}
                {message.token_usage.total_tokens != null && (
                  <span className="ml-2 font-medium text-ink-secondary">
                    Total: {message.token_usage.total_tokens} tokens
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
