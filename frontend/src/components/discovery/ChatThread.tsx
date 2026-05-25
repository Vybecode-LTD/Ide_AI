/**
 * ChatThread — Scrollable message list for AI conversation.
 * Strips [CHIPS: ...] annotations from displayed text.
 * @module components/discovery/ChatThread
 */
import { useEffect, useRef } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatThreadProps {
  messages: Message[]
  streamingContent?: string
}

/** Remove the [CHIPS: ...] line that the AI appends for the frontend chip system. */
function stripChipsLine(text: string): string {
  return text.replace(/\n?\[CHIPS:.*?\]/g, '').trim()
}

export function ChatThread({ messages, streamingContent }: ChatThreadProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  return (
    <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 md:px-6 py-3 md:py-4 space-y-3 md:space-y-4">
      {messages.map((msg, i) => (
        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
          <div
            className={`max-w-[90%] md:max-w-[80%] rounded-xl px-3 md:px-4 py-2.5 md:py-3 text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-accent/15 text-white border border-accent/20'
                : 'bg-surface border border-border text-white'
            }`}
          >
            <p className="whitespace-pre-wrap break-words">{stripChipsLine(msg.content)}</p>
          </div>
        </div>
      ))}

      {streamingContent && (
        <div className="flex justify-start">
          <div className="max-w-[90%] md:max-w-[80%] rounded-xl px-3 md:px-4 py-2.5 md:py-3 text-sm leading-relaxed bg-surface border border-border text-white">
            <p className="whitespace-pre-wrap break-words">{stripChipsLine(streamingContent)}<span className="animate-pulse text-accent">|</span></p>
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  )
}
