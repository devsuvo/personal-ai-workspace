import { Layers, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { createArtifact, fetchProjects } from '../../services/workspaceService';
import type {
  ArtifactItem,
  ArtifactType,
  ProjectSummary,
} from '../../types/workspace';

interface SaveAsArtifactModalProps {
  initialContent: string;
  conversationId?: string | null;
  onClose: () => void;
  onSaved: (artifact: ArtifactItem) => void;
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

function detectInitialArtifact(raw: string): {
  type: ArtifactType;
  language: string;
  content: string;
} {
  const fence = raw.match(/```(\w+)?\n([\s\S]*?)```/);
  if (fence) {
    const lang = (fence[1] || '').toLowerCase();
    const body = fence[2].trim();
    if (lang === 'html') return { type: 'html', language: 'html', content: body };
    if (lang === 'json') return { type: 'json', language: 'json', content: body };
    if (lang === 'csv') return { type: 'csv', language: 'csv', content: body };
    return { type: 'code', language: lang || 'text', content: body };
  }
  return { type: 'markdown', language: '', content: raw };
}

export function SaveAsArtifactModal({
  initialContent,
  conversationId,
  onClose,
  onSaved,
}: SaveAsArtifactModalProps) {
  const detected = detectInitialArtifact(initialContent);
  const [title, setTitle] = useState('Saved AI Output');
  const [artifactType, setArtifactType] = useState<ArtifactType>(detected.type);
  const [language, setLanguage] = useState(detected.language);
  const [content, setContent] = useState(detected.content);
  const [projectId, setProjectId] = useState('');
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchProjects('', false)
      .then(setProjects)
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await createArtifact({
        title: title.trim(),
        artifact_type: artifactType,
        content,
        language: artifactType === 'code' ? language.trim() || null : null,
        project_id: projectId || null,
        conversation_id: conversationId || null,
      });
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save artifact.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-[1px]">
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-surface-elevated shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-accent" />
            <h2 className="text-sm font-semibold text-ink-primary">
              Save Response as Artifact
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-ink-secondary hover:bg-surface"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="overflow-y-auto p-6 space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs font-medium text-ink-secondary">
                Artifact Title *
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-ink-secondary">
                Type
              </label>
              <select
                value={artifactType}
                onChange={(e) => setArtifactType(e.target.value as ArtifactType)}
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
              >
                {ARTIFACT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-secondary">
                Project (Optional)
              </label>
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
              >
                <option value="">No project</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {artifactType === 'code' && (
              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Language
                </label>
                <input
                  type="text"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  placeholder="python, typescript, sql..."
                  className="w-full rounded-xl border border-border bg-canvas px-3 py-2 font-mono text-xs text-ink-primary focus:outline-none"
                />
              </div>
            )}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-ink-secondary">
              Content (editable before saving)
            </label>
            <textarea
              rows={10}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full rounded-xl border border-border bg-canvas p-3 font-mono text-xs leading-relaxed text-ink-primary focus:outline-none"
            />
          </div>

          {error && (
            <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-300">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 border-t border-border pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-border bg-surface px-4 py-2 text-xs text-ink-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover disabled:opacity-60"
            >
              {saving ? 'Saving...' : 'Save Artifact'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
