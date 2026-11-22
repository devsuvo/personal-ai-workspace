import { useState, type ReactNode } from 'react';
import { Sidebar } from '../components/layout/Sidebar';
import { TopNav } from '../components/layout/TopNav';
import type { SystemStatusState } from '../hooks/useSystemStatus';
import type { ThemeMode } from '../hooks/useTheme';
import type { ConversationSummary } from '../types/chat';
import type { PageId } from '../types/navigation';

interface WorkspaceLayoutProps {
  activePage: PageId;
  activeConversationTitle?: string | null;
  activeModelLabel?: string | null;
  onSelectPage: (page: PageId) => void;
  onNewChat: () => void;
  theme: ThemeMode;
  onToggleTheme: () => void;
  sidebarCollapsed: boolean;
  onToggleSidebarCollapsed: () => void;
  systemStatus: SystemStatusState;
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSelectConversation: (conversationId: string) => void;
  onRenameConversation: (conversationId: string, newTitle: string) => void;
  onTogglePinConversation: (conversationId: string, isPinned: boolean) => void;
  onClearConversation: () => void;
  onDeleteConversation: (conversationId: string) => void;
  children: ReactNode;
}

export function WorkspaceLayout({
  activePage,
  activeConversationTitle,
  activeModelLabel,
  onSelectPage,
  onNewChat,
  theme,
  onToggleTheme,
  sidebarCollapsed,
  onToggleSidebarCollapsed,
  systemStatus,
  conversations,
  activeConversationId,
  searchQuery,
  onSearchChange,
  onSelectConversation,
  onRenameConversation,
  onTogglePinConversation,
  onClearConversation,
  onDeleteConversation,
  children,
}: WorkspaceLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-canvas text-ink-primary">
      <Sidebar
        activePage={activePage}
        onSelectPage={onSelectPage}
        onNewChat={onNewChat}
        collapsed={sidebarCollapsed}
        onToggleCollapse={onToggleSidebarCollapsed}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
        systemStatus={systemStatus}
        conversations={conversations}
        activeConversationId={activeConversationId}
        searchQuery={searchQuery}
        onSearchChange={onSearchChange}
        onSelectConversation={onSelectConversation}
        onRenameConversation={onRenameConversation}
        onTogglePinConversation={onTogglePinConversation}
        onDeleteConversation={onDeleteConversation}
      />

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopNav
          activePage={activePage}
          activeConversationId={activeConversationId}
          activeConversationTitle={activeConversationTitle}
          activeModelLabel={activeModelLabel}
          onClearConversation={onClearConversation}
          onSelectPage={onSelectPage}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
          theme={theme}
          onToggleTheme={onToggleTheme}
          systemStatus={systemStatus}
        />

        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
