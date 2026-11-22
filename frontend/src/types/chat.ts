export interface ConversationSummary {
  id: string;
  title: string;
  project_id: string | null;
  provider_id: string | null;
  model_name: string | null;
  system_prompt: string;
  is_pinned: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface TokenUsage {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | string;
  content: string;
  provider_id: string | null;
  provider_name: string | null;
  model_id: string | null;
  model_name: string | null;
  credential_id: string | null;
  status: 'completed' | 'streaming' | 'stopped' | 'error' | string;
  error_message: string | null;
  token_usage: TokenUsage | null;
  created_at: string;
}

export interface MessageListResponse {
  conversation_id: string;
  messages: ChatMessage[];
  total: number;
  limit: number;
  offset: number;
}

export interface ChatStreamPayload {
  conversation_id?: string | null;
  content?: string | null;
  provider_id: string;
  model_id: string;
  credential_id?: string | null;
  project_id?: string | null;
  attachment_ids?: string[];
  regenerate_message_id?: string | null;
  edit_message_id?: string | null;
}

export interface StreamMessageStartEvent {
  conversation_id: string;
  conversation_title: string;
  user_message: ChatMessage | null;
  assistant_message_id: string;
  provider_id: string;
  provider_name: string;
  model_id: string;
  context_truncated: boolean;
  excluded_messages_count: number;
  attached_files?: string[];
}
