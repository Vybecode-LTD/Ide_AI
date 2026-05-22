/**
 * TranscriptExportMenu — Dropdown menu for exporting discovery transcripts.
 * Supports clipboard copy, PDF, TXT, and MD downloads.
 * @module components/discovery/TranscriptExportMenu
 */
import { useState, useRef, useEffect } from 'react'
import apiClient from '../../lib/apiClient'
import { downloadBlob } from '../../lib/exportUtils'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface TranscriptExportMenuProps {
  sessionId: string
  projectName?: string
  messages?: Message[]
}

const FORMATS = [
  { key: 'clipboard', label: 'Copy to Clipboard', icon: '📋' },
  { key: 'md', label: 'Download Markdown', icon: '📝' },
  { key: 'txt', label: 'Download Text', icon: '📄' },
  { key: 'pdf', label: 'Download PDF', icon: '📕' },
] as const

type FormatKey = (typeof FORMATS)[number]['key']

export function TranscriptExportMenu({ sessionId, projectName, messages }: TranscriptExportMenuProps) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState<FormatKey | null>(null)
  const [copied, setCopied] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close on outside click or Escape key
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    if (open) {
      document.addEventListener('mousedown', handleClick)
      document.addEventListener('keydown', handleKey)
    }
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [open])

  const handleExport = async (format: FormatKey) => {
    setBusy(format)
    try {
      if (format === 'clipboard') {
        let text = ''
        try {
          const { data } = await apiClient.get(
            `/discovery/${sessionId}/transcript?format=md`,
            { responseType: 'text' }
          )
          text = typeof data === 'string' ? data : ''
        } catch {
          // API failed — skip, fall through to local fallback
        }
        // Fallback: format local messages (both user + AI)
        if (!text && messages?.length) {
          text = messages.map((m) => `**${m.role === 'user' ? 'You' : 'AI'}:** ${m.content}`).join('\n\n')
        }
        if (text) {
          await navigator.clipboard.writeText(text)
          setCopied(true)
          setTimeout(() => setCopied(false), 2000)
        }
      } else {
        const response = await apiClient.get(
          `/discovery/${sessionId}/transcript?format=${format}`,
          { responseType: format === 'pdf' ? 'blob' : 'text' }
        )
        const slug = (projectName || 'discovery').toLowerCase().replace(/\s+/g, '-').slice(0, 30)
        const ext = format
        const blob =
          response.data instanceof Blob
            ? response.data
            : new Blob([response.data], { type: 'text/plain' })
        downloadBlob(blob, `${slug}-transcript.${ext}`)
      }
    } catch (err) {
      console.error('Transcript export failed:', err)
    } finally {
      setBusy(null)
      setOpen(false)
    }
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        aria-label="Export transcript"
        aria-expanded={open}
        aria-haspopup="menu"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 min-h-[44px] md:min-h-0 text-xs font-medium rounded-lg bg-white/5 border border-border text-text-muted hover:text-white hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-accent/50 transition-colors"
      >
        <span aria-hidden="true">↗</span>
        <span>{copied ? 'Copied!' : 'Export Transcript'}</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-52 rounded-lg border border-border bg-surface shadow-xl z-50 py-1">
          {FORMATS.map((fmt) => (
            <button
              key={fmt.key}
              onClick={() => handleExport(fmt.key)}
              disabled={busy !== null}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-text-muted hover:text-white hover:bg-white/5 transition-colors disabled:opacity-50"
            >
              <span>{fmt.icon}</span>
              <span>{busy === fmt.key ? 'Exporting...' : fmt.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
