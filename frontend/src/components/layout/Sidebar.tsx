import {
  BarChart3,
  BookMarked,
  Check,
  Cpu,
  FolderKanban,
  Layers,
  MessageSquare,
  MessageSquarePlus,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Pin,
  Search,
  Settings,
  Sparkles,
  Trash2,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useState } from 'react';
import { BrandMark } from '../../assets/BrandMark';
import type { SystemStatusState } from '../../hooks/useSystemStatus';
import type { ConversationSummary } from '../../types/chat';
import type { PageId } from '../../types/navigation';

interface SidebarProps {
  activePage: PageId;
  onSelectPage: (page: PageId) => void;
  onNewChat: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  systemStatus: SystemStatusState;
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSelectConversation: (conversationId: string) => void;
  onRenameConversation: (conversationId: string, newTitle: string) => void;
  onTogglePinConversation: (conversationId: string, isPinned: boolean) => void;
  onDeleteConversation: (conversationId: string) => void;
}

interface SidebarNavItem {
  id: PageId;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: SidebarNavItem[] = [
  { id: 'projects', label: 'Projects', icon: FolderKanban },
  { id: 'tools', label: 'AI Tools', icon: Sparkles },
  { id: 'prompts', label: 'Prompt Library', icon: BookMarked },
  { id: 'providers', label: 'AI Providers', icon: Cpu },
  { id: 'artifacts', label: 'Artifacts', icon: Layers },
  { id: 'usage', label: 'Usage', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({
  activePage,
  onSelectPage,
  onNewChat,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  systemStatus,
  conversations,
  activeConversationId,
  searchQuery,
  onSearchChange,
  onSelectConversation,
  onRenameConversation,
  onTogglePinConversation,
  onDeleteConversation,
}: SidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  const isBackendHealthy = systemStatus.health?.status === 'ok';
  const backendStatusLabel = systemStatus.loading
    ? 'Checking backend...'
    : isBackendHealthy
      ? 'Local backend connected'
      : 'Backend offline';

  const handleNavClick = (page: PageId) => {
    onSelectPage(page);
    onCloseMobile();
  };

  const handleNewChatClick = () => {
    onNewChat();
    onCloseMobile();
  };

  const handleSelectConv = (id: string) => {
    onSelectConversation(id);
    onCloseMobile();
  };

  const commitRename = (id: string) => {
    const trimmed = editingTitle.trim();
    setEditingId(null);
    if (trimmed) {
      onRenameConversation(id, trimmed);
    }
  };

  const sidebarContent = (
    <aside
      className={`flex h-full flex-col border-r border-border bg-surface transition-all duration-200 ${
        collapsed ? 'w-[68px]' : 'w-[268px]'
      }`}
    >
      {/* Header: Brand + Collapse */}
      <div className="flex h-14 items-center justify-between border-b border-border/70 px-3">
        <button
          type="button"
          onClick={handleNewChatClick}
          className="flex min-w-0 items-center gap-2.5 rounded-lg p-1 text-left transition-colors hover:bg-surface-hover"
          title="Personal AI Workspace"
        >
          <BrandMark className="h-7 w-7 shrink-0" />
          {!collapsed && (
            <div className="min-w-0">
              <div className="truncate text-xs font-semibold tracking-wider text-ink-primary">
                PERSONAL AI
              </div>
              <div className="truncate text-[10px] font-medium tracking-widest text-ink-muted">
                WORKSPACE
              </div>
            </div>
          )}
        </button>

        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="hidden h-8 w-8 shrink-0 items-center justify-center rounded-lg text-ink-secondary transition-colors hover:bg-surface-hover hover:text-ink-primary lg:inline-flex"
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </button>

        <button
          type="button"
          onClick={onCloseMobile}
          aria-label="Close navigation menu"
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-ink-secondary transition-colors hover:bg-surface-hover hover:text-ink-primary lg:hidden"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Primary action: New Chat + Search */}
      <div className="space-y-2 p-3">
        <button
          type="button"
          onClick={handleNewChatClick}
          title="New Chat"
          className={`flex w-full items-center gap-2.5 rounded-xl border border-border bg-surface-elevated px-3 py-2 text-sm font-medium text-ink-primary shadow-sm transition-colors hover:border-border-strong hover:bg-surface-hover ${
            collapsed ? 'justify-center px-0' : ''
          }`}
        >
          <MessageSquarePlus className="h-4 w-4 shrink-0 text-accent" />
          {!collapsed && <span>New Chat</span>}
        </button>

        {!collapsed ? (
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search conversations..."
              aria-label="Search conversations"
              className="w-full rounded-lg border border-border bg-canvas/70 py-1.5 pl-8 pr-3 text-xs text-ink-primary placeholder:text-ink-muted focus:border-border-strong focus:outline-none"
            />
          </div>
        ) : (
          <button
            type="button"
            onClick={onToggleCollapse}
            title="Search conversations"
            aria-label="Search conversations"
            className="flex w-full items-center justify-center rounded-lg py-2 text-ink-secondary transition-colors hover:bg-surface-hover hover:text-ink-primary"
          >
            <Search className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Recent Conversations + Workspace Nav */}
      <div className="flex-1 overflow-y-auto px-3 py-1">
        {!collapsed && (
          <div className="mb-4">
            <div className="mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-ink-muted">
              Recent Conversations
            </div>

            {conversations.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border bg-canvas/50 px-3 py-4 text-center">
                <p className="text-xs font-medium text-ink-secondary">
                  {searchQuery.trim()
                    ? 'No matching conversations'
                    : 'No conversations yet'}
                </p>
                <p className="mt-1 text-[11px] leading-relaxed text-ink-muted">
                  Start a new chat to save history locally in SQLite.
                </p>
              </div>
            ) : (
              <div className="space-y-0.5">
                {conversations.map((conv) => {
                  const isActive =
                    activePage === 'chat' && activeConversationId === conv.id;
                  const isEditing = editingId === conv.id;

                  return (
                    <div
                      key={conv.id}
                      className={`group flex items-center gap-1 rounded-xl px-2 py-1.5 text-xs transition-colors ${
                        isActive
                          ? 'bg-surface-elevated text-ink-primary shadow-sm ring-1 ring-border'
                          : 'text-ink-secondary hover:bg-surface-hover hover:text-ink-primary'
                      }`}
                    >
                      {isEditing ? (
                        <div className="flex flex-1 items-center gap-1">
                          <input
                            type="text"
                            autoFocus
                            value={editingTitle}
                            onChange={(e) => setEditingTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') commitRename(conv.id);
                              if (e.key === 'Escape') setEditingId(null);
                            }}
                            className="min-w-0 flex-1 rounded bg-canvas px-1.5 py-0.5 text-xs text-ink-primary focus:outline-none"
                          />
                          <button
                            type="button"
                            onClick={() => commitRename(conv.id)}
                            className="p-0.5 text-emerald-600"
                            aria-label="Save title"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => handleSelectConv(conv.id)}
                            className="flex min-w-0 flex-1 items-center gap-2 text-left"
                            title={conv.title}
                          >
                            {conv.is_pinned ? (
                              <Pin className="h-3.5 w-3.5 shrink-0 text-accent" />
                            ) : (
                              <MessageSquare className="h-3.5 w-3.5 shrink-0 text-ink-muted" />
                            )}
                            <span className="truncate font-medium">
                              {conv.title}
                            </span>
                          </button>

                          <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                            <button
                              type="button"
                              onClick={() =>
                                onTogglePinConversation(conv.id, !conv.is_pinned)
                              }
                              title={conv.is_pinned ? 'Unpin' : 'Pin'}
                              aria-label={conv.is_pinned ? 'Unpin conversation' : 'Pin conversation'}
                              className={`rounded p-1 hover:bg-canvas ${
                                conv.is_pinned ? 'text-accent' : 'text-ink-muted hover:text-ink-primary'
                              }`}
                            >
                              <Pin className="h-3 w-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setEditingId(conv.id);
                                setEditingTitle(conv.title);
                              }}
                              title="Rename"
                              aria-label="Rename conversation"
                              className="rounded p-1 text-ink-muted hover:bg-canvas hover:text-ink-primary"
                            >
                              <Pencil className="h-3 w-3" />
                            </button>
                            <button
                              type="button"
                              onClick={() => onDeleteConversation(conv.id)}
                              title="Delete"
                              aria-label="Delete conversation"
                              className="rounded p-1 text-ink-muted hover:bg-rose-500/10 hover:text-rose-600"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        <nav aria-label="Workspace sections" className="space-y-1">
          {!collapsed && (
            <div className="mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-ink-muted">
              Workspace
            </div>
          )}
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleNavClick(item.id)}
                title={collapsed ? item.label : undefined}
                className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-sm font-medium transition-colors ${
                  collapsed ? 'justify-center px-0' : ''
                } ${
                  isActive
                    ? 'bg-surface-elevated text-ink-primary shadow-sm ring-1 ring-border'
                    : 'text-ink-secondary hover:bg-surface-hover hover:text-ink-primary'
                }`}
              >
                <Icon
                  className={`h-4 w-4 shrink-0 ${
                    isActive ? 'text-accent' : 'text-ink-muted'
                  }`}
                />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer: Local Status */}
      <div className="border-t border-border/70 p-3">
        <button
          type="button"
          onClick={() => handleNavClick('settings')}
          title={backendStatusLabel}
          className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-xs transition-colors hover:bg-surface-hover ${
            collapsed ? 'justify-center px-0' : ''
          }`}
        >
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${
              systemStatus.loading
                ? 'bg-amber-400'
                : isBackendHealthy
                  ? 'bg-emerald-500'
                  : 'bg-rose-500'
            }`}
          />
          {!collapsed && (
            <div className="min-w-0 flex-1">
              <div className="truncate font-medium text-ink-primary">
                {backendStatusLabel}
              </div>
              <div className="truncate text-[11px] text-ink-muted">
                Local-first · SQLite
              </div>
            </div>
          )}
        </button>
      </div>
    </aside>
  );

  return (
    <>
      <div className="hidden h-full shrink-0 lg:block">{sidebarContent}</div>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-[1px]"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative z-10 h-full">{sidebarContent}</div>
        </div>
      )}
    </>
  );
}
