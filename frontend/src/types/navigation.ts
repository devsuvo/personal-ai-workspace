export type PageId =
  | 'chat'
  | 'projects'
  | 'tools'
  | 'prompts'
  | 'artifacts'
  | 'providers'
  | 'usage'
  | 'settings';

export interface NavItemConfig {
  id: PageId;
  label: string;
  title: string;
  description: string;
}

export const PAGE_METADATA: Record<PageId, NavItemConfig> = {
  chat: {
    id: 'chat',
    label: 'Chat',
    title: 'New Conversation',
    description: 'Start a local AI conversation across your connected providers.',
  },
  projects: {
    id: 'projects',
    label: 'Projects',
    title: 'Projects',
    description: 'Organize instructions, files, and conversations into dedicated workspaces.',
  },
  tools: {
    id: 'tools',
    label: 'AI Tools',
    title: 'AI Tools',
    description: 'Dedicated productivity tools powered by your configured AI models.',
  },
  prompts: {
    id: 'prompts',
    label: 'Prompt Library',
    title: 'Prompt Library',
    description: 'Save, organize, and reuse your favorite prompts directly in chat.',
  },
  artifacts: {
    id: 'artifacts',
    label: 'Artifacts',
    title: 'Artifacts',
    description: 'Browse generated code, documents, and structured outputs saved locally.',
  },
  providers: {
    id: 'providers',
    label: 'AI Providers',
    title: 'AI Providers',
    description: 'Connect and manage your own API keys or local Ollama runtime.',
  },
  usage: {
    id: 'usage',
    label: 'Usage',
    title: 'Usage Analytics',
    description: 'Track local token consumption, request counts, and configured costs.',
  },
  settings: {
    id: 'settings',
    label: 'Settings',
    title: 'Settings',
    description: 'Manage local workspace preferences, diagnostics, and storage.',
  },
};
