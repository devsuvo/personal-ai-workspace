import { Cpu, Download, Eraser, Menu, Moon, Settings, Sun } from 'lucide-react';
import type { SystemStatusState } from '../../hooks/useSystemStatus';
import type { ThemeMode } from '../../hooks/useTheme';
import { getConversationExportUrl } from '../../services/chatService';
import { PAGE_METADATA, type PageId } from '../../types/navigation';

interface TopNavProps {
  activePage: PageId;
  activeConversationId?: string | null;
  activeConversationTitle?: string | null;
  activeModelLabel?: string | null;
  onClearConversation?: () => void;
  onSelectPage: (page: PageId) => void;
  onOpenMobileMenu: () => void;
  theme: ThemeMode;
  onToggleTheme: () => void;
  systemStatus: SystemStatusState;
}

export function TopNav({
  activePage,
  activeConversationId,
  activeConversationTitle,
  activeModelLabel,
  onClearConversation,
  onSelectPage,
  onOpenMobileMenu,
  theme,
  onToggleTheme,
  systemStatus,
}: TopNavProps) {
  const currentMeta = PAGE_METADATA[activePage];
  const configuredCount = systemStatus.systemInfo?.configured_providers_count ?? 0;

  const heading =
    activePage === 'chat' && activeConversationTitle
      ? activeConversationTitle
      : currentMeta.title;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-canvas/85 px-4 backdrop-blur-sm sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          aria-label="Open navigation menu"
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-ink-secondary transition-colors hover:bg-surface hover:text-ink-primary lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold text-ink-primary sm:text-[15px]">
            {heading}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {activePage === 'chat' && activeConversationId && (
          <div className="hidden items-center gap-1 md:flex">
            <a
              href={getConversationExportUrl(activeConversationId, 'md')}
              title="Export conversation as Markdown (.md)"
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface-elevated px-2.5 py-1.5 text-[11px] font-medium text-ink-secondary hover:border-border-strong hover:text-ink-primary"
            >
              <Download className="h-3 w-3" />
              <span>MD</span>
            </a>
            <a
              href={getConversationExportUrl(activeConversationId, 'txt')}
              title="Export conversation as Text (.txt)"
              className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface-elevated px-2.5 py-1.5 text-[11px] font-medium text-ink-secondary hover:border-border-strong hover:text-ink-primary"
            >
              <Download className="h-3 w-3" />
              <span>TXT</span>
            </a>
            {onClearConversation && (
              <button
                type="button"
                onClick={onClearConversation}
                title="Clear conversation messages"
                className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface-elevated px-2.5 py-1.5 text-[11px] font-medium text-ink-secondary hover:border-rose-500/40 hover:text-rose-600"
              >
                <Eraser className="h-3 w-3" />
                <span>Clear</span>
              </button>
            )}
          </div>
        )}

        <button
          type="button"
          onClick={() => onSelectPage('providers')}
          className="hidden items-center gap-2 rounded-full border border-border bg-surface-elevated px-3 py-1.5 text-xs font-medium text-ink-secondary transition-colors hover:border-border-strong hover:text-ink-primary sm:inline-flex"
          title="Manage AI providers"
        >
          <Cpu className="h-3.5 w-3.5 text-accent" />
          <span className="max-w-[200px] truncate">
            {activeModelLabel
              ? activeModelLabel
              : configuredCount > 0
                ? `${configuredCount} provider${configuredCount === 1 ? '' : 's'} ready`
                : 'No provider connected'}
          </span>
        </button>

        <button
          type="button"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-transparent text-ink-secondary transition-colors hover:border-border hover:bg-surface hover:text-ink-primary"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>

        <button
          type="button"
          onClick={() => onSelectPage('settings')}
          aria-label="Open Settings"
          title="Settings"
          className={`inline-flex h-9 w-9 items-center justify-center rounded-lg border transition-colors ${
            activePage === 'settings'
              ? 'border-border bg-surface-elevated text-accent'
              : 'border-transparent text-ink-secondary hover:border-border hover:bg-surface hover:text-ink-primary'
          }`}
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
