import {
  Check,
  Copy,
  Download,
  Eye,
  FileCode2,
  Layers,
  Pencil,
  Plus,
  Save,
  Search,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import {
  oneDark,
  oneLight,
} from 'react-syntax-highlighter/dist/esm/styles/prism';
import { MarkdownContent } from '../components/chat/MarkdownContent';
import { StatusBadge } from '../components/common/StatusBadge';
import type { ThemeMode } from '../hooks/useTheme';
import {
  createArtifact,
  deleteArtifact,
  duplicateArtifact,
  fetchArtifacts,
  fetchProjects,
  getArtifactExportUrl,
  updateArtifact,
} from '../services/workspaceService';
import type {
  ArtifactItem,
  ArtifactType,
  ProjectSummary,
} from '../types/workspace';

interface ArtifactsPageProps {
  theme: ThemeMode;
}

const ARTIFACT_TYPES: ArtifactType[] = [
  'markdown',
  'document',
  'code',
  'html',
  'json',
  'table',
  'csv',
  'text',
];

export function ArtifactsPage({ theme }: ArtifactsPageProps) {
  const [artifacts, setArtifacts] = useState<ArtifactItem[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [selected, setSelected] = useState<ArtifactItem | null>(null);
  const [mode, setMode] = useState<'preview' | 'edit'>('preview');

  const [title, setTitle] = useState('');
  const [artifactType, setArtifactType] = useState<ArtifactType>('markdown');
  const [language, setLanguage] = useState('');
  const [projectId, setProjectId] = useState('');
  const [content, setContent] = useState('');
  const [copied, setCopied] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    const [arts, projs] = await Promise.all([
      fetchArtifacts({ search, artifactType: typeFilter || undefined }),
      fetchProjects('', false),
    ]);
    setArtifacts(arts);
    setProjects(projs);
  }, [search, typeFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadAll(), 150);
    return () => window.clearTimeout(timer);
  }, [loadAll]);

  const selectArtifact = (item: ArtifactItem) => {
    setSelected(item);
    setTitle(item.title);
    setArtifactType((item.artifact_type as ArtifactType) || 'markdown');
    setLanguage(item.language || '');
    setProjectId(item.project_id || '');
    setContent(item.content);
    setNotice(null);
  };

  const handleCreateNew = async () => {
    const created = await createArtifact({
      title: 'Untitled Artifact',
      artifact_type: 'markdown',
      content: '# New Artifact\n\nStart writing or paste generated output here.',
    });
    await loadAll();
    selectArtifact(created);
    setMode('edit');
  };

  const handleSave = async () => {
    if (!selected) return;
    const updated = await updateArtifact(selected.id, {
      title: title.trim() || 'Untitled Artifact',
      artifact_type: artifactType,
      content,
      language: artifactType === 'code' ? language.trim() || null : null,
      project_id: projectId || null,
    });
    selectArtifact(updated);
    await loadAll();
    setNotice('Artifact saved locally.');
    window.setTimeout(() => setNotice(null), 2500);
  };

  const handleDuplicate = async () => {
    if (!selected) return;
    const copy = await duplicateArtifact(selected.id);
    await loadAll();
    selectArtifact(copy);
  };

  const handleDelete = async () => {
    if (!selected) return;
    await deleteArtifact(selected.id);
    setSelected(null);
    await loadAll();
  };

  const handleCopyContent = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col px-4 py-6 sm:px-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-ink-primary">Artifacts</h2>
          <p className="mt-0.5 text-xs text-ink-secondary">
            Standalone documents, code, sandboxed HTML previews, JSON, and CSV
            outputs stored locally.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleCreateNew()}
          className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
        >
          <Plus className="h-4 w-4" />
          <span>New Artifact</span>
        </button>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-5 lg:grid-cols-12">
        {/* Left List */}
        <div className="flex flex-col space-y-3 lg:col-span-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-muted" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search artifacts..."
                className="w-full rounded-xl border border-border bg-surface-elevated py-1.5 pl-8 pr-3 text-xs text-ink-primary focus:outline-none"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="rounded-xl border border-border bg-surface-elevated px-2.5 py-1.5 text-xs text-ink-primary focus:outline-none"
            >
              <option value="">All</option>
              {ARTIFACT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto pr-1">
            {artifacts.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border bg-surface-elevated p-6 text-center text-xs text-ink-muted">
                No artifacts saved yet. Create one or save any AI chat response as
                an artifact.
              </div>
            ) : (
              artifacts.map((art) => (
                <button
                  key={art.id}
                  type="button"
                  onClick={() => selectArtifact(art)}
                  className={`w-full rounded-xl border p-3.5 text-left transition-colors ${
                    selected?.id === art.id
                      ? 'border-accent bg-surface-elevated shadow-sm'
                      : 'border-border bg-surface-elevated/60 hover:border-border-strong'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-semibold text-ink-primary">
                      {art.title}
                    </span>
                    <StatusBadge variant="neutral">
                      {art.artifact_type}
                    </StatusBadge>
                  </div>
                  <div className="mt-1 text-[11px] text-ink-muted">
                    Updated {new Date(art.updated_at).toLocaleString()}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Right Editor / Preview */}
        <div className="flex min-h-[460px] flex-col rounded-2xl border border-border bg-surface-elevated lg:col-span-8">
          {!selected ? (
            <div className="m-auto p-8 text-center">
              <Layers className="mx-auto mb-3 h-8 w-8 text-ink-muted" />
              <p className="text-sm font-medium text-ink-primary">
                Select an artifact to preview or edit
              </p>
              <p className="mt-1 text-xs text-ink-secondary">
                HTML artifacts render safely inside a strict sandboxed iframe.
              </p>
            </div>
          ) : (
            <>
              {/* Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setMode('preview')}
                    className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium ${
                      mode === 'preview'
                        ? 'bg-surface text-ink-primary ring-1 ring-border'
                        : 'text-ink-secondary hover:bg-surface'
                    }`}
                  >
                    <Eye className="h-3.5 w-3.5" />
                    <span>Preview</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode('edit')}
                    className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium ${
                      mode === 'edit'
                        ? 'bg-surface text-ink-primary ring-1 ring-border'
                        : 'text-ink-secondary hover:bg-surface'
                    }`}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                    <span>Edit</span>
                  </button>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => void handleCopyContent()}
                    className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-ink-secondary hover:text-ink-primary"
                  >
                    {copied ? (
                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDuplicate()}
                    className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-ink-secondary hover:text-ink-primary"
                  >
                    <FileCode2 className="h-3.5 w-3.5" />
                    <span>Duplicate</span>
                  </button>
                  <a
                    href={getArtifactExportUrl(selected.id)}
                    className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-xs text-ink-secondary hover:text-ink-primary"
                  >
                    <Download className="h-3.5 w-3.5" />
                    <span>Export</span>
                  </a>
                  <button
                    type="button"
                    onClick={() => void handleSave()}
                    className="inline-flex items-center gap-1 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-hover"
                  >
                    <Save className="h-3.5 w-3.5" />
                    <span>Save</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete()}
                    aria-label="Delete artifact"
                    className="rounded-lg border border-border bg-surface p-1.5 text-rose-600 hover:bg-rose-500/10"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {/* Metadata bar */}
              <div className="grid grid-cols-1 gap-2 border-b border-border/70 bg-canvas/40 px-4 py-2.5 sm:grid-cols-4">
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="rounded-lg border border-border bg-surface-elevated px-2.5 py-1 text-xs font-medium text-ink-primary sm:col-span-2 focus:outline-none"
                />
                <select
                  value={artifactType}
                  onChange={(e) => setArtifactType(e.target.value as ArtifactType)}
                  className="rounded-lg border border-border bg-surface-elevated px-2 py-1 text-xs text-ink-primary focus:outline-none"
                >
                  {ARTIFACT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t.toUpperCase()}
                    </option>
                  ))}
                </select>
                <select
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  className="rounded-lg border border-border bg-surface-elevated px-2 py-1 text-xs text-ink-primary focus:outline-none"
                >
                  <option value="">No project</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              {notice && (
                <div className="bg-emerald-500/10 px-4 py-1.5 text-xs text-emerald-700 dark:text-emerald-300">
                  {notice}
                </div>
              )}

              {/* Content area */}
              <div className="flex-1 overflow-y-auto p-5">
                {mode === 'edit' ? (
                  <div className="flex h-full flex-col space-y-2">
                    {artifactType === 'code' && (
                      <input
                        type="text"
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                        placeholder="Language (python, typescript, sql...)"
                        className="max-w-xs rounded-lg border border-border bg-canvas px-2.5 py-1 font-mono text-xs text-ink-primary focus:outline-none"
                      />
                    )}
                    <textarea
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      className="min-h-[340px] w-full flex-1 resize-none rounded-xl border border-border bg-canvas p-3 font-mono text-xs leading-relaxed text-ink-primary focus:outline-none"
                    />
                  </div>
                ) : artifactType === 'html' ? (
                  <div className="space-y-2">
                    <p className="text-[11px] text-ink-muted">
                      Sandboxed HTML preview (scripts and parent-window access
                      disabled for safety).
                    </p>
                    <iframe
                      title={title}
                      sandbox=""
                      srcDoc={content}
                      className="h-[380px] w-full rounded-xl border border-border bg-white"
                    />
                  </div>
                ) : artifactType === 'code' || artifactType === 'json' ? (
                  <SyntaxHighlighter
                    language={
                      artifactType === 'json' ? 'json' : language || 'text'
                    }
                    style={theme === 'dark' ? oneDark : oneLight}
                    customStyle={{
                      margin: 0,
                      borderRadius: '0.75rem',
                      fontSize: '0.8125rem',
                    }}
                  >
                    {content}
                  </SyntaxHighlighter>
                ) : artifactType === 'markdown' ||
                  artifactType === 'document' ||
                  artifactType === 'table' ? (
                  <MarkdownContent content={content} theme={theme} />
                ) : (
                  <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-ink-primary">
                    {content}
                  </pre>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
