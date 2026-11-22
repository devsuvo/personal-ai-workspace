import {
  Archive,
  ArrowLeft,
  BookOpen,
  Code2,
  Download,
  Eye,
  FileText,
  FolderKanban,
  Layers,
  MessageSquare,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Trash2,
  Upload,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  fetchConversations,
  updateConversation,
} from '../services/chatService';
import {
  archiveProject,
  createProject,
  deleteProject,
  deleteUploadedFile,
  fetchArtifacts,
  fetchFileDetail,
  fetchFiles,
  fetchProjects,
  getFileDownloadUrl,
  reExtractFile,
  restoreProject,
  updateProject,
  uploadLocalFile,
} from '../services/workspaceService';
import type { ConversationSummary } from '../types/chat';
import type {
  ArtifactItem,
  ProjectSummary,
  UploadedFileDetail,
  UploadedFileMetadata,
} from '../types/workspace';

interface ProjectsPageProps {
  onOpenConversation: (conversationId: string) => void;
  onStartChatInProject: (projectId: string) => void;
  onOpenArtifacts: () => void;
}

const COLOR_STYLES: Record<string, string> = {
  terracotta: 'bg-accent/15 text-accent border-accent/30',
  blue: 'bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/30',
  emerald: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30',
  amber: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30',
  violet: 'bg-violet-500/15 text-violet-600 dark:text-violet-400 border-violet-500/30',
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function ProjectsPage({
  onOpenConversation,
  onStartChatInProject,
  onOpenArtifacts,
}: ProjectsPageProps) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(true);

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newInstructions, setNewInstructions] = useState('');
  const [newColor, setNewColor] = useState('terracotta');

  const [selectedProject, setSelectedProject] = useState<ProjectSummary | null>(
    null
  );
  const [workspaceTab, setWorkspaceTab] = useState<
    'instructions' | 'conversations' | 'files' | 'artifacts'
  >('instructions');

  // Selected project workspace states
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editInstructions, setEditInstructions] = useState('');
  const [projConversations, setProjConversations] = useState<
    ConversationSummary[]
  >([]);
  const [allConversations, setAllConversations] = useState<
    ConversationSummary[]
  >([]);
  const [moveConvId, setMoveConvId] = useState('');
  const [projFiles, setProjFiles] = useState<UploadedFileMetadata[]>([]);
  const [projArtifacts, setProjArtifacts] = useState<ArtifactItem[]>([]);
  const [previewFile, setPreviewFile] = useState<UploadedFileDetail | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const list = await fetchProjects(search, showArchived);
      setProjects(list);
    } finally {
      setLoading(false);
    }
  }, [search, showArchived]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadProjects(), 150);
    return () => window.clearTimeout(timer);
  }, [loadProjects]);

  const loadWorkspaceData = useCallback(async (project: ProjectSummary) => {
    setEditName(project.name);
    setEditDesc(project.description);
    setEditInstructions(project.instructions);
    try {
      const [allConvs, files, arts] = await Promise.all([
        fetchConversations('', 100, 0),
        fetchFiles({ projectId: project.id }),
        fetchArtifacts({ projectId: project.id }),
      ]);
      setAllConversations(allConvs.conversations);
      setProjConversations(
        allConvs.conversations.filter((c) => c.project_id === project.id)
      );
      setProjFiles(files);
      setProjArtifacts(arts);
    } catch {
      // handled gracefully
    }
  }, []);

  const handleOpenProject = (project: ProjectSummary) => {
    setSelectedProject(project);
    setWorkspaceTab('instructions');
    setFeedback(null);
    setConfirmDelete(false);
    void loadWorkspaceData(project);
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const created = await createProject({
        name: newName.trim(),
        description: newDesc.trim(),
        instructions: newInstructions.trim(),
        color: newColor,
        icon: 'folder',
      });
      setShowCreateModal(false);
      setNewName('');
      setNewDesc('');
      setNewInstructions('');
      await loadProjects();
      handleOpenProject(created);
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to create project.',
      });
    }
  };

  const handleSaveProject = async () => {
    if (!selectedProject) return;
    setFeedback(null);
    try {
      const updated = await updateProject(selectedProject.id, {
        name: editName.trim(),
        description: editDesc.trim(),
        instructions: editInstructions,
      });
      setSelectedProject(updated);
      await loadProjects();
      setFeedback({
        type: 'success',
        text: 'Project details and AI instructions saved locally.',
      });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to save project.',
      });
    }
  };

  const handleUploadFiles = async (fileList: FileList | null) => {
    if (!selectedProject || !fileList || fileList.length === 0) return;
    setUploading(true);
    setFeedback(null);
    try {
      for (const file of Array.from(fileList)) {
        await uploadLocalFile(file, { projectId: selectedProject.id });
      }
      await loadWorkspaceData(selectedProject);
      setFeedback({ type: 'success', text: 'File(s) uploaded and processed.' });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'File upload failed.',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleMoveConversation = async () => {
    if (!selectedProject || !moveConvId) return;
    try {
      await updateConversation(moveConvId, { project_id: selectedProject.id });
      setMoveConvId('');
      await loadWorkspaceData(selectedProject);
      setFeedback({ type: 'success', text: 'Conversation moved into project.' });
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Could not move conversation.',
      });
    }
  };

  const handleArchiveToggle = async () => {
    if (!selectedProject) return;
    const updated = selectedProject.is_archived
      ? await restoreProject(selectedProject.id)
      : await archiveProject(selectedProject.id);
    setSelectedProject(updated);
    await loadProjects();
  };

  const handleDeleteProject = async () => {
    if (!selectedProject) return;
    await deleteProject(selectedProject.id);
    setSelectedProject(null);
    setConfirmDelete(false);
    await loadProjects();
  };

  // --- Project Workspace View ---
  if (selectedProject) {
    const movableConversations = allConversations.filter(
      (c) => c.project_id !== selectedProject.id
    );

    return (
      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setSelectedProject(null);
                void loadProjects();
              }}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-surface-elevated text-ink-secondary hover:text-ink-primary"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-ink-primary">
                  {selectedProject.name}
                </h2>
                {selectedProject.is_archived && (
                  <StatusBadge variant="warning">Archived</StatusBadge>
                )}
              </div>
              <p className="text-xs text-ink-secondary">
                {selectedProject.description || 'Local project workspace'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onStartChatInProject(selectedProject.id)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-3.5 py-2 text-xs font-medium text-white hover:bg-accent-hover"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>New Project Chat</span>
            </button>
            <button
              type="button"
              onClick={() => void handleArchiveToggle()}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface-elevated px-3 py-2 text-xs font-medium text-ink-secondary hover:text-ink-primary"
            >
              {selectedProject.is_archived ? (
                <>
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Restore</span>
                </>
              ) : (
                <>
                  <Archive className="h-3.5 w-3.5" />
                  <span>Archive</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-700 dark:text-rose-300"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Delete</span>
            </button>
          </div>
        </div>

        {confirmDelete && (
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-800 dark:text-rose-200">
            <div>
              <strong>Delete &ldquo;{selectedProject.name}&rdquo;?</strong> Your
              conversations, uploaded files, and artifacts will{' '}
              <strong>not</strong> be deleted—they will remain safely in your
              local workspace unlinked from this project.
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="rounded-lg border border-border bg-surface px-3 py-1.5 text-ink-primary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleDeleteProject()}
                className="rounded-lg bg-rose-600 px-3 py-1.5 font-medium text-white hover:bg-rose-700"
              >
                Confirm Delete
              </button>
            </div>
          </div>
        )}

        {feedback && (
          <div
            className={`rounded-xl border px-4 py-3 text-xs ${
              feedback.type === 'success'
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                : 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300'
            }`}
          >
            {feedback.text}
          </div>
        )}

        {/* Workspace tabs */}
        <div className="flex flex-wrap gap-1.5 border-b border-border pb-3">
          {(
            [
              { id: 'instructions', label: 'Instructions & Details' },
              { id: 'conversations', label: `Conversations (${projConversations.length})` },
              { id: 'files', label: `Files (${projFiles.length})` },
              { id: 'artifacts', label: `Artifacts (${projArtifacts.length})` },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setWorkspaceTab(tab.id)}
              className={`rounded-xl px-3.5 py-1.5 text-xs font-medium transition-colors ${
                workspaceTab === tab.id
                  ? 'bg-surface-elevated text-ink-primary shadow-sm ring-1 ring-border'
                  : 'text-ink-secondary hover:bg-surface'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab 1: Instructions */}
        {workspaceTab === 'instructions' && (
          <section className="rounded-2xl border border-border bg-surface-elevated p-6 space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Project Name
                </label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Description
                </label>
                <input
                  type="text"
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-ink-secondary">
                Project-Specific AI Instructions
              </label>
              <p className="mb-2 text-[11px] text-ink-muted">
                Automatically included in chats inside this project. Kept separate
                from global workspace settings (project instructions take
                precedence over global defaults if conflicting).
              </p>
              <textarea
                rows={6}
                value={editInstructions}
                onChange={(e) => setEditInstructions(e.target.value)}
                placeholder="Example: I am a beginner in Python. Explain concepts step by step with simple examples."
                className="w-full rounded-xl border border-border bg-canvas p-3 text-xs leading-relaxed text-ink-primary focus:outline-none"
              />
            </div>

            <div className="flex justify-end border-t border-border/70 pt-4">
              <button
                type="button"
                onClick={() => void handleSaveProject()}
                className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
              >
                <Save className="h-3.5 w-3.5" />
                <span>Save Project</span>
              </button>
            </div>
          </section>
        )}

        {/* Tab 2: Conversations */}
        {workspaceTab === 'conversations' && (
          <section className="space-y-4">
            {movableConversations.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-border bg-surface-elevated p-4">
                <select
                  value={moveConvId}
                  onChange={(e) => setMoveConvId(e.target.value)}
                  className="min-w-[220px] flex-1 rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
                >
                  <option value="">Move an existing conversation into this project...</option>
                  {movableConversations.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={!moveConvId}
                  onClick={() => void handleMoveConversation()}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs font-medium text-ink-primary hover:bg-surface-hover disabled:opacity-50"
                >
                  Move Here
                </button>
              </div>
            )}

            {projConversations.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-surface-elevated p-8 text-center text-xs text-ink-muted">
                No conversations in this project yet. Click &ldquo;New Project Chat&rdquo;
                or move an existing conversation here.
              </div>
            ) : (
              <div className="space-y-2">
                {projConversations.map((conv) => (
                  <button
                    key={conv.id}
                    type="button"
                    onClick={() => onOpenConversation(conv.id)}
                    className="flex w-full items-center justify-between rounded-xl border border-border bg-surface-elevated p-4 text-left transition-colors hover:border-border-strong"
                  >
                    <div className="flex items-center gap-3">
                      <MessageSquare className="h-4 w-4 text-accent" />
                      <div>
                        <div className="text-sm font-medium text-ink-primary">
                          {conv.title}
                        </div>
                        <div className="text-[11px] text-ink-muted">
                          {conv.message_count} messages · Updated{' '}
                          {new Date(conv.updated_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Tab 3: Files */}
        {workspaceTab === 'files' && (
          <section className="space-y-4">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                void handleUploadFiles(e.dataTransfer.files);
              }}
              className={`rounded-2xl border-2 border-dashed p-6 text-center transition-colors ${
                isDragging
                  ? 'border-accent bg-accent/10'
                  : 'border-border bg-surface-elevated'
              }`}
            >
              <Upload className="mx-auto mb-2 h-6 w-6 text-accent" />
              <p className="text-xs font-medium text-ink-primary">
                {uploading
                  ? 'Uploading and extracting text locally...'
                  : 'Drag & drop files here, or click to browse'}
              </p>
              <p className="mt-1 text-[11px] text-ink-muted">
                PDF, DOCX, TXT, MD, CSV, XLSX, JSON, Code (PY/JS/TS/HTML/CSS/SQL/PHP),
                Images (PNG/JPG/WEBP)
              </p>
              <label className="mt-3 inline-flex cursor-pointer items-center gap-1.5 rounded-xl border border-border bg-surface px-4 py-2 text-xs font-medium text-ink-primary hover:bg-surface-hover">
                <Plus className="h-3.5 w-3.5" />
                <span>Choose Files</span>
                <input
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(e) => void handleUploadFiles(e.target.files)}
                />
              </label>
            </div>

            {projFiles.length === 0 ? (
              <p className="py-6 text-center text-xs text-ink-muted">
                No files uploaded to this project yet.
              </p>
            ) : (
              <div className="space-y-2">
                {projFiles.map((f) => (
                  <div
                    key={f.id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface-elevated p-4"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <FileText className="h-4 w-4 shrink-0 text-accent" />
                      <div className="min-w-0">
                        <div className="truncate text-xs font-semibold text-ink-primary">
                          {f.original_filename}
                        </div>
                        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
                          <span>{formatBytes(f.file_size)}</span>
                          <StatusBadge
                            variant={
                              f.extraction_status === 'completed'
                                ? 'success'
                                : f.extraction_status === 'ocr_required'
                                  ? 'warning'
                                  : f.extraction_status === 'failed'
                                    ? 'error'
                                    : 'neutral'
                            }
                          >
                            {f.extraction_status}
                          </StatusBadge>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() =>
                          void fetchFileDetail(f.id).then(setPreviewFile)
                        }
                        title="Preview"
                        className="rounded-lg border border-border bg-surface p-1.5 text-ink-secondary hover:text-ink-primary"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          void reExtractFile(f.id).then(() =>
                            loadWorkspaceData(selectedProject)
                          )
                        }
                        title="Re-extract text"
                        className="rounded-lg border border-border bg-surface p-1.5 text-ink-secondary hover:text-ink-primary"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                      </button>
                      <a
                        href={getFileDownloadUrl(f.id)}
                        download={f.original_filename}
                        title="Download original"
                        className="rounded-lg border border-border bg-surface p-1.5 text-ink-secondary hover:text-ink-primary"
                      >
                        <Download className="h-3.5 w-3.5" />
                      </a>
                      <button
                        type="button"
                        onClick={() =>
                          void deleteUploadedFile(f.id).then(() =>
                            loadWorkspaceData(selectedProject)
                          )
                        }
                        title="Delete file"
                        className="rounded-lg border border-border bg-surface p-1.5 text-rose-600 hover:bg-rose-500/10"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {previewFile && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                <div className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-surface-elevated">
                  <div className="flex items-center justify-between border-b border-border px-5 py-3">
                    <div className="truncate text-sm font-semibold text-ink-primary">
                      {previewFile.original_filename}
                    </div>
                    <button
                      type="button"
                      onClick={() => setPreviewFile(null)}
                      className="rounded-lg p-1 text-ink-secondary hover:bg-surface"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="overflow-y-auto p-5 text-xs">
                    {previewFile.is_image ? (
                      <img
                        src={getFileDownloadUrl(previewFile.id)}
                        alt={previewFile.original_filename}
                        className="mx-auto max-h-[60vh] rounded-xl border border-border"
                      />
                    ) : previewFile.extracted_text_preview ? (
                      <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-ink-primary">
                        {previewFile.extracted_text_preview}
                      </pre>
                    ) : (
                      <p className="text-ink-secondary">
                        {previewFile.extraction_error ||
                          'No extracted text available for this file.'}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* Tab 4: Artifacts */}
        {workspaceTab === 'artifacts' && (
          <section className="space-y-3">
            {projArtifacts.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-surface-elevated p-8 text-center text-xs text-ink-muted">
                No artifacts linked to this project yet.{' '}
                <button
                  type="button"
                  onClick={onOpenArtifacts}
                  className="text-accent underline"
                >
                  Open Artifacts Workspace
                </button>
              </div>
            ) : (
              projArtifacts.map((a) => (
                <button
                  key={a.id}
                  type="button"
                  onClick={onOpenArtifacts}
                  className="flex w-full items-center justify-between rounded-xl border border-border bg-surface-elevated p-4 text-left hover:border-border-strong"
                >
                  <div className="flex items-center gap-3">
                    <Layers className="h-4 w-4 text-accent" />
                    <div>
                      <div className="text-sm font-medium text-ink-primary">
                        {a.title}
                      </div>
                      <div className="text-[11px] text-ink-muted">
                        {a.artifact_type.toUpperCase()} · Updated{' '}
                        {new Date(a.updated_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </button>
              ))
            )}
          </section>
        )}
      </div>
    );
  }

  // --- Projects List View ---
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-ink-primary">Projects</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            Organize conversations, project-specific AI instructions, local files,
            and artifacts into dedicated workspaces.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 self-start rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
        >
          <Plus className="h-4 w-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Search & Archive filter */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="relative min-w-[240px] flex-1 max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects..."
            className="w-full rounded-xl border border-border bg-surface-elevated py-2 pl-9 pr-3 text-xs text-ink-primary focus:outline-none"
          />
        </div>

        <label className="inline-flex items-center gap-2 text-xs text-ink-secondary">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="h-3.5 w-3.5 accent-accent"
          />
          <span>Show archived</span>
        </label>
      </div>

      {loading ? (
        <p className="py-12 text-center text-xs text-ink-muted">Loading projects...</p>
      ) : projects.length === 0 ? (
        <div className="rounded-2xl border border-border bg-surface-elevated p-10 text-center">
          <FolderKanban className="mx-auto mb-3 h-8 w-8 text-accent" />
          <h3 className="text-base font-semibold text-ink-primary">
            No projects yet
          </h3>
          <p className="mx-auto mt-1.5 max-w-md text-xs leading-relaxed text-ink-secondary">
            Create projects like Website Development, Python Learning, or Research
            to keep custom AI instructions, files, and chats neatly separated.
          </p>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
          >
            <Plus className="h-4 w-4" />
            <span>Create First Project</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => handleOpenProject(p)}
              className="flex flex-col justify-between rounded-2xl border border-border bg-surface-elevated p-5 text-left transition-colors hover:border-border-strong"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div
                    className={`flex h-9 w-9 items-center justify-center rounded-xl border ${
                      COLOR_STYLES[p.color] || COLOR_STYLES.terracotta
                    }`}
                  >
                    {p.icon === 'code' ? (
                      <Code2 className="h-4 w-4" />
                    ) : p.icon === 'book' ? (
                      <BookOpen className="h-4 w-4" />
                    ) : (
                      <FolderKanban className="h-4 w-4" />
                    )}
                  </div>
                  {p.is_archived && (
                    <StatusBadge variant="warning">Archived</StatusBadge>
                  )}
                </div>

                <h3 className="mt-3 text-sm font-semibold text-ink-primary">
                  {p.name}
                </h3>
                <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-ink-secondary">
                  {p.description || 'No description'}
                </p>
              </div>

              <div className="mt-4 flex items-center gap-3 border-t border-border/70 pt-3 text-[11px] text-ink-muted">
                <span>{p.conversations_count} chats</span>
                <span>·</span>
                <span>{p.files_count} files</span>
                <span>·</span>
                <span>{p.artifacts_count} artifacts</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-[1px]">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-surface-elevated shadow-xl">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <h3 className="text-sm font-semibold text-ink-primary">
                Create New Project
              </h3>
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="rounded-lg p-1 text-ink-secondary hover:bg-surface"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-4 p-6">
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Python Learning"
                  className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Description
                </label>
                <input
                  type="text"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Short summary of this project"
                  className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Accent Color
                </label>
                <div className="flex gap-2">
                  {Object.keys(COLOR_STYLES).map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => setNewColor(color)}
                      className={`rounded-lg border px-3 py-1 text-xs capitalize ${
                        newColor === color
                          ? COLOR_STYLES[color]
                          : 'border-border bg-surface text-ink-secondary'
                      }`}
                    >
                      {color}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Project AI Instructions (Optional)
                </label>
                <textarea
                  rows={4}
                  value={newInstructions}
                  onChange={(e) => setNewInstructions(e.target.value)}
                  placeholder="Custom instructions applied to conversations in this project..."
                  className="w-full rounded-xl border border-border bg-canvas p-3 text-xs text-ink-primary focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs text-ink-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
                >
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
