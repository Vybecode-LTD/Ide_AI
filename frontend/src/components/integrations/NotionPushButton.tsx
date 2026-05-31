/**
 * NotionPushButton — header action that pushes a project's design kit to Notion.
 *
 * Self-contained: owns its own modal (inline, matching the ShareDialog pattern —
 * the codebase has no shared Modal component) + API calls, so host pages
 * (DesignKit) only need to drop `<NotionPushButton projectId={id} />` into their
 * actions row.
 *
 * Flow: click → fetch the integration's accessible Notion pages → user picks a
 * parent page → POST the push → toast a link to the new page. If Notion isn't
 * connected the page-list call 404s and we point the user at Settings.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import apiClient from '../../lib/apiClient'
import { extractError } from '../../lib/extractError'

interface NotionPage {
  id: string
  title: string
}

export function NotionPushButton({ projectId }: { projectId?: string }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [loadingPages, setLoadingPages] = useState(false)
  const [pages, setPages] = useState<NotionPage[]>([])
  const [selected, setSelected] = useState<string>('')
  const [pushing, setPushing] = useState(false)

  const openPicker = async () => {
    if (!projectId) return
    setOpen(true)
    setLoadingPages(true)
    try {
      const { data } = await apiClient.get<{ pages: NotionPage[] }>('/integrations/notion/pages')
      setPages(data.pages || [])
      if (data.pages?.length) setSelected(data.pages[0].id)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      setOpen(false)
      if (status === 404) {
        toast.error('Connect Notion in Settings first')
        navigate('/settings?notion=connect')
      } else {
        toast.error(extractError(err, 'Could not load your Notion pages'))
      }
    } finally {
      setLoadingPages(false)
    }
  }

  const handlePush = async () => {
    if (!projectId || !selected) return
    setPushing(true)
    try {
      const { data } = await apiClient.post<{ url?: string }>(
        `/integrations/notion/push/${projectId}`,
        { parent_page_id: selected },
      )
      setOpen(false)
      if (data.url) {
        const url = data.url
        toast.success(
          (t) => (
            <span>
              Pushed to Notion.{' '}
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent underline"
                onClick={() => toast.dismiss(t.id)}
              >
                Open page
              </a>
            </span>
          ),
          { duration: 8000 },
        )
      } else {
        toast.success('Pushed to Notion')
      }
    } catch (err) {
      toast.error(extractError(err, 'Failed to push to Notion'))
    } finally {
      setPushing(false)
    }
  }

  return (
    <>
      <button
        onClick={openPicker}
        className="text-xs font-medium text-text-muted hover:text-white border border-border hover:border-accent/40 px-3 py-2 rounded-lg transition-colors"
      >
        Push to Notion
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            onClick={() => setOpen(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            <div className="w-full max-w-md pointer-events-auto bg-surface border border-border rounded-2xl shadow-2xl">
              <div className="flex items-center justify-between p-4 border-b border-border">
                <h3 className="text-sm font-semibold text-white">Push to Notion</h3>
                <button
                  onClick={() => setOpen(false)}
                  className="text-text-muted hover:text-white text-lg leading-none"
                >
                  ×
                </button>
              </div>
              <div className="p-4">
                {loadingPages ? (
                  <div className="py-6 text-center text-sm text-text-muted animate-pulse">
                    Loading your Notion pages…
                  </div>
                ) : pages.length === 0 ? (
                  <div className="py-2 text-sm text-text-muted">
                    No pages found. In Notion, open the page you want to use, click{' '}
                    <span className="text-white">•••</span> →
                    <span className="text-white"> Connections</span>, and add the Ide/AI integration
                    so it can write there.
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs text-text-muted mb-1.5">Parent page</label>
                      <select
                        value={selected}
                        onChange={(e) => setSelected(e.target.value)}
                        className="w-full rounded-lg bg-white/5 border border-border px-3 py-2 text-sm text-white focus:border-accent outline-none"
                      >
                        {pages.map((p) => (
                          <option key={p.id} value={p.id} className="bg-[#15151c]">
                            {p.title || 'Untitled'}
                          </option>
                        ))}
                      </select>
                      <p className="text-[11px] text-text-muted mt-1.5">
                        A new sub-page with your full design kit will be created here.
                      </p>
                    </div>
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setOpen(false)}
                        className="text-xs px-3 py-1.5 rounded-lg border border-border text-text-muted hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handlePush}
                        disabled={pushing || !selected}
                        className="text-xs px-3 py-1.5 rounded-lg bg-accent text-black font-medium disabled:opacity-50"
                      >
                        {pushing ? 'Pushing…' : 'Push'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  )
}
