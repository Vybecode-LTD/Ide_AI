/**
 * NotionConnectCard — Settings card to connect / disconnect a Notion workspace.
 *
 * Self-contained: owns its own data fetch + OAuth kickoff so Settings only needs
 * to drop `<NotionConnectCard />` into its list.
 *
 * States it renders:
 *  - server not configured (no NOTION_* env)     → "Not available yet"
 *  - available + configured + not connected      → "Connect Notion" button
 *  - connected                                   → workspace name + Disconnect
 *
 * After the OAuth round-trip the backend redirects to
 * `/settings?notion=connected|error`; we surface that as a toast and clean the
 * query string.
 */
import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import apiClient from '../../lib/apiClient'
import { extractError } from '../../lib/extractError'
import { Card } from '../ui/Card'

interface IntegrationItem {
  id: string | null
  provider: string
  enabled: boolean
  has_token: boolean
  config: { workspace_name?: string } | null
  status?: string
  configured?: boolean
}

export function NotionConnectCard() {
  const [params, setParams] = useSearchParams()
  const [item, setItem] = useState<IntegrationItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data } = await apiClient.get<IntegrationItem[]>('/integrations')
      setItem(data.find((i) => i.provider === 'notion') || null)
    } catch {
      // Non-fatal — the card just won't render its connected state.
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // Surface the post-OAuth redirect result, then strip the query param.
  useEffect(() => {
    const flag = params.get('notion')
    if (!flag) return
    if (flag === 'connected') toast.success('Notion connected')
    else if (flag === 'error') toast.error('Could not connect Notion. Please try again.')
    // 'connect' is an internal hint (from the push button) — no toast.
    params.delete('notion')
    setParams(params, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const connected = !!(item && (item.has_token || item.id))
  const configured = item?.configured !== false // undefined (connected) or true → treat as configured

  const handleConnect = async () => {
    setBusy(true)
    try {
      const { data } = await apiClient.post<{ authorize_url: string }>('/integrations/notion/authorize')
      window.location.href = data.authorize_url
    } catch (err) {
      toast.error(extractError(err, 'Could not start Notion connection'))
      setBusy(false)
    }
  }

  const handleDisconnect = async () => {
    if (!item?.id) return
    setBusy(true)
    try {
      await apiClient.delete(`/integrations/${item.id}`)
      toast.success('Notion disconnected')
      await load()
    } catch (err) {
      toast.error(extractError(err, 'Could not disconnect Notion'))
    } finally {
      setBusy(false)
    }
  }

  if (loading) return null

  const workspace = item?.config?.workspace_name

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
            <span>📝</span> Notion
          </h3>
          <p className="text-xs text-text-muted">
            {connected
              ? `Connected${workspace ? ` to ${workspace}` : ''}. Push any design kit to a Notion page from its Design Kit screen.`
              : 'Connect a Notion workspace to push your design kits into Notion pages.'}
          </p>
        </div>

        <div className="shrink-0">
          {connected ? (
            <button
              onClick={handleDisconnect}
              disabled={busy}
              className="text-xs px-3 py-1.5 rounded-lg border border-border text-text-muted hover:text-white disabled:opacity-50"
            >
              {busy ? '…' : 'Disconnect'}
            </button>
          ) : configured ? (
            <button
              onClick={handleConnect}
              disabled={busy}
              className="text-xs px-3 py-1.5 rounded-lg bg-accent text-black font-medium disabled:opacity-50"
            >
              {busy ? 'Connecting…' : 'Connect Notion'}
            </button>
          ) : (
            <span className="text-xs text-text-muted/70 italic">Not available yet</span>
          )}
        </div>
      </div>
    </Card>
  )
}
