/**
 * UpgradeModal — Shown when a user hits an entitlement limit (403).
 * Displays the limit info and a link to the pricing page.
 * @module components/ui/UpgradeModal
 */
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from './Button'
import type { EntitlementDetail } from '../../lib/extractError'

interface UpgradeModalProps {
  /** The structured 403 detail from the entitlement guard, or null to hide. */
  detail: EntitlementDetail | null
  onClose: () => void
}

const PLAN_LABELS: Record<string, string> = {
  free: 'Free',
  basic: 'Basic',
  pro: 'Pro',
}

function featureLabel(detail: EntitlementDetail): string {
  if (detail.code === 'project_limit_reached') return 'projects'
  const f = detail.feature ?? ''
  return f.replace(/_/g, ' ')
}

export function UpgradeModal({ detail, onClose }: UpgradeModalProps) {
  if (!detail) return null

  const planName = PLAN_LABELS[detail.plan] ?? detail.plan
  const label = featureLabel(detail)

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* Modal card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          transition={{ duration: 0.2 }}
          className="relative z-10 w-full max-w-sm rounded-2xl border border-border bg-surface/90 backdrop-blur-xl p-6 shadow-[0_0_40px_rgba(0,229,255,0.08)]"
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-3 right-3 text-text-muted hover:text-white transition-colors text-lg leading-none"
            aria-label="Close"
          >
            &times;
          </button>

          {/* Icon */}
          <div className="text-center mb-4">
            <span className="inline-block text-4xl opacity-70">&#x26A1;</span>
          </div>

          {/* Title */}
          <h2 className="text-center text-white font-semibold text-lg mb-2">
            {detail.code === 'project_limit_reached'
              ? 'Project Limit Reached'
              : 'Feature Limit Reached'}
          </h2>

          {/* Description */}
          <p className="text-center text-text-muted text-sm mb-4">
            Your <span className="text-white font-medium">{planName}</span> plan
            allows{' '}
            <span className="text-white font-medium">
              {detail.limit} {label}
            </span>
            . You&apos;ve used{' '}
            <span className="text-accent font-medium">{detail.current}</span>.
          </p>

          {/* Usage bar */}
          <div className="mb-6">
            <div className="h-2 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full rounded-full bg-accent transition-all"
                style={{
                  width: `${Math.min((detail.current / detail.limit) * 100, 100)}%`,
                }}
              />
            </div>
            <p className="text-[10px] text-text-muted mt-1 text-right">
              {detail.current} / {detail.limit}
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" className="flex-1" onClick={onClose}>
              Maybe Later
            </Button>
            <Button
              size="sm"
              className="flex-1"
              onClick={() => {
                window.location.href = '/pricing'
              }}
            >
              View Plans
            </Button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
