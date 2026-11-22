import {
  ArrowRight,
  BookMarked,
  Pencil,
  Plus,
  Search,
  Star,
  Trash2,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  createPromptTemplate,
  deletePromptTemplate,
  fetchPrompts,
  updatePromptTemplate,
  type PromptTemplate,
} from '../services/productivityService';

interface PromptsPageProps {
  onUseInChat: (promptContent: string) => void;
}

const DEFAULT_CATEGORIES = [
  'General',
  'Coding',
  'Writing',
  'Research',
  'Business',
  'Learning',
];

export function PromptsPage({ onUseInChat }: PromptsPageProps) {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  const [editing, setEditing] = useState<PromptTemplate | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('General');
  const [description, setDescription] = useState('');
  const [content, setContent] = useState('');
  const [isFavorite, setIsFavorite] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetchPrompts({
        search,
        category: categoryFilter || undefined,
        favoritesOnly,
      });
      setPrompts(res.prompts);
      setCategories(res.categories);
    } catch {
      // handled gracefully
    }
  }, [search, categoryFilter, favoritesOnly]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 150);
    return () => window.clearTimeout(timer);
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setTitle('');
    setCategory('General');
    setDescription('');
    setContent('');
    setIsFavorite(false);
    setShowModal(true);
  };

  const openEdit = (p: PromptTemplate) => {
    setEditing(p);
    setTitle(p.title);
    setCategory(p.category);
    setDescription(p.description);
    setContent(p.content);
    setIsFavorite(p.is_favorite);
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) return;
    if (editing) {
      await updatePromptTemplate(editing.id, {
        title: title.trim(),
        category: category.trim() || 'General',
        description: description.trim(),
        content: content.trim(),
        is_favorite: isFavorite,
      });
    } else {
      await createPromptTemplate({
        title: title.trim(),
        category: category.trim() || 'General',
        description: description.trim(),
        content: content.trim(),
        is_favorite: isFavorite,
      });
    }
    setShowModal(false);
    await load();
  };

  const handleToggleFavorite = async (p: PromptTemplate) => {
    await updatePromptTemplate(p.id, { is_favorite: !p.is_favorite });
    await load();
  };

  const handleDelete = async (id: string) => {
    await deletePromptTemplate(id);
    await load();
  };

  const allCategories = Array.from(
    new Set([...DEFAULT_CATEGORIES, ...categories])
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-ink-primary">
            Prompt Library
          </h2>
          <p className="mt-1 text-sm text-ink-secondary">
            Save reusable prompts, organize by category, favorite your top
            templates, and insert them directly into chat.
          </p>
        </div>

        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center gap-2 self-start rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
        >
          <Plus className="h-4 w-4" />
          <span>New Prompt</span>
        </button>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1 max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search prompt library..."
            className="w-full rounded-xl border border-border bg-surface-elevated py-2 pl-9 pr-3 text-xs text-ink-primary focus:outline-none"
          />
        </div>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-xl border border-border bg-surface-elevated px-3 py-2 text-xs text-ink-primary focus:outline-none"
        >
          <option value="">All Categories</option>
          {allCategories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <label className="inline-flex items-center gap-2 text-xs text-ink-secondary">
          <input
            type="checkbox"
            checked={favoritesOnly}
            onChange={(e) => setFavoritesOnly(e.target.checked)}
            className="h-3.5 w-3.5 accent-accent"
          />
          <span>Favorites only</span>
        </label>
      </div>

      {prompts.length === 0 ? (
        <div className="rounded-2xl border border-border bg-surface-elevated p-10 text-center">
          <BookMarked className="mx-auto mb-3 h-8 w-8 text-accent" />
          <h3 className="text-base font-semibold text-ink-primary">
            No saved prompts yet
          </h3>
          <p className="mx-auto mt-1.5 max-w-md text-xs text-ink-secondary">
            Save your best prompts once and reuse them across any provider or
            conversation with one click.
          </p>
          <button
            type="button"
            onClick={openCreate}
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
          >
            <Plus className="h-4 w-4" />
            <span>Create First Prompt</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {prompts.map((p) => (
            <div
              key={p.id}
              className="flex flex-col justify-between rounded-2xl border border-border bg-surface-elevated p-5"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink-primary">
                      {p.title}
                    </h3>
                    {p.description && (
                      <p className="mt-0.5 text-xs text-ink-secondary">
                        {p.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <StatusBadge variant="neutral">{p.category}</StatusBadge>
                    <button
                      type="button"
                      onClick={() => void handleToggleFavorite(p)}
                      aria-label="Toggle favorite"
                      className={`rounded-lg p-1 ${
                        p.is_favorite
                          ? 'text-amber-500'
                          : 'text-ink-muted hover:text-ink-primary'
                      }`}
                    >
                      <Star
                        className={`h-4 w-4 ${p.is_favorite ? 'fill-current' : ''}`}
                      />
                    </button>
                  </div>
                </div>

                <pre className="mt-3 line-clamp-4 whitespace-pre-wrap rounded-xl border border-border/70 bg-canvas/60 p-3 font-mono text-[11px] leading-relaxed text-ink-secondary">
                  {p.content}
                </pre>
              </div>

              <div className="mt-4 flex items-center justify-between gap-2 border-t border-border/70 pt-3">
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => openEdit(p)}
                    className="rounded-lg border border-border bg-surface p-1.5 text-ink-secondary hover:text-ink-primary"
                    title="Edit"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete(p.id)}
                    className="rounded-lg border border-border bg-surface p-1.5 text-rose-600 hover:bg-rose-500/10"
                    title="Delete"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => onUseInChat(p.content)}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-accent px-3.5 py-1.5 text-xs font-medium text-white hover:bg-accent-hover"
                >
                  <span>Use in Chat</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-[1px]">
          <div className="w-full max-w-xl rounded-2xl border border-border bg-surface-elevated shadow-xl">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <h3 className="text-sm font-semibold text-ink-primary">
                {editing ? 'Edit Prompt' : 'New Prompt Template'}
              </h3>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="rounded-lg p-1 text-ink-secondary hover:bg-surface"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-4 p-6">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-ink-secondary">
                    Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Architecture Review"
                    className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-ink-secondary">
                    Category
                  </label>
                  <input
                    type="text"
                    list="prompt-categories"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-sm text-ink-primary focus:outline-none"
                  />
                  <datalist id="prompt-categories">
                    {allCategories.map((c) => (
                      <option key={c} value={c} />
                    ))}
                  </datalist>
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Description (Optional)
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-ink-secondary">
                  Prompt Content *
                </label>
                <textarea
                  rows={6}
                  required
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Write your reusable prompt template..."
                  className="w-full rounded-xl border border-border bg-canvas p-3 font-mono text-xs text-ink-primary focus:outline-none"
                />
              </div>

              <label className="inline-flex items-center gap-2 text-xs text-ink-primary">
                <input
                  type="checkbox"
                  checked={isFavorite}
                  onChange={(e) => setIsFavorite(e.target.checked)}
                  className="h-4 w-4 accent-accent"
                />
                <span>Mark as favorite</span>
              </label>

              <div className="flex justify-end gap-2 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-xs text-ink-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-accent px-4 py-2 text-xs font-medium text-white hover:bg-accent-hover"
                >
                  Save Prompt
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
