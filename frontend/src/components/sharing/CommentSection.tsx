/**
 * CommentSection — Displays and submits comments on a shared project.
 * Uses the public sharing API (no auth required).
 */
import { useCallback, useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

interface Comment {
  id: string
  author_name: string
  content: string
  created_at: string
}

interface CommentSectionProps {
  shareToken: string
}

export function CommentSection({ shareToken }: CommentSectionProps) {
  const [comments, setComments] = useState<Comment[]>([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchComments = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/sharing/public/${shareToken}/comments`)
      if (resp.ok) {
        const data = await resp.json()
        setComments(data)
      }
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }, [shareToken])

  useEffect(() => {
    fetchComments()
  }, [fetchComments])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const resp = await fetch(`${API_BASE}/sharing/public/${shareToken}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          author_name: name.trim() || 'Anonymous',
          content: content.trim(),
        }),
      })
      if (resp.ok) {
        setContent('')
        setName('')
        await fetchComments()
      } else {
        const data = await resp.json()
        setError(data.detail || 'Failed to post comment.')
      }
    } catch {
      setError('Failed to connect to server.')
    } finally {
      setSubmitting(false)
    }
  }

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })

  return (
    <div>
      <h3 className="text-sm font-semibold text-white mb-4">Comments</h3>

      {/* Comment form */}
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name (optional)"
            maxLength={100}
            className="w-40 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder:text-white/30 focus:outline-none focus:border-accent/40"
          />
        </div>
        <div className="flex gap-2">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Leave a comment..."
            maxLength={2000}
            rows={2}
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-accent/40 resize-none"
          />
          <button
            type="submit"
            disabled={!content.trim() || submitting}
            className="self-end px-4 py-2 bg-accent text-black font-medium text-xs rounded-lg hover:bg-accent/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? '...' : 'Post'}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
      </form>

      {/* Comment list */}
      {loading ? (
        <p className="text-xs text-white/30">Loading comments...</p>
      ) : comments.length === 0 ? (
        <p className="text-xs text-white/30">No comments yet. Be the first!</p>
      ) : (
        <div className="space-y-3">
          {comments.map((c) => (
            <div
              key={c.id}
              className="bg-white/[0.03] border border-white/5 rounded-lg px-4 py-3"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-white">
                  {c.author_name}
                </span>
                <span className="text-[10px] text-white/30">
                  {formatDate(c.created_at)}
                </span>
              </div>
              <p className="text-sm text-white/70 leading-relaxed">{c.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
