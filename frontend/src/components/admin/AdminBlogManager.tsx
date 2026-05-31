/**
 * AdminBlogManager — Blog CMS inside the Admin dashboard.
 * List view (incl. drafts) + an inline create/edit form with live Markdown
 * preview, publish toggle, and delete. Admin-only routes enforce auth server-side.
 * @module components/admin/AdminBlogManager
 */
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from '../ui/Button'
import {
  adminCreatePost,
  adminDeletePost,
  adminGetPost,
  adminListPosts,
  adminUpdatePost,
  slugify,
} from '../../lib/blogApi'
import type { BlogPostSummary } from '../../types/blog'

const inputClass =
  'w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent'

interface FormState {
  title: string
  slug: string
  excerpt: string
  coverImageUrl: string
  tags: string
  authorName: string
  body: string
  published: boolean
}

const EMPTY_FORM: FormState = {
  title: '',
  slug: '',
  excerpt: '',
  coverImageUrl: '',
  tags: '',
  authorName: '',
  body: '',
  published: false,
}

function errMessage(e: unknown): string {
  const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return detail || 'Something went wrong'
}

export function AdminBlogManager() {
  const [posts, setPosts] = useState<BlogPostSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<'list' | 'edit'>('list')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [slugTouched, setSlugTouched] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showPreview, setShowPreview] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const data = await adminListPosts()
      setPosts(data.items)
    } catch (e) {
      toast.error(errMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openNew = () => {
    setForm(EMPTY_FORM)
    setEditingId(null)
    setSlugTouched(false)
    setShowPreview(false)
    setView('edit')
  }

  const openEdit = async (id: string) => {
    try {
      const post = await adminGetPost(id)
      setForm({
        title: post.title,
        slug: post.slug,
        excerpt: post.excerpt ?? '',
        coverImageUrl: post.cover_image_url ?? '',
        tags: (post.tags ?? []).join(', '),
        authorName: post.author_name ?? '',
        body: post.body,
        published: post.published,
      })
      setEditingId(id)
      setSlugTouched(true)
      setShowPreview(false)
      setView('edit')
    } catch (e) {
      toast.error(errMessage(e))
    }
  }

  const setTitle = (title: string) => {
    setForm((f) => ({ ...f, title, slug: slugTouched ? f.slug : slugify(title) }))
  }

  const save = async () => {
    if (!form.title.trim() || !form.body.trim()) {
      toast.error('Title and body are required')
      return
    }
    setSaving(true)
    const payload = {
      title: form.title.trim(),
      slug: slugify(form.slug || form.title),
      excerpt: form.excerpt.trim() || null,
      cover_image_url: form.coverImageUrl.trim() || null,
      tags: form.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
      author_name: form.authorName.trim() || null,
      body: form.body,
      published: form.published,
    }
    try {
      if (editingId) {
        await adminUpdatePost(editingId, payload)
        toast.success('Post updated')
      } else {
        await adminCreatePost(payload)
        toast.success('Post created')
      }
      setView('list')
      await load()
    } catch (e) {
      toast.error(errMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const del = async (id: string, title: string) => {
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return
    try {
      await adminDeletePost(id)
      toast.success('Post deleted')
      await load()
    } catch (e) {
      toast.error(errMessage(e))
    }
  }

  // ── Editor view ───────────────────────────────────────────────────
  if (view === 'edit') {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">
            {editingId ? 'Edit post' : 'New post'}
          </h3>
          <button
            onClick={() => setView('list')}
            className="text-xs text-text-muted hover:text-white transition-colors"
          >
            ← Back to list
          </button>
        </div>

        <div className="grid sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2">
            <label className="text-xs text-text-muted mb-1 block">Title *</label>
            <input
              className={inputClass}
              value={form.title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="How to go from idea to design kit in 20 minutes"
            />
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1 block">Slug</label>
            <input
              className={inputClass}
              value={form.slug}
              onChange={(e) => {
                setSlugTouched(true)
                setForm((f) => ({ ...f, slug: e.target.value }))
              }}
              placeholder="idea-to-design-kit"
            />
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1 block">Author</label>
            <input
              className={inputClass}
              value={form.authorName}
              onChange={(e) => setForm((f) => ({ ...f, authorName: e.target.value }))}
              placeholder="Ide/AI Team"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs text-text-muted mb-1 block">
              Excerpt (SEO description / card teaser)
            </label>
            <input
              className={inputClass}
              value={form.excerpt}
              onChange={(e) => setForm((f) => ({ ...f, excerpt: e.target.value }))}
              maxLength={500}
              placeholder="A short, search-friendly summary of the post."
            />
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1 block">Cover image URL</label>
            <input
              className={inputClass}
              value={form.coverImageUrl}
              onChange={(e) => setForm((f) => ({ ...f, coverImageUrl: e.target.value }))}
              placeholder="https://…/cover.png"
            />
          </div>
          <div>
            <label className="text-xs text-text-muted mb-1 block">Tags (comma-separated)</label>
            <input
              className={inputClass}
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
              placeholder="tutorial, tips"
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-text-muted">Body (Markdown) *</label>
            <button
              onClick={() => setShowPreview((p) => !p)}
              className="text-xs text-accent hover:text-accent/80 transition-colors"
            >
              {showPreview ? 'Edit' : 'Preview'}
            </button>
          </div>
          {showPreview ? (
            <div className="blog-content min-h-[16rem] rounded-lg border border-border bg-background p-4">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {form.body || '_Nothing to preview yet._'}
              </ReactMarkdown>
            </div>
          ) : (
            <textarea
              className={`${inputClass} min-h-[16rem] font-mono leading-relaxed`}
              value={form.body}
              onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
              placeholder={'## Section heading\n\nWrite your post in Markdown… (the title above is the page H1, so start body headings at ##)'}
            />
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <button
              type="button"
              onClick={() => setForm((f) => ({ ...f, published: !f.published }))}
              className={`relative w-10 h-5 rounded-full transition-colors ${
                form.published ? 'bg-accent' : 'bg-border'
              }`}
            >
              <span
                className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                  form.published ? 'translate-x-5' : 'translate-x-0.5'
                }`}
              />
            </button>
            <span className="text-sm text-white">
              {form.published ? 'Published' : 'Draft'}
            </span>
          </label>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => setView('list')}>
              Cancel
            </Button>
            <Button size="sm" onClick={save} disabled={saving}>
              {saving ? 'Saving…' : editingId ? 'Save changes' : 'Create post'}
            </Button>
          </div>
        </div>
      </div>
    )
  }

  // ── List view ─────────────────────────────────────────────────────
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-text-muted">{posts.length} post{posts.length === 1 ? '' : 's'}</p>
        <Button size="sm" onClick={openNew}>
          + New post
        </Button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : posts.length === 0 ? (
        <p className="text-sm text-text-muted py-12 text-center">
          No posts yet. Create your first one.
        </p>
      ) : (
        <div className="space-y-2">
          {posts.map((post) => (
            <div
              key={post.id}
              className="flex items-center gap-3 rounded-lg border border-border bg-white/[0.02] px-4 py-3"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white truncate">{post.title}</span>
                  <span
                    className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded-full shrink-0 ${
                      post.published
                        ? 'bg-green-500/15 text-green-400'
                        : 'bg-white/10 text-text-muted'
                    }`}
                  >
                    {post.published ? 'Published' : 'Draft'}
                  </span>
                </div>
                <p className="text-xs text-text-muted/70 truncate">
                  /{post.slug} · {post.view_count} view{post.view_count === 1 ? '' : 's'}
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                {post.published && (
                  <a
                    href={`/blog/${post.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-text-muted hover:text-white px-2 py-1 transition-colors"
                  >
                    View
                  </a>
                )}
                <button
                  onClick={() => openEdit(post.id)}
                  className="text-xs text-accent hover:text-accent/80 px-2 py-1 transition-colors"
                >
                  Edit
                </button>
                <button
                  onClick={() => del(post.id, post.title)}
                  className="text-xs text-red-400 hover:text-red-300 px-2 py-1 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
