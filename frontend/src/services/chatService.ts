import type {
  ChatMessage,
  ChatStreamPayload,
  ConversationListResponse,
  ConversationSummary,
  MessageListResponse,
  StreamMessageStartEvent,
} from '../types/chat';
import { API_BASE_URL, ApiClientError, apiRequest } from './apiClient';

export function fetchConversations(
  search = '',
  limit = 50,
  offset = 0
): Promise<ConversationListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (search.trim()) {
    params.set('search', search.trim());
  }
  return apiRequest<ConversationListResponse>(`/conversations?${params.toString()}`);
}

export function createConversation(payload: {
  title?: string;
  provider_id?: string | null;
  model_name?: string | null;
}): Promise<ConversationSummary> {
  return apiRequest<ConversationSummary>('/conversations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateConversation(
  conversationId: string,
  payload: {
    title?: string;
    project_id?: string | null;
    provider_id?: string | null;
    model_name?: string | null;
    system_prompt?: string;
    is_pinned?: boolean;
  }
): Promise<ConversationSummary> {
  return apiRequest<ConversationSummary>(
    `/conversations/${encodeURIComponent(conversationId)}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  );
}

export function clearConversation(
  conversationId: string
): Promise<ConversationSummary> {
  return apiRequest<ConversationSummary>(
    `/conversations/${encodeURIComponent(conversationId)}/clear`,
    { method: 'POST' }
  );
}

export function getConversationExportUrl(
  conversationId: string,
  format: 'md' | 'txt'
): string {
  return `${API_BASE_URL}/conversations/${encodeURIComponent(conversationId)}/export?format=${format}`;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/conversations/${encodeURIComponent(conversationId)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) {
    throw new Error(`Failed to delete conversation (HTTP ${res.status})`);
  }
}

export function fetchMessages(
  conversationId: string,
  limit = 200,
  offset = 0
): Promise<MessageListResponse> {
  return apiRequest<MessageListResponse>(
    `/conversations/${encodeURIComponent(conversationId)}/messages?limit=${limit}&offset=${offset}`
  );
}

export interface StreamHandlers {
  onStart?: (data: StreamMessageStartEvent) => void;
  onDelta?: (messageId: string, delta: string) => void;
  onComplete?: (message: ChatMessage) => void;
  onStopped?: (message: ChatMessage) => void;
  onError?: (err: {
    code: string;
    message: string;
    assistant_message_id?: string;
    message_record?: ChatMessage;
  }) => void;
}

export async function streamChat(
  payload: ChatStreamPayload,
  handlers: StreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    let message = `Streaming request failed (HTTP ${response.status})`;
    let code = `HTTP_${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson?.error?.message) message = errJson.error.message;
      if (errJson?.error?.code) code = errJson.error.code;
    } catch {
      // ignore non-JSON error
    }
    throw new ApiClientError(message, response.status, code);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new ApiClientError('Browser did not return a readable stream.', 0, 'NO_STREAM');
  }

  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  const dispatchBlock = (block: string) => {
    let eventName = '';
    const dataLines: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (!eventName || dataLines.length === 0) return;
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(dataLines.join('\n')) as Record<string, unknown>;
    } catch {
      return;
    }

    if (eventName === 'message_start') {
      handlers.onStart?.(parsed as unknown as StreamMessageStartEvent);
    } else if (eventName === 'content_delta') {
      handlers.onDelta?.(
        String(parsed.message_id || ''),
        String(parsed.delta || '')
      );
    } else if (eventName === 'message_complete') {
      handlers.onComplete?.(parsed.message as ChatMessage);
    } else if (eventName === 'generation_stopped') {
      handlers.onStopped?.(parsed.message as ChatMessage);
    } else if (eventName === 'error') {
      handlers.onError?.({
        code: String(parsed.code || 'STREAM_ERROR'),
        message: String(parsed.message || 'Streaming failed.'),
        assistant_message_id: parsed.assistant_message_id
          ? String(parsed.assistant_message_id)
          : undefined,
        message_record: parsed.message_record as ChatMessage | undefined,
      });
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? '';
      for (const block of blocks) {
        if (block.trim()) {
          dispatchBlock(block);
        }
      }
    }
    if (buffer.trim()) {
      dispatchBlock(buffer);
    }
  } finally {
    reader.releaseLock();
  }
}
