/**
 * Inbox — Idea capture page. Quick-add ideas manually or receive via email.
 * Items can be promoted to full projects.
 * @module pages/Inbox
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import apiClient from '../lib/apiClient'
import { extractError, getEntitlementDetail, type EntitlementDetail } from '../lib/extractError'
import { UpgradeModal } from '../components/ui/UpgradeModal'
import { useAuthStore } from '../stores/authStore'
import { useTutorialStore } from '../stores/tutorialStore'

interface InboxItem {
  id: string
  subject: string
  body: string | null
  source: string
  sender_email: string | null
  project_id: string | null
  created_at: string
}

export function Inbox() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [items, setItems] = useState<InboxItem[]>([])
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')

  // Quick-add form
  const [showForm, setShowForm] = useState(false)
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [upgradeDetail, setUpgradeDetail] = useState<EntitlementDetail | null>(null)
  const showTip = useTutorialStore(s => !s.dismissedWhispers.includes('inbox-how-to'))
  const dismissTip = useTutorialStore(s => s.dismissWhisper)

  useEffect(() => {
    fetchItems()
  }, [])

  const fetchItems = async () => {
    try {
      const { data } = await apiClient.get('/inbox')
      setItems(data)
    } catch {
      setError('Failed to load inbox.')
    } finally {
      setLoading(false)
    }
  }

  const handleAdd = async () => {
    if (!subject.trim()) return
    setSubmitting(true)
    setError('')
    try {
      const { data } = await apiClient.post('/inbox', {
        subject: subject.trim(),
        body: body.trim() || null,
      })
      setItems(prev => [data, ...prev])
      setSubject('')
      setBody('')
      setShowForm(false)
    } catch (err: unknown) {
      setError(extractError(err, 'Failed to add idea.'))
    } finally {
      setSubmitting(false)
    }
  }

  const handlePromote = async (item: InboxItem) => {
    try {
      const { data } = await apiClient.post(`/inbox/${item.id}/promote`, { name: item.subject })
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, project_id: data.project_id } : i))
      navigate(`/discovery/${data.project_id}`)
    } catch (err: unknown) {
      const ent = getEntitlementDetail(err)
      if (ent) setUpgradeDetail(ent)
      else setError(extractError(err, 'Failed to create project.'))
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await apiClient.delete(`/inbox/${id}`)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch (err: unknown) {
      setError(extractError(err, 'Failed to delete.'))
    }
  }

  const unpromoted = items.filter(i => !i.project_id)
  const promoted = items.filter(i => i.project_id)

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="ml-0 md:ml-[232px] pb-14 md:pb-0 flex-1 flex flex-col h-screen">
        <TopBar title="Idea Inbox" subtitle="Capture ideas, promote them to projects" />

        <div className="flex-1 p-4 md:p-6 overflow-y-auto pb-20 md:pb-6">
          <div className="max-w-2xl mx-auto space-y-4">
            {error && (
              <div className="text-red-400 text-xs bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            {/* Inbox email address */}
            {user?.inbox_email && (
              <Card>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-text-muted mb-1">Email your ideas to:</p>
                    <p className="text-sm text-accent font-mono">{user.inbox_email}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      navigator.clipboard.writeText(user.inbox_email!)
                      setCopied(true)
                      setTimeout(() => setCopied(false), 2000)
                    }}
                  >
                    {copied ? 'Copied!' : 'Copy'}
                  </Button>
                </div>
              </Card>
            )}

            {/* How-to tip — dismissable */}
            <AnimatePresence>
              {showTip && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  <Card>
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-2">
                        <h3 className="text-sm font-semibold text-white flex items-center gap-1.5">
                          <span className="text-accent">How it works</span>
                        </h3>
                        <ul className="text-xs text-text-muted space-y-1.5">
                          <li className="flex items-start gap-2">
                            <span className="text-accent mt-0.5 shrink-0">1.</span>
                            <span>Send or forward an email to your unique inbox address above.</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-accent mt-0.5 shrink-0">2.</span>
                            <span>The <strong className="text-white/80">subject line</strong> becomes the idea title. The <strong className="text-white/80">email body</strong> is captured as additional details.</span>
                          </li>
                          <li className="flex items-start gap-2">
                            <span className="text-accent mt-0.5 shrink-0">3.</span>
                            <span>Only the subject is required — body is optional. Keep subjects short and descriptive.</span>
                          </li>
                        </ul>
                        <p className="text-[10px] text-text-muted/60">You can also capture ideas manually with the button below.</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => dismissTip('inbox-how-to')}
                        className="text-text-muted hover:text-white transition-colors p-1 shrink-0"
                        title="Dismiss"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Quick-add button / form */}
            <AnimatePresence mode="wait">
              {!showForm ? (
                <motion.div key="btn" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <Button onClick={() => setShowForm(true)} className="w-full">
                    + Capture New Idea
                  </Button>
                </motion.div>
              ) : (
                <motion.div key="form" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                  <Card glow>
                    <h3 className="text-sm font-semibold text-white mb-3">Quick Capture</h3>
                    <input
                      type="text"
                      value={subject}
                      onChange={e => setSubject(e.target.value)}
                      placeholder="What's the idea?"
                      autoFocus
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors mb-3"
                    />
                    <textarea
                      value={body}
                      onChange={e => setBody(e.target.value)}
                      placeholder="Any details? (optional)"
                      rows={3}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors resize-none mb-3"
                    />
                    <div className="flex items-center gap-2">
                      <Button size="sm" onClick={handleAdd} disabled={submitting || !subject.trim()}>
                        {submitting ? 'Adding...' : 'Add to Inbox'}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => { setShowForm(false); setSubject(''); setBody('') }}>
                        Cancel
                      </Button>
                    </div>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Unpromoted items */}
            {loading ? (
              <div className="text-center py-12 text-text-muted text-sm animate-pulse">Loading inbox...</div>
            ) : unpromoted.length === 0 && promoted.length === 0 ? (
              <div className="text-center py-16">
                <div className="text-3xl mb-3">📥</div>
                <p className="text-text-muted text-sm">Your inbox is empty.</p>
                <p className="text-text-muted text-xs mt-1">Capture quick ideas here and promote them to full projects when ready.</p>
              </div>
            ) : (
              <>
                {unpromoted.length > 0 && (
                  <div className="space-y-2">
                    <h3 className="text-xs font-medium text-text-muted uppercase tracking-wider">
                      Ideas ({unpromoted.length})
                    </h3>
                    <AnimatePresence>
                      {unpromoted.map(item => (
                        <motion.div
                          key={item.id}
                          layout
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                        >
                          <Card>
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="text-xs px-1.5 py-0.5 rounded bg-accent/10 text-accent capitalize">
                                    {item.source}
                                  </span>
                                  <span className="text-[10px] text-text-muted">
                                    {new Date(item.created_at).toLocaleDateString()}
                                  </span>
                                </div>
                                <h4 className="text-sm font-medium text-white truncate">{item.subject}</h4>
                                {item.body && (
                                  <p className="text-xs text-text-muted mt-1 line-clamp-2">{item.body}</p>
                                )}
                                {item.sender_email && (
                                  <p className="text-[10px] text-text-muted mt-1">From: {item.sender_email}</p>
                                )}
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0">
                                <Button size="sm" onClick={() => handlePromote(item)}>
                                  Start Project
                                </Button>
                                <button
                                  type="button"
                                  onClick={() => handleDelete(item.id)}
                                  className="text-text-muted hover:text-red-400 transition-colors p-1"
                                  title="Delete"
                                >
                                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                          </Card>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                )}

                {promoted.length > 0 && (
                  <div className="space-y-2 mt-6">
                    <h3 className="text-xs font-medium text-text-muted uppercase tracking-wider">
                      Promoted ({promoted.length})
                    </h3>
                    {promoted.map(item => (
                      <Card key={item.id}>
                        <div className="flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <h4 className="text-sm text-text-muted truncate line-through">{item.subject}</h4>
                            <span className="text-[10px] text-green-400">Promoted to project</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleDelete(item.id)}
                            className="text-text-muted hover:text-red-400 transition-colors p-1"
                            title="Remove from inbox"
                          >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      <UpgradeModal detail={upgradeDetail} onClose={() => setUpgradeDetail(null)} />
    </div>
  )
}
