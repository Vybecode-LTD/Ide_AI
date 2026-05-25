/**
 * Discovery — SSE-powered AI conversation with live design sheet extraction.
 * @module pages/Discovery
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { ChatThread } from '../components/discovery/ChatThread'
import { StagesStepper } from '../components/discovery/StagesStepper'
import { QuickChips } from '../components/discovery/QuickChips'
import { TranscriptExportMenu } from '../components/discovery/TranscriptExportMenu'
import { DesignSheetPanel } from '../components/framework/DesignSheetPanel'
import { ProgressPanel } from '../components/discovery/ProgressPanel'
import { ActivePartnerBadge } from '../components/partner/ActivePartnerBadge'
import { PartnerSelector } from '../components/partner/PartnerSelector'
import { VoiceMicButton } from '../components/voice/VoiceMicButton'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { StageInterlude, PulseBeacon, Whisper } from '../components/tutorial'
import { useSSE } from '../hooks/useSSE'
import type { FieldSummary, FieldUpdate } from '../hooks/useSSE'
import { usePathwayStore } from '../stores/pathwayStore'
import apiClient from '../lib/apiClient'
import toast from 'react-hot-toast'
import { extractError } from '../lib/extractError'
import type { PartnerStyleMeta } from '../types/project'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface SheetData {
  problem?: string
  audience?: string
  mvp?: string
  features?: Array<{ name: string; description?: string; priority?: string }>
  tone?: string
  platform?: string
  tech_constraints?: string
  success_metric?: string
  confidence_score: number
  fields_data?: Record<string, unknown>
}

/** Initial chips shown before first AI response */
const INITIAL_CHIPS: string[] = []

const AUTO_SAVE_INTERVAL_MS = 30_000

export function Discovery() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { active: activePathway, fetchPathways, setActiveByProject } = usePathwayStore()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const [stage, setStage] = useState('greeting')
  const [chips, setChips] = useState<string[]>(INITIAL_CHIPS)
  const [sheet, setSheet] = useState<SheetData>({ confidence_score: 0 })
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [showSheet, setShowSheet] = useState(false)
  const [partnerStyle, setPartnerStyle] = useState('strategist')
  const [partnerMeta, setPartnerMeta] = useState<PartnerStyleMeta | null>(null)
  const [allPartners, setAllPartners] = useState<PartnerStyleMeta[]>([])
  const [showPartnerPicker, setShowPartnerPicker] = useState(false)

  // ── v2 flow state ─────────────────────────────────────────────
  // `flowVersion` resolves from the project record on mount. Until then we
  // assume v1 so the legacy sheet panel renders (matches CLAUDE.md rule:
  // existing rows backfilled to v1 in migration 029).
  const [flowVersion, setFlowVersion] = useState<'v1' | 'v2'>('v1')
  const [fieldSummary, setFieldSummary] = useState<FieldSummary | null>(null)
  const [recentUpdates, setRecentUpdates] = useState<FieldUpdate[]>([])

  // Auto-save refs
  const autoSaveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const prevStageRef = useRef(stage)

  const { send, abort, isStreaming } = useSSE({
    onToken: (token) => setStreamingContent((prev) => prev + token),
    onDone: (data) => {
      setStreamingContent((prev) => {
        if (prev) {
          setMessages((msgs) => [...msgs, { role: 'assistant', content: prev }])
        }
        return ''
      })
      if (data.stage) setStage(data.stage)
      // Use backend chips (which include smart fallbacks)
      setChips(data.chips?.length ? data.chips : [])
    },
    onSheetUpdate: (sheetData) => {
      setSheet((prev) => ({ ...prev, ...sheetData } as SheetData))
    },
    onFieldUpdate: ({ updates, summary }) => {
      setFieldSummary(summary)
      setRecentUpdates(updates)
    },
    // L1 highlight-fade is handled by a useEffect on recentUpdates below.
    onError: (err) => {
      console.error('SSE error:', err)
      toast.error('Connection issue. Please retry.')
    },
  })

  // ── Ref-based autosave ────────────────────────────────────────────
  // Keep a ref with the latest values so save functions never depend on
  // `messages` or `stage` as effect dependencies (the root cause of the
  // stale-overwrite bug).
  const latestRef = useRef({
    sessionId: null as string | null,
    stage: 'greeting',
    messageCount: 0,
  })

  useEffect(() => {
    latestRef.current = {
      sessionId,
      stage,
      messageCount: messages.length,
    }
  }, [sessionId, stage, messages.length])

  // Stable save — reads from the ref, so it never goes stale.
  const saveProgressRef = useCallback(async () => {
    const latest = latestRef.current
    if (!latest.sessionId) return
    await apiClient.patch(`/discovery/${latest.sessionId}/progress`, {
      stage: latest.stage,
      client_message_count: latest.messageCount,
    })
  }, [])

  // Auto-save interval (every 30 s while session is active)
  useEffect(() => {
    if (!sessionId) return
    autoSaveTimerRef.current = setInterval(() => {
      saveProgressRef().catch((err) => console.error('Auto-save failed:', err))
    }, AUTO_SAVE_INTERVAL_MS)
    return () => {
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current)
        autoSaveTimerRef.current = null
      }
    }
  }, [sessionId, saveProgressRef])

  // Save when page becomes hidden (tab switch, minimize)
  useEffect(() => {
    const handler = () => {
      if (document.visibilityState === 'hidden') {
        saveProgressRef().catch((err) => console.error('Visibility save failed:', err))
      }
    }
    document.addEventListener('visibilitychange', handler)
    return () => document.removeEventListener('visibilitychange', handler)
  }, [saveProgressRef])

  // Save on unmount + abort in-flight SSE stream
  useEffect(() => {
    return () => {
      abort()
      void saveProgressRef().catch((err) => console.error('Unmount save failed:', err))
    }
  }, [saveProgressRef, abort])

  // Auto-save on stage change
  useEffect(() => {
    if (!sessionId) return
    if (prevStageRef.current === stage) return
    prevStageRef.current = stage
    saveProgressRef().catch((err) => console.error('Stage-change save failed:', err))
  }, [sessionId, stage, saveProgressRef])

  // L1: time-fade the "just filled" highlight after 8s so the accent doesn't
  // linger forever between AI turns. Cleared on next field_update or unmount.
  useEffect(() => {
    if (recentUpdates.length === 0) return
    const t = setTimeout(() => setRecentUpdates([]), 8000)
    return () => clearTimeout(t)
  }, [recentUpdates])

  // M6 hydration: for v2 projects, fetch the current field summary as soon as
  // we have a sessionId. Without this, the ProgressPanel sits empty on resume
  // until the user's next message triggers a field_update SSE event.
  useEffect(() => {
    if (!sessionId || flowVersion !== 'v2') return
    let cancelled = false
    apiClient.get(`/discovery/${sessionId}/field-summary`)
      .then(({ data }) => {
        if (!cancelled && data) setFieldSummary(data)
      })
      .catch(() => { /* 409 (v1) or 404 — let the empty state render */ })
    return () => { cancelled = true }
  }, [sessionId, flowVersion])

  // Fetch partner style metadata
  useEffect(() => {
    apiClient.get('/meta/partner-styles')
      .then(({ data }) => {
        setAllPartners(data)
        const match = data.find((p: PartnerStyleMeta) => p.id === partnerStyle)
        if (match) setPartnerMeta(match)
      })
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Resolve partner meta whenever style changes
  useEffect(() => {
    if (allPartners.length) {
      setPartnerMeta(allPartners.find((p) => p.id === partnerStyle) || null)
    }
  }, [partnerStyle, allPartners])

  // Load design sheet state from backend
  const loadSheet = useCallback(async (id: string) => {
    try {
      const { data } = await apiClient.get(`/discovery/${id}/sheet`)
      setSheet({
        problem: data.problem ?? undefined,
        audience: data.audience ?? undefined,
        mvp: data.mvp ?? undefined,
        features: data.features ?? undefined,
        tone: data.tone ?? undefined,
        platform: data.platform ?? undefined,
        tech_constraints: data.tech_constraints ?? undefined,
        success_metric: data.success_metric ?? undefined,
        confidence_score: data.confidence_score ?? 0,
        fields_data: data.fields_data ?? undefined,
      } as SheetData)
    } catch {
      // Sheet may not exist yet for fresh projects
      setSheet({ confidence_score: 0 })
    }
  }, [])

  // Fetch the pathway registry once. (Independent of the project — used to
  // render stage steppers + sheet field configs for v1.)
  useEffect(() => {
    fetchPathways()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Single bootstrap: project → flow_version → session → (v1 only) loadSheet → greeting.
  // Doing this in one effect (a) lets us skip loadSheet for v2 projects (audit
  // M4 — the design_sheet 404 was wasted), and (b) ensures `flow_version` is
  // known before the field-summary hydration effect fires.
  useEffect(() => {
    if (!projectId) return
    let cancelled = false

    const init = async () => {
      try {
        // Step 1: project (gives flow_version)
        let fv: 'v1' | 'v2' = 'v1'
        try {
          const { data: proj } = await apiClient.get(`/projects/${projectId}`)
          if (cancelled) return
          setActiveByProject(proj)
          fv = proj?.flow_version === 'v2' ? 'v2' : 'v1'
          setFlowVersion(fv)
        } catch {
          // Project fetch failed — keep v1 fallback so the legacy panel renders
        }

        // Step 2: start session
        const { data } = await apiClient.post('/discovery/start', { project_id: projectId })
        if (cancelled) return
        setSessionId(data.id)
        if (data.ai_partner_style) setPartnerStyle(data.ai_partner_style)

        // Step 3: v1 only — load the design sheet. v2 uses module_responses
        // via the field-summary endpoint instead, hydrated by a separate effect.
        if (fv === 'v1') {
          await loadSheet(data.id)
        }

        if (data.messages?.length) {
          setMessages(data.messages)
          if (data.stage) setStage(data.stage)
          return // session already has messages — skip auto-greeting
        }

        if (data.stage) setStage(data.stage)

        // Step 4: auto-trigger AI greeting for fresh sessions
        const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
        if (!cancelled) {
          await send(`${baseUrl}/discovery/${data.id}/init`, {})
        }
      } catch (err) {
        console.error('Failed to start session:', err)
        toast.error(extractError(err, "Couldn't start your discovery session."))
      }
    }

    init()
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const sendMessage = useCallback(async (content: string) => {
    if (!sessionId || !content.trim() || isStreaming) return

    setMessages((prev) => [...prev, { role: 'user', content }])
    setInput('')
    setChips([])
    setStreamingContent('')

    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    await send(`${baseUrl}/discovery/${sessionId}/message`, { content })
  }, [sessionId, isStreaming, send])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const handlePartnerSwitch = useCallback(async (newStyle: string) => {
    if (!sessionId || newStyle === partnerStyle) return
    setPartnerStyle(newStyle)
    try {
      await apiClient.patch(`/discovery/${sessionId}/partner`, { ai_partner_style: newStyle })
      // Add a system event to the chat timeline
      const partnerName = allPartners.find((p) => p.id === newStyle)?.name || newStyle
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `*AI Partner switched to ${partnerName}*` },
      ])
    } catch (err) {
      console.error('Failed to switch partner:', err)
      toast.error(extractError(err, "Couldn't switch AI partner."))
    }
  }, [sessionId, partnerStyle, allPartners])

  // ── Save Place ─────────────────────────────────────────────────
  const [savePlaceStatus, setSavePlaceStatus] = useState<'idle' | 'saving' | 'saved'>('idle')

  const handleSavePlace = useCallback(async () => {
    if (!sessionId || savePlaceStatus === 'saving') return
    setSavePlaceStatus('saving')
    try {
      await saveProgressRef()
      setSavePlaceStatus('saved')
      setTimeout(() => setSavePlaceStatus('idle'), 2500)
    } catch (err) {
      console.error('Save place failed:', err)
      toast.error(extractError(err, "Couldn't save your place."))
      setSavePlaceStatus('idle')
    }
  }, [sessionId, savePlaceStatus, saveProgressRef])

  const showExport = stage === 'confirm' || messages.length >= 4

  return (
    <div className="h-dvh bg-background flex overflow-hidden">
      <StageInterlude
        phase="discovery"
        message="Tell your AI partner about your idea. They'll extract the building blocks as you talk."
        stepIndex={0}
        totalSteps={5}
      />
      <Sidebar projectId={projectId} />

      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col min-h-0">
        {/* M2/L3: hide the stage-name subtitle for v2 — there's no meaningful
            stage progression in the unified flow (session.stage stays at
            "greeting" forever). The progress % is shown via the mobile badge
            and the right-side ProgressPanel instead. */}
        <TopBar title="Discovery" subtitle={flowVersion === 'v2' ? undefined : `Stage: ${stage}`}>
          {/* Active partner badge */}
          <ActivePartnerBadge partner={partnerMeta} onClick={() => setShowPartnerPicker(true)} />
          {/* Save Place button — visible once conversation has started */}
          {sessionId && messages.length >= 2 && (
            <button
              onClick={handleSavePlace}
              disabled={savePlaceStatus === 'saving'}
              aria-label="Save your place"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 min-h-[44px] md:min-h-0 text-xs font-medium rounded-lg bg-white/5 border border-border text-text-muted hover:text-white hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-accent/50 transition-colors disabled:opacity-50"
            >
              <span aria-hidden="true">{savePlaceStatus === 'saved' ? '✓' : '🔖'}</span>
              <span>
                {savePlaceStatus === 'saving'
                  ? 'Saving...'
                  : savePlaceStatus === 'saved'
                    ? 'Place Saved!'
                    : 'Save Place'}
              </span>
            </button>
          )}
          {/* Transcript export */}
          {showExport && sessionId && (
            <TranscriptExportMenu sessionId={sessionId} messages={messages} />
          )}
          {/* Mobile toggle for design sheet / progress panel */}
          <button
            onClick={() => setShowSheet(!showSheet)}
            className="md:hidden px-3 py-1.5 rounded-lg text-xs font-medium bg-accent/10 text-accent border border-accent/20"
          >
            {showSheet ? 'Chat' : flowVersion === 'v2' ? 'Progress' : 'Sheet'}
            {flowVersion === 'v2'
              ? fieldSummary && fieldSummary.total_fields > 0 && (
                  <Badge variant="accent" className="ml-1.5">{fieldSummary.overall_percent}%</Badge>
                )
              : sheet.confidence_score > 0 && (
                  <Badge variant="accent" className="ml-1.5">{sheet.confidence_score}%</Badge>
                )}
          </button>
        </TopBar>

        <div className="flex-1 flex min-h-0">
          {/* Left: Stepper — hidden on mobile, and hidden entirely for v2
              (no stage progression in the unified flow). */}
          {flowVersion !== 'v2' && (
            <div className="hidden md:block w-48 border-r border-border bg-surface/30 shrink-0 overflow-y-auto">
              <StagesStepper currentStage={stage} stages={activePathway?.stages} />
            </div>
          )}

          {/* Center: Chat — hidden on mobile when sheet is shown */}
          <div className={`flex-1 flex flex-col min-h-0 ${showSheet ? 'hidden md:flex' : 'flex'}`}>
            {/* Mobile stage indicator (v1 only) */}
            {flowVersion !== 'v2' && (
              <div className="md:hidden flex items-center gap-2 px-4 py-2 border-b border-border bg-surface/30 overflow-x-auto">
                <span className="text-[10px] text-text-muted font-medium shrink-0">Stage:</span>
                <span className="text-[10px] text-accent font-semibold shrink-0">{stage}</span>
              </div>
            )}

            <ChatThread messages={messages} streamingContent={streamingContent} />
            <PulseBeacon id="discovery:chips">
              <QuickChips chips={chips} onSelect={sendMessage} disabled={isStreaming} />
            </PulseBeacon>

            {/* Proceed to pathway CTA — gate depends on flow version.
                v1: confidence_score >= 70 → /pathway-review/{id}
                v2: always available once a summary exists with required fields;
                    shows a warning chip when <80% of required fields are filled.
                    Routes to /design-kit/{id}. */}
            {projectId && flowVersion === 'v1' && sheet.confidence_score >= 70 && (
              <div className="px-3 md:px-4 py-2 shrink-0">
                <PulseBeacon id="discovery:proceed">
                  <button
                    type="button"
                    onClick={() => navigate(`/pathway-review/${projectId}`)}
                    className="w-full py-2.5 rounded-xl text-sm font-semibold bg-accent/20 text-accent border border-accent/30 hover:bg-accent/30 transition-colors"
                  >
                    Proceed to Design Kit Pathway
                  </button>
                </PulseBeacon>
              </div>
            )}
            {projectId && flowVersion === 'v2' && fieldSummary && fieldSummary.total_fields > 0 && (() => {
              // Audit M8: gate on total_fields > 0 (not required_total) so
              // pathways made entirely of optional fields still get a Proceed
              // button. The required-percent warning chip only shows when
              // there actually are required fields to gate on.
              const hasRequired = fieldSummary.required_total > 0
              const requiredPct = hasRequired
                ? Math.round((fieldSummary.required_filled / fieldSummary.required_total) * 100)
                : 100
              const short = hasRequired && requiredPct < 80
              return (
                <div className="px-3 md:px-4 py-2 shrink-0">
                  <PulseBeacon id="discovery:proceed">
                    <button
                      type="button"
                      onClick={() => navigate(`/design-kit/${projectId}`)}
                      className="w-full py-2.5 rounded-xl text-sm font-semibold bg-accent/20 text-accent border border-accent/30 hover:bg-accent/30 transition-colors flex items-center justify-center gap-2"
                    >
                      <span>Proceed to Design Kit</span>
                      {short && (
                        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-amber-400/20 border border-amber-400/30 text-amber-300">
                          {requiredPct}% required — keep going?
                        </span>
                      )}
                    </button>
                  </PulseBeacon>
                </div>
              )
            })()}

            {/* Input */}
            <Whisper id="discovery:input" text="Use the quick replies, speak via the mic, or type freely">
            <div className="border-t border-border p-3 md:p-4 shrink-0">
              <div className="flex gap-2 md:gap-3 items-end">
                <VoiceMicButton
                  className="shrink-0"
                  onTranscript={(text) => setInput(text)}
                />
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type or speak your response..."
                  aria-label="Enter your response to the AI partner"
                  className="flex-1 bg-surface border border-border rounded-xl px-3 md:px-4 py-2.5 md:py-3 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 resize-none h-11 md:h-12 max-h-32"
                  rows={1}
                />
                <Button onClick={() => sendMessage(input)} disabled={!input.trim() || isStreaming}>
                  Send
                </Button>
              </div>
            </div>
            </Whisper>
          </div>

          {/* Right: Progress (v2) or Design Sheet (v1) — full width on mobile when
              toggled, side panel on desktop. The v2 ProgressPanel hydrates from
              the field_update SSE event; the v1 DesignSheetPanel from sheet_update. */}
          <div className={`${showSheet ? 'flex' : 'hidden'} md:flex w-full md:w-72 border-l-0 md:border-l border-border bg-surface/30 shrink-0 flex-col min-h-0`}>
            <div className="px-4 py-3 border-b border-border shrink-0">
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                {flowVersion === 'v2' ? 'Design Kit Progress' : 'Design Sheet'}
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto">
              {flowVersion === 'v2' ? (
                <ProgressPanel summary={fieldSummary} recentUpdates={recentUpdates} />
              ) : (
                <DesignSheetPanel sheet={sheet} fieldConfigs={activePathway?.sheet_fields} />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Partner selector modal */}
      <PartnerSelector
        open={showPartnerPicker}
        currentStyle={partnerStyle}
        onSelect={handlePartnerSwitch}
        onClose={() => setShowPartnerPicker(false)}
      />
    </div>
  )
}
