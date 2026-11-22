import {
  AlertCircle,
  ArrowRight,
  Code2,
  FileText,
  Info,
  Lightbulb,
  PenLine,
  ShieldCheck,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { BrandMark } from '../assets/BrandMark';
import { ChatMessageItem } from '../components/chat/ChatMessageItem';
import { MessageComposer } from '../components/chat/MessageComposer';
import { SaveAsArtifactModal } from '../components/chat/SaveAsArtifactModal';
import type { ThemeMode } from '../hooks/useTheme';
import { fetchMessages, streamChat } from '../services/chatService';
import {
  fetchConfiguredProviders,
  fetchProviderDetail,
  fetchProviderModels,
  setDefaultModel,
} from '../services/providerService';
import { uploadLocalFile } from '../services/workspaceService';
import type { ChatMessage } from '../types/chat';
import type { PageId } from '../types/navigation';
import type {
  ConfiguredProviderDetail,
  ConfiguredProviderSummary,
} from '../types/provider';
import type { UploadedFileMetadata } from '../types/workspace';

interface ChatPageProps {
  theme: ThemeMode;
  activeConversationId: string | null;
  activeProjectId?: string | null;
  onConversationCreated: (conversationId: string) => void;
  onConversationsChanged: () => void;
  onActiveModelLabelChange: (label: string | null) => void;
  onNavigate: (page: PageId) => void;
  draftPrompt: string;
  onDraftPromptChange: (value: string) => void;
  sendOnEnter: boolean;
  showTokenUsage: boolean;
}

const SUGGESTED_PROMPTS = [
  {
    icon: Code2,
    title: 'Review architecture',
    prompt:
      'Review a local-first Python + React architecture and suggest improvements for maintainability.',
  },
  {
    icon: FileText,
    title: 'Summarize technical notes',
    prompt:
      'Help me distill a set of engineering notes into concise action items and open questions.',
  },
  {
    icon: Lightbulb,
    title: 'Compare model trade-offs',
    prompt:
      'Compare when to use a local Ollama model versus a hosted frontier model for coding tasks.',
  },
  {
    icon: PenLine,
    title: 'Draft a project spec',
    prompt:
      'Outline a clear technical specification with goals, constraints, and milestones.',
  },
];

function getTimeGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export function ChatPage({
  theme,
  activeConversationId,
  activeProjectId,
  onConversationCreated,
  onConversationsChanged,
  onActiveModelLabelChange,
  onNavigate,
  draftPrompt,
  onDraftPromptChange,
  sendOnEnter,
  showTokenUsage,
}: ChatPageProps) {
  const [providers, setProviders] = useState<ConfiguredProviderSummary[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<string>('');
  const [selectedProviderDetail, setSelectedProviderDetail] =
    useState<ConfiguredProviderDetail | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [selectedCredentialId, setSelectedCredentialId] = useState<string>('');

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [contextNotice, setContextNotice] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<UploadedFileMetadata[]>([]);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [artifactDraftContent, setArtifactDraftContent] = useState<string | null>(
    null
  );

  const abortControllerRef = useRef<AbortController | null>(null);
  const bottomAnchorRef = useRef<HTMLDivElement | null>(null);

  // Load configured providers
  useEffect(() => {
    let active = true;
    void fetchConfiguredProviders()
      .then((list) => {
        if (!active) return;
        setProviders(list);
        const enabled = list.filter((p) => p.enabled);
        if (enabled.length > 0 && !selectedProviderId) {
          setSelectedProviderId(enabled[0].id);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [selectedProviderId]);

  // Load selected provider details (models & credentials)
  useEffect(() => {
    if (!selectedProviderId) {
      setSelectedProviderDetail(null);
      return;
    }
    let active = true;
    void fetchProviderDetail(selectedProviderId)
      .then(async (detail) => {
        if (!active) return;
        let available = detail.models.filter((m) => m.is_available);

        // No models yet → auto-discover them from the provider and pick a default
        if (available.length === 0) {
          try {
            const res = await fetchProviderModels(selectedProviderId, true);
            if (!active) return;
            available = res.models.filter((m) => m.is_available);
            detail = { ...detail, models: res.models };
            if (available.length > 0) {
              const preferred =
                available.find((m) => m.model_id === 'gemini-flash-latest') ||
                available.find((m) => /flash|mini|haiku|sonnet/i.test(m.model_id) && !/preview|exp|tts|image|embed/i.test(m.model_id)) ||
                available[0];
              detail = { ...detail, default_model: preferred.model_id };
              void setDefaultModel(selectedProviderId, preferred.model_id).catch(() => {});
              setChatError(null);
            } else if (res.discovery_warning) {
              setChatError(`Model list load hoy nai: ${res.discovery_warning}`);
            }
          } catch (err) {
            if (!active) return;
            setChatError(
              `Model list load hoy nai. API key ta AI Providers page e check korun. (${err instanceof Error ? err.message : 'error'})`
            );
          }
        }

        setSelectedProviderDetail(detail);
        const defaultOrFirst =
          detail.default_model || available[0]?.model_id || '';
        setSelectedModelId((prev) => {
          if (prev && available.some((m) => m.model_id === prev)) return prev;
          return defaultOrFirst;
        });
        const activeCred =
          detail.credentials.find((c) => c.is_active) || detail.credentials[0];
        setSelectedCredentialId(activeCred?.id || '');
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [selectedProviderId]);

  // Report current provider + model label to TopNav
  useEffect(() => {
    if (selectedProviderDetail && selectedModelId) {
      onActiveModelLabelChange(
        `${selectedProviderDetail.display_name} · ${selectedModelId}`
      );
    } else {
      onActiveModelLabelChange(null);
    }
  }, [selectedProviderDetail, selectedModelId, onActiveModelLabelChange]);

  // Load messages when active conversation changes
  const loadHistory = useCallback(async (convId: string) => {
    setLoadingMessages(true);
    setChatError(null);
    setContextNotice(null);
    try {
      const res = await fetchMessages(convId);
      setMessages(res.messages);
    } catch (err) {
      setChatError(
        err instanceof Error ? err.message : 'Failed to load conversation history.'
      );
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      setChatError(null);
      setContextNotice(null);
      return;
    }
    if (!isStreaming) {
      void loadHistory(activeConversationId);
    }
  }, [activeConversationId, isStreaming, loadHistory]);

  // Scroll to bottom as messages arrive
  useEffect(() => {
    bottomAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isStreaming]);

  const runStream = async (opts: {
    content?: string;
    regenerateMessageId?: string;
    editMessageId?: string;
  }) => {
    setChatError(null);
    setContextNotice(null);

    if (!selectedProviderId) {
      setChatError(
        'No AI provider is configured yet. Open AI Providers to add a provider and API key (or Ollama).'
      );
      return;
    }
    if (!selectedModelId.trim()) {
      setChatError(
        'Select or enter a model identifier before sending a message.'
      );
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    setIsStreaming(true);

    let streamedConvId = activeConversationId;
    let assistantPlaceholderId = '';

    const currentAttachmentIds = attachedFiles.map((f) => f.id);

    try {
      await streamChat(
        {
          conversation_id: activeConversationId,
          content: opts.content ?? null,
          provider_id: selectedProviderId,
          model_id: selectedModelId.trim(),
          credential_id: selectedCredentialId || null,
          project_id: activeProjectId ?? null,
          attachment_ids: currentAttachmentIds,
          regenerate_message_id: opts.regenerateMessageId ?? null,
          edit_message_id: opts.editMessageId ?? null,
        },
        {
          onStart: (start) => {
            streamedConvId = start.conversation_id;
            assistantPlaceholderId = start.assistant_message_id;

            if (!activeConversationId) {
              onConversationCreated(start.conversation_id);
            }
            if (start.context_truncated && start.excluded_messages_count > 0) {
              setContextNotice(
                `${start.excluded_messages_count} older message${
                  start.excluded_messages_count === 1 ? '' : 's'
                } excluded to fit the model context window.`
              );
            }

            const placeholder: ChatMessage = {
              id: start.assistant_message_id,
              conversation_id: start.conversation_id,
              role: 'assistant',
              content: '',
              provider_id: start.provider_id,
              provider_name: start.provider_name,
              model_id: start.model_id,
              model_name: start.model_id,
              credential_id: selectedCredentialId || null,
              status: 'streaming',
              error_message: null,
              token_usage: null,
              created_at: new Date().toISOString(),
            };

            setMessages((prev) => {
              if (opts.regenerateMessageId) {
                const idx = prev.findIndex((m) => m.id === opts.regenerateMessageId);
                if (idx >= 0) {
                  return [...prev.slice(0, idx), placeholder];
                }
              }
              if (opts.editMessageId && start.user_message) {
                const idx = prev.findIndex((m) => m.id === opts.editMessageId);
                if (idx >= 0) {
                  return [...prev.slice(0, idx), start.user_message, placeholder];
                }
              }
              const next = [...prev];
              if (
                start.user_message &&
                !next.some((m) => m.id === start.user_message!.id)
              ) {
                next.push(start.user_message);
              }
              next.push(placeholder);
              return next;
            });
          },
          onDelta: (messageId, delta) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === messageId ? { ...m, content: m.content + delta } : m
              )
            );
          },
          onComplete: (finalMsg) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === finalMsg.id ? finalMsg : m))
            );
          },
          onStopped: (stoppedMsg) => {
            setMessages((prev) =>
              prev.map((m) => (m.id === stoppedMsg.id ? stoppedMsg : m))
            );
          },
          onError: (err) => {
            if (err.message_record) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === err.message_record!.id ? err.message_record! : m
                )
              );
            } else {
              setChatError(err.message);
            }
          },
        },
        controller.signal
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        if (assistantPlaceholderId) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantPlaceholderId ? { ...m, status: 'stopped' } : m
            )
          );
        }
      } else {
        setChatError(
          err instanceof Error ? err.message : 'Streaming connection failed.'
        );
      }
    } finally {
      abortControllerRef.current = null;
      setIsStreaming(false);
      onConversationsChanged();
      if (streamedConvId) {
        // Re-sync cleanly with persisted DB state after cancellation/completion
        void fetchMessages(streamedConvId)
          .then((res) => setMessages(res.messages))
          .catch(() => {});
      }
    }
  };

  const handleSend = (text: string) => {
    onDraftPromptChange('');
    void runStream({ content: text });
    setAttachedFiles([]);
  };

  const handleAttachFiles = async (fileList: FileList) => {
    setUploadingFile(true);
    setChatError(null);
    try {
      const uploaded: UploadedFileMetadata[] = [];
      for (const file of Array.from(fileList)) {
        const res = await uploadLocalFile(file, {
          projectId: activeProjectId ?? undefined,
          conversationId: activeConversationId ?? undefined,
        });
        uploaded.push(res);
      }
      setAttachedFiles((prev) => [...prev, ...uploaded]);
    } catch (err) {
      setChatError(
        err instanceof Error ? err.message : 'File upload failed.'
      );
    } finally {
      setUploadingFile(false);
    }
  };

  const handleStop = () => {
    abortControllerRef.current?.abort();
  };

  const handleRegenerate = (messageId: string) => {
    void runStream({ regenerateMessageId: messageId });
  };

  const handleEditAndResend = (messageId: string, newContent: string) => {
    void runStream({ editMessageId: messageId, content: newContent });
  };

  const enabledProvidersCount = providers.filter((p) => p.enabled).length;
  const showWelcome = !activeConversationId && messages.length === 0;

  return (
    <div className="mx-auto flex min-h-full max-w-3xl flex-col justify-between px-4 py-6 sm:px-6">
      {showWelcome ? (
        <div className="my-auto flex flex-col items-center py-6 text-center">
          <div className="mb-5">
            <BrandMark className="h-11 w-11" />
          </div>

          <h2 className="font-serif text-3xl font-normal tracking-tight text-ink-primary sm:text-4xl">
            {getTimeGreeting()}.
          </h2>
          <p className="mt-2.5 max-w-lg text-sm leading-relaxed text-ink-secondary">
            Your private, local-first multi-provider AI workspace. Switch
            between cloud APIs and local Ollama models in one unified chat.
          </p>

          {enabledProvidersCount === 0 && (
            <div className="mt-6 w-full rounded-2xl border border-border bg-surface-elevated p-4 text-left">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent">
                    <ShieldCheck className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-ink-primary">
                      No AI provider connected yet
                    </h3>
                    <p className="mt-0.5 text-xs leading-relaxed text-ink-secondary">
                      Add an API key (Claude, Gemini, OpenAI, DeepSeek, Grok,
                      Mistral, Groq, OpenRouter) or connect local Ollama to start
                      chatting.
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onNavigate('providers')}
                  className="inline-flex shrink-0 items-center justify-center gap-1.5 rounded-xl bg-accent px-3.5 py-2 text-xs font-medium text-white transition-colors hover:bg-accent-hover"
                >
                  <span>Connect Provider</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}

          <div className="mt-6 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2">
            {SUGGESTED_PROMPTS.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => {
                    onDraftPromptChange(item.prompt);
                    setChatError(null);
                  }}
                  className="group flex items-start gap-3 rounded-xl border border-border bg-surface-elevated/70 p-3.5 text-left transition-colors hover:border-border-strong hover:bg-surface-elevated"
                >
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface text-ink-secondary transition-colors group-hover:text-accent">
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-ink-primary">
                      {item.title}
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-ink-secondary">
                      {item.prompt}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="flex-1 space-y-6 pb-6">
          {contextNotice && (
            <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3.5 py-2 text-xs text-ink-secondary">
              <Info className="h-3.5 w-3.5 shrink-0 text-accent" />
              <span>{contextNotice}</span>
            </div>
          )}

          {loadingMessages ? (
            <p className="py-12 text-center text-xs text-ink-muted">
              Loading conversation history...
            </p>
          ) : (
            messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                theme={theme}
                showTokenUsage={showTokenUsage}
                isStreaming={isStreaming}
                onRegenerate={handleRegenerate}
                onEditAndResend={handleEditAndResend}
                onSaveAsArtifact={(content) => setArtifactDraftContent(content)}
              />
            ))
          )}
          <div ref={bottomAnchorRef} />
        </div>
      )}

      {/* Bottom sticky composer */}
      <div className="sticky bottom-0 bg-canvas/95 pt-3 backdrop-blur-sm">
        {chatError && (
          <div className="mb-3 flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-2.5 text-xs leading-relaxed text-rose-700 dark:text-rose-300">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="flex-1">{chatError}</div>
          </div>
        )}

        <MessageComposer
          value={draftPrompt}
          onChange={onDraftPromptChange}
          onSend={handleSend}
          onStop={handleStop}
          isStreaming={isStreaming}
          sendOnEnter={sendOnEnter}
          providers={providers}
          selectedProviderId={selectedProviderId}
          onSelectProvider={(id) => {
            setSelectedProviderId(id);
            setSelectedModelId('');
          }}
          selectedProviderDetail={selectedProviderDetail}
          selectedModelId={selectedModelId}
          onSelectModel={setSelectedModelId}
          selectedCredentialId={selectedCredentialId}
          onSelectCredential={setSelectedCredentialId}
          attachedFiles={attachedFiles}
          onAttachFiles={(files) => void handleAttachFiles(files)}
          onRemoveAttachedFile={(id) =>
            setAttachedFiles((prev) => prev.filter((f) => f.id !== id))
          }
          uploadingFile={uploadingFile}
          onOpenProviders={() => onNavigate('providers')}
        />

        <p className="mt-2 text-center text-[11px] text-ink-muted">
          All conversations and credentials stay local on this machine · Shift+Enter
          for new line
        </p>
      </div>

      {artifactDraftContent !== null && (
        <SaveAsArtifactModal
          initialContent={artifactDraftContent}
          conversationId={activeConversationId}
          onClose={() => setArtifactDraftContent(null)}
          onSaved={() => {
            setArtifactDraftContent(null);
            onNavigate('artifacts');
          }}
        />
      )}
    </div>
  );
}
