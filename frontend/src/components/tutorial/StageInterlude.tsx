/**
 * StageInterlude — Glass card overlay shown once per phase.
 * Auto-dismisses after 4 seconds or on click.
 */
import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTutorialStore } from '../../stores/tutorialStore'

interface StageInterludeProps {
  phase: string
  message: string
  stepIndex: number
  totalSteps: number
}

function ProgressArc({ current, total }: { current: number; total: number }) {
  const size = 36
  const strokeWidth = 2.5
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const gap = 4
  const segmentLength = (circumference - gap * total) / total

  return (
    <svg width={size} height={size} className="mx-auto mb-2">
      {Array.from({ length: total }, (_, i) => {
        const offset = i * (segmentLength + gap)
        const isCompleted = i < current
        const isCurrent = i === current
        return (
          <circle
            key={i}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={isCompleted || isCurrent ? 'var(--color-accent)' : 'rgba(255,255,255,0.1)'}
            strokeWidth={strokeWidth}
            strokeDasharray={`${segmentLength} ${circumference - segmentLength}`}
            strokeDashoffset={-offset}
            strokeLinecap="round"
            opacity={isCompleted ? 0.4 : isCurrent ? 1 : 0.3}
            style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
          />
        )
      })}
    </svg>
  )
}

export function StageInterlude({ phase, message, stepIndex, totalSteps }: StageInterludeProps) {
  const { seenInterludes, markInterludeSeen } = useTutorialStore()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (seenInterludes[phase]) return
    // Small delay so page content renders first
    const showTimer = setTimeout(() => setVisible(true), 300)
    return () => clearTimeout(showTimer)
  }, [phase, seenInterludes])

  const dismiss = useCallback(() => {
    setVisible(false)
    markInterludeSeen(phase)
  }, [phase, markInterludeSeen])

  useEffect(() => {
    if (!visible) return
    const timer = setTimeout(() => dismiss(), 4000)
    return () => clearTimeout(timer)
  }, [visible, dismiss])

  if (seenInterludes[phase]) return null

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center cursor-pointer"
          onClick={dismiss}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          <motion.div
            className="bg-white/5 backdrop-blur-xl border border-accent/20 rounded-[var(--radius-card)] px-8 py-6 max-w-sm text-center shadow-[0_0_40px_rgba(0,229,255,0.08)]"
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.3 }}
          >
            <ProgressArc current={stepIndex} total={totalSteps} />
            <p className="text-white text-sm leading-relaxed">{message}</p>
            <p className="text-text-muted text-[10px] mt-3 opacity-60">Click anywhere to dismiss</p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
