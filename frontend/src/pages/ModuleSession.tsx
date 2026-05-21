/**
 * ModuleSession — AI-guided conversation for a single module.
 * Uses SSE streaming (same pattern as Discovery chat).
 * Shows module completion summary and Next Module CTA.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { PathwayProgress } from '../components/pathway/PathwayProgress'
import { QuickChips } from '../components/discovery/QuickChips'
import { Button } from '../components/ui/Button'
import { StageInterlude, Whisper } from '../components/tutorial'
import { useSSE } from '../hooks/useSSE'
import { useModulePathwayStore } from '../stores/modulePathwayStore'
import apiClient from '../lib/apiClient'
import type { ModuleStartResponse } from '../types/modulePathway'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export function ModuleSession() {
  const { projectId, moduleId } = useParams<{ projectId: string; moduleId: string }>()
  const navigate = useNavigate()
  const {
    assembledModules,
    pathway,
    moduleResponses,
    fetchPathway,
    fetchResponses,
    setActiveModule,
  } = useModulePathwayStore()

  const [messages, setMessages] = useState<Message[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const [input, setInput] = useState('')
  const [chips, setChips] = useState<string[]>([])
  const [isComplete, setIsComplete] = useState(false)
  const [moduleLabel, setModuleLabel] = useState('')
  const [questionNumber, setQuestionNumber] = useState(1)
  const [totalQuestions, setTotalQuestions] = useState(3)
  const scrollRef = useRef<HTMLDivElement>(null)

  const baseUrl = (import.meta.env.VITE_API_BASE_URL || '/api/v1')

  const { send, isStreaming } = useSSE({
    onToken(token) {
      setStreamingContent(prev => prev + token)
    },
    onDone(data) {
      setStreamingContent(prev => {
        if (prev) {
          setMessages(msgs => [...msgs, { role: 'assistant', content: prev }])
        }
        return ''
      })
      if (data.complete) setIsComplete(true)
      if (data.chips?.length) setChips(data.chips)
      if (data.question_number) setQuestionNumber(data.question_number)
    },
    onError(err) {
      console.error('[ModuleSession] SSE error:', err)
    },
  })

  // Initialize module
  useEffect(() => {
    if (!projectId || !moduleId) return

    const init = async () => {
      await fetchPathway(projectId)
      await fetchResponses(projectId)
      setActiveModule(moduleId)

      try {
        const { data } = await apiClient.post<ModuleStartResponse>(
          `/modules/${projectId}/${moduleId}/start`
        )

        if (data.existing_module && data.redirect) {
          navigate(`${data.redirect}/${projectId}`)
          return
        }

        // Resumed: load existing messages from backend
        if (data.resumed && data.messages?.length) {
          setModuleLabel(data.label)
          setTotalQuestions(data.total_questions)
          setQuestionNumber(data.question_number)
          setMessages(data.messages as Message[])
          return
        }

        // Already complete: show transcript and completion state
        if (data.already_complete) {
          setModuleLabel(data.label || moduleId || '')
          setIsComplete(true)
          if (data.messages?.length) {
            setMessages(data.messages as Message[])
          }
          return
        }

        setModuleLabel(data.label)
        setTotalQuestions(data.total_questions)
        setMessages([{ role: 'assistant', content: data.question }])

        // Parse chips from first question
        const chipMatch = data.question.match(/\[(?:CHIPS|chips|Chips):\s*(.*?)\]\s*[.!]?\s*$/)
        if (chipMatch) {
          setChips(chipMatch[1].split('|').map((c: string) => c.trim()).filter(Boolean))
        }
      } catch (err) {
        console.error('[ModuleSession] start failed:', err)
      }
    }

    init()
  }, [projectId, moduleId])

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, streamingContent])

  const handleSend = useCallback(
    (text?: string) => {
      const content = text || input.trim()
      if (!content || isStreaming || !projectId || !moduleId) return

      setMessages(prev => [...prev, { role: 'user', content }])
      setInput('')
      setChips([])
      setStreamingContent('')

      send(`${baseUrl}/modules/${projectId}/${moduleId}/respond`, { content })
    },
    [input, isStreaming, projectId, moduleId, send, baseUrl],
  )

  const handleSkip = async () => {
    if (!projectId || !moduleId) return
    await apiClient.post(`/modules/${projectId}/${moduleId}/skip`)
    handleNextModule()
  }

  const handleNextModule = () => {
    if (!projectId || !pathway) return

    const currentIndex = pathway.modules.indexOf(moduleId!)
    const nextIndex = currentIndex + 1

    if (nextIndex < pathway.modules.length) {
      const nextModuleId = pathway.modules[nextIndex]
      navigate(`/module-session/${projectId}/${nextModuleId}`)
    } else {
      // All modules done — go back to pathway execution view
      navigate(`/pathway-execute/${projectId}`)
    }
  }

  // Find current module info from assembled modules
  const currentModule = assembledModules.find(m => m.module_id === moduleId)

  return (
    <div className="h-screen bg-background flex overflow-hidden">
      <StageInterlude
        phase="module-session"
        message="Answer your AI partner's questions. They'll extract structured data from your answers."
        stepIndex={3}
        totalSteps={5}
      />
      <Sidebar />
      <div className="flex-1 flex min-w-0">
        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar />

          {/* Module header */}
          <div className="px-4 md:px-6 py-3 border-b border-white/5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">{moduleLabel || moduleId}</h2>
                <p className="text-xs text-text-muted">
                  Question {questionNumber}/{totalQuestions}
                  {currentModule && ` · ${currentModule.mode} mode`}
                </p>
              </div>
              <Whisper id="module:skip" text="Skip if this module isn't relevant to your concept">
                <button
                  type="button"
                  onClick={handleSkip}
                  className="text-xs text-text-muted hover:text-yellow-400 transition-colors"
                >
                  Skip module
                </button>
              </Whisper>
            </div>
          </div>

          {/* Chat messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 md:px-6 py-4 space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] md:max-w-[70%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-accent/20 text-white rounded-br-md'
                      : 'bg-white/[0.05] text-white/90 rounded-bl-md'
                  }`}
                >
                  {msg.content.replace(/\[CHIPS:.*?\]\s*$/, '').trim()}
                </div>
              </div>
            ))}

            {/* Streaming content */}
            {streamingContent && (
              <div className="flex justify-start">
                <div className="max-w-[85%] md:max-w-[70%] px-4 py-3 rounded-2xl rounded-bl-md bg-white/[0.05] text-white/90 text-sm leading-relaxed">
                  {streamingContent.replace(/\[CHIPS:.*?\]\s*$/, '').trim()}
                  <span className="inline-block w-1.5 h-4 bg-accent/50 animate-pulse ml-0.5" />
                </div>
              </div>
            )}
          </div>

          {/* Module complete banner */}
          {isComplete && (
            <div className="px-4 md:px-6 py-4 border-t border-white/5">
              <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 text-center">
                <p className="text-green-400 font-medium text-sm mb-2">Module Complete</p>
                <Button onClick={handleNextModule} className="px-6">
                  Next Module
                </Button>
              </div>
            </div>
          )}

          {/* Input area */}
          {!isComplete && (
            <div className="px-4 md:px-6 pb-4 md:pb-6 pt-2">
              {chips.length > 0 && (
                <QuickChips chips={chips} onSelect={handleSend} />
              )}
              <div className="flex gap-2 mt-2">
                <input
                  type="text"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                  placeholder="Type your answer..."
                  disabled={isStreaming}
                  className="flex-1 bg-white/[0.05] border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent/40 disabled:opacity-50"
                />
                <Button
                  onClick={() => handleSend()}
                  disabled={isStreaming || !input.trim()}
                  className="px-4"
                >
                  Send
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar: Pathway Progress (desktop only) */}
        <div className="hidden lg:block w-64 border-l border-white/5 p-4 overflow-y-auto">
          <h3 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">Pathway Progress</h3>
          <PathwayProgress
            modules={assembledModules}
            responses={moduleResponses}
            activeModuleId={moduleId ?? null}
            onModuleClick={(mid) => {
              if (projectId) navigate(`/module-session/${projectId}/${mid}`)
            }}
          />
        </div>
      </div>
    </div>
  )
}
