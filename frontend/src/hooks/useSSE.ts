/**
 * useSSE — EventSource-like hook using fetch for SSE with POST support.
 * @module hooks/useSSE
 */
import { useCallback, useRef, useState } from 'react'
import { getAuthToken } from '../lib/apiClient'

interface SSEMessage {
  type: string
  content?: string
  stage?: string
  chips?: string[]
  sheet?: Record<string, unknown>
  updates?: FieldUpdate[]
  summary?: FieldSummary
  complete?: boolean
  question_number?: number
  [key: string]: unknown
}

interface SSEDoneData {
  stage: string
  chips: string[]
  complete?: boolean
  question_number?: number
}

/** Single field update emitted by the v2 discovery extractor. */
export interface FieldUpdate {
  module_id: string
  field_key: string
  value: unknown
}

/** Aggregate field-completion stats payload from the backend
 *  (see `compute_field_summary` in discovery_service.py). */
export interface FieldSummary {
  total_filled: number
  total_fields: number
  required_filled: number
  required_total: number
  overall_percent: number
  per_module: Array<{
    module_id: string
    label: string
    filled: number
    total: number
    required_filled: number
    required_total: number
  }>
}

export interface FieldUpdatePayload {
  updates: FieldUpdate[]
  summary: FieldSummary
}

interface UseSSEOptions {
  onToken?: (token: string) => void
  onDone?: (data: SSEDoneData) => void
  onSheetUpdate?: (sheet: Record<string, unknown>) => void
  onFieldUpdate?: (payload: FieldUpdatePayload) => void
  onError?: (error: Error) => void
}

export function useSSE(options: UseSSEOptions) {
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const optionsRef = useRef(options)
  optionsRef.current = options

  const send = useCallback(async (url: string, body: Record<string, unknown>) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setIsStreaming(true)

    try {
      const token = await getAuthToken()
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      let receivedDone = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          // Flush remaining buffer — the 'done' event often lands here
          buffer += decoder.decode()
        } else {
          buffer += decoder.decode(value, { stream: true })
        }

        const lines = buffer.split('\n')
        buffer = done ? '' : (lines.pop() || '')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data: SSEMessage = JSON.parse(line.slice(6))
            if (data.type === 'token' && data.content) {
              optionsRef.current.onToken?.(data.content)
            } else if (data.type === 'done') {
              receivedDone = true
              optionsRef.current.onDone?.({
                stage: data.stage || '',
                chips: data.chips || [],
                complete: data.complete,
                question_number: data.question_number,
              })
            } else if (data.type === 'sheet_update' && data.sheet) {
              optionsRef.current.onSheetUpdate?.(data.sheet)
            } else if (data.type === 'field_update' && data.summary) {
              optionsRef.current.onFieldUpdate?.({
                updates: data.updates ?? [],
                summary: data.summary,
              })
            }
          } catch { /* skip malformed lines */ }
        }

        if (done) break
      }

      // Safety net: if stream ended without a 'done' event, fire onDone
      // with empty stage/chips so the UI doesn't get stuck
      if (!receivedDone) {
        optionsRef.current.onDone?.({ stage: '', chips: [] })
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        optionsRef.current.onError?.(err as Error)
      }
    } finally {
      setIsStreaming(false)
    }
  }, [])

  const abort = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { send, abort, isStreaming }
}
