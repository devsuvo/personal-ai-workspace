import { API_BASE_URL, apiRequest } from './apiClient';

export interface AIToolOption {
  key: string;
  label: string;
  choices?: string[];
  type?: string;
  default?: string;
}

export interface AIToolDefinition {
  id: string;
  name: string;
  description: string;
  category: string;
  input_label: string;
  input_placeholder: string;
  options: AIToolOption[];
}

export interface AIToolRunResult {
  tool_id: string;
  output: string;
  provider_name: string;
  model_id: string;
  token_usage: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  } | null;
}

export interface PromptTemplate {
  id: string;
  title: string;
  category: string;
  description: string;
  content: string;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModelPricing {
  id: string;
  provider_name: string;
  model_name: string;
  input_cost_per_1m: number;
  output_cost_per_1m: number;
  updated_at: string;
}

export interface ModelUsageBreakdown {
  provider_name: string;
  model_name: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost: number | null;
}

export interface PeriodUsagePoint {
  period: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

export interface AnalyticsOverview {
  total_conversations: number;
  total_messages: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  estimated_total_cost: number | null;
  has_configured_pricing: boolean;
  top_models: ModelUsageBreakdown[];
  daily_usage: PeriodUsagePoint[];
  monthly_usage: PeriodUsagePoint[];
}

// --- AI Tools ---
export async function fetchAITools(): Promise<AIToolDefinition[]> {
  const res = await apiRequest<{ tools: AIToolDefinition[] }>('/tools');
  return res.tools;
}

export function runAITool(payload: {
  tool_id: string;
  input_text: string;
  provider_id: string;
  model_id: string;
  options: Record<string, string>;
}): Promise<AIToolRunResult> {
  return apiRequest<AIToolRunResult>('/tools/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// --- Prompt Library ---
export function fetchPrompts(opts?: {
  search?: string;
  category?: string;
  favoritesOnly?: boolean;
}): Promise<{ prompts: PromptTemplate[]; categories: string[]; total: number }> {
  const params = new URLSearchParams();
  if (opts?.search?.trim()) params.set('search', opts.search.trim());
  if (opts?.category?.trim()) params.set('category', opts.category.trim());
  if (opts?.favoritesOnly) params.set('favorites_only', 'true');
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest<{
    prompts: PromptTemplate[];
    categories: string[];
    total: number;
  }>(`/prompts${query}`);
}

export function createPromptTemplate(payload: {
  title: string;
  category: string;
  description: string;
  content: string;
  is_favorite?: boolean;
}): Promise<PromptTemplate> {
  return apiRequest<PromptTemplate>('/prompts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updatePromptTemplate(
  id: string,
  payload: Partial<{
    title: string;
    category: string;
    description: string;
    content: string;
    is_favorite: boolean;
  }>
): Promise<PromptTemplate> {
  return apiRequest<PromptTemplate>(`/prompts/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deletePromptTemplate(id: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/prompts/${encodeURIComponent(id)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) throw new Error(`Failed to delete prompt (HTTP ${res.status})`);
}

// --- Analytics & Pricing ---
export function fetchAnalyticsOverview(days = 30): Promise<AnalyticsOverview> {
  return apiRequest<AnalyticsOverview>(`/analytics/overview?days=${days}`);
}

export async function fetchModelPricing(): Promise<ModelPricing[]> {
  const res = await apiRequest<{ pricing: ModelPricing[] }>('/analytics/pricing');
  return res.pricing;
}

export function upsertModelPricing(payload: {
  provider_name: string;
  model_name: string;
  input_cost_per_1m: number;
  output_cost_per_1m: number;
}): Promise<ModelPricing> {
  return apiRequest<ModelPricing>('/analytics/pricing', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteModelPricing(id: string): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/analytics/pricing/${encodeURIComponent(id)}`,
    { method: 'DELETE' }
  );
  if (!res.ok) throw new Error(`Failed to delete pricing (HTTP ${res.status})`);
}
