import { useCallback, useEffect, useState } from 'react';
import { useAppSettings } from './hooks/useAppSettings';
import { useSystemStatus } from './hooks/useSystemStatus';
import { useTheme, type ThemePreference } from './hooks/useTheme';
import { WorkspaceLayout } from './layouts/WorkspaceLayout';
import { AIToolsPage } from './pages/AIToolsPage';
import { ArtifactsPage } from './pages/ArtifactsPage';
import { ChatPage } from './pages/ChatPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { PromptsPage } from './pages/PromptsPage';
import { ProvidersPage } from './pages/ProvidersPage';
import { SettingsPage } from './pages/SettingsPage';
import { UsagePage } from './pages/UsagePage';
import {
  clearConversation,
  deleteConversation,
  fetchConversations,
  updateConversation,
} from './services/chatService';
import type { ConversationSummary } from './types/chat';
import type { PageId } from './types/navigation';

export function App() {
  const [activePage, setActivePage] = useState<PageId>('chat');
  const [draftPrompt, setDraftPrompt] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    null
  );
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeModelLabel, setActiveModelLabel] = useState<string | null>(null);
  const [chatResetTick, setChatResetTick] = useState(0);

  const { theme, preference, setThemePreference, toggleTheme } = useTheme();
  const systemStatus = useSystemStatus();
  const appSettings = useAppSettings();

  // Hydrate persisted theme & sidebar preference from backend on startup
  useEffect(() => {
    const savedTheme = appSettings.items.theme?.value;
    if (
      savedTheme === 'light' ||
      savedTheme === 'dark' ||
      savedTheme === 'system'
    ) {
      setThemePreference(savedTheme);
    }
    if (typeof appSettings.items.sidebar_collapsed?.value === 'boolean') {
      setSidebarCollapsed(appSettings.items.sidebar_collapsed.value);
    }
  }, [
    appSettings.items.theme?.value,
    appSettings.items.sidebar_collapsed?.value,
    setThemePreference,
  ]);

  const loadConversations = useCallback(async (query: string) => {
    try {
      const res = await fetchConversations(query, 50, 0);
      setConversations(res.conversations);
    } catch {
      // Backend offline status is already surfaced in the sidebar footer
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadConversations(searchQuery);
    }, 180);
    return () => window.clearTimeout(timer);
  }, [searchQuery, loadConversations]);

  const handleNewChat = useCallback(() => {
    setActiveConversationId(null);
    setActiveProjectId(null);
    setDraftPrompt('');
    setActivePage('chat');
  }, []);

  // Global keyboard shortcuts (Ctrl/Cmd + Shift + N for New Chat)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        handleNewChat();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [handleNewChat]);

  const handleToggleTheme = () => {
    const next = toggleTheme();
    void appSettings.saveSetting('theme', next).catch(() => {});
  };

  const handleChangeThemePreference = (next: ThemePreference) => {
    setThemePreference(next);
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      void appSettings.saveSetting('sidebar_collapsed', next).catch(() => {});
      return next;
    });
  };

  const handleStartChatInProject = (projectId: string) => {
    setActiveConversationId(null);
    setActiveProjectId(projectId);
    setDraftPrompt('');
    setActivePage('chat');
  };

  const handleSelectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId);
    setActivePage('chat');
  };

  const handleRenameConversation = (
    conversationId: string,
    newTitle: string
  ) => {
    void updateConversation(conversationId, { title: newTitle })
      .then(() => loadConversations(searchQuery))
      .catch(() => {});
  };

  const handleTogglePinConversation = (
    conversationId: string,
    isPinned: boolean
  ) => {
    void updateConversation(conversationId, { is_pinned: isPinned })
      .then(() => loadConversations(searchQuery))
      .catch(() => {});
  };

  const handleClearConversation = () => {
    if (!activeConversationId) return;
    if (!window.confirm('Clear all messages in this conversation?')) return;
    void clearConversation(activeConversationId)
      .then(() => {
        setChatResetTick((t) => t + 1);
        return loadConversations(searchQuery);
      })
      .catch(() => {});
  };

  const handleDeleteConversation = (conversationId: string) => {
    void deleteConversation(conversationId)
      .then(() => {
        if (activeConversationId === conversationId) {
          setActiveConversationId(null);
        }
        return loadConversations(searchQuery);
      })
      .catch(() => {});
  };

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId
  );

  const sendOnEnter =
    typeof appSettings.items.chat_send_on_enter?.value === 'boolean'
      ? appSettings.items.chat_send_on_enter.value
      : true;
  const showTokenUsage =
    typeof appSettings.items.chat_show_token_usage?.value === 'boolean'
      ? appSettings.items.chat_show_token_usage.value
      : true;

  const renderPage = () => {
    switch (activePage) {
      case 'chat':
        return (
          <ChatPage
            key={chatResetTick}
            theme={theme}
            activeConversationId={activeConversationId}
            activeProjectId={activeProjectId}
            onConversationCreated={(id) => {
              setActiveConversationId(id);
              void loadConversations(searchQuery);
            }}
            onConversationsChanged={() => void loadConversations(searchQuery)}
            onActiveModelLabelChange={setActiveModelLabel}
            onNavigate={setActivePage}
            draftPrompt={draftPrompt}
            onDraftPromptChange={setDraftPrompt}
            sendOnEnter={sendOnEnter}
            showTokenUsage={showTokenUsage}
          />
        );
      case 'projects':
        return (
          <ProjectsPage
            onOpenConversation={handleSelectConversation}
            onStartChatInProject={handleStartChatInProject}
            onOpenArtifacts={() => setActivePage('artifacts')}
          />
        );
      case 'tools':
        return <AIToolsPage theme={theme} onNavigate={setActivePage} />;
      case 'prompts':
        return (
          <PromptsPage
            onUseInChat={(content) => {
              setDraftPrompt(content);
              setActivePage('chat');
            }}
          />
        );
      case 'artifacts':
        return <ArtifactsPage theme={theme} />;
      case 'providers':
        return <ProvidersPage systemStatus={systemStatus} />;
      case 'usage':
        return <UsagePage />;
      case 'settings':
        return (
          <SettingsPage
            themePreference={preference}
            onChangeThemePreference={handleChangeThemePreference}
            sidebarCollapsed={sidebarCollapsed}
            onChangeSidebarCollapsed={setSidebarCollapsed}
            appSettings={appSettings}
            systemStatus={systemStatus}
          />
        );
    }
  };

  return (
    <WorkspaceLayout
      activePage={activePage}
      activeConversationTitle={activeConversation?.title ?? null}
      activeModelLabel={activeModelLabel}
      onSelectPage={setActivePage}
      onNewChat={handleNewChat}
      theme={theme}
      onToggleTheme={handleToggleTheme}
      sidebarCollapsed={sidebarCollapsed}
      onToggleSidebarCollapsed={handleToggleSidebar}
      systemStatus={systemStatus}
      conversations={conversations}
      activeConversationId={activeConversationId}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
      onSelectConversation={handleSelectConversation}
      onRenameConversation={handleRenameConversation}
      onTogglePinConversation={handleTogglePinConversation}
      onClearConversation={handleClearConversation}
      onDeleteConversation={handleDeleteConversation}
    >
      {renderPage()}
    </WorkspaceLayout>
  );
}

export default App;
