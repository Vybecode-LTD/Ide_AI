/**
 * UpgradeModal — In-app plan selection and Stripe checkout.
 * Follows the ShareDialog modal pattern (backdrop + Card + escape-to-close).
 * @module components/billing/UpgradeModal
 */
import { useState, useEffect } from 'react'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import apiClient from '../../lib/apiClient'
import toast from 'react-hot-toast'
import { PLANS, type Cycle } from '../../lib/plans'

interface UpgradeModalProps {
  open: boolean
  onClose: () => void
  currentPlan?: string // 'free' | 'basic' | 'pro'
}

const PLAN_RANK: Record<string, number> = { free: 0, basic: 1, pro: 2 }

export function UpgradeModal({ open, onClose, currentPlan = 'free' }: UpgradeModalProps) {
  const [cycle, setCycle] = useState<Cycle>('yearly')
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null)

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  // Reset state when opened
  useEffect(() => {
    if (open) {
      setCheckoutLoading(null)
    }
  }, [open])

  if (!open) return null

  const handleCheckout = async (planId: string) => {
    const plan = PLANS.find((p) => p.id === planId)
    if (!plan) return
    const priceId = cycle === 'yearly' ? plan.stripePriceYearly : plan.stripePriceMonthly
    if (!priceId) return

    setCheckoutLoading(planId)
    try {
      const { data } = await apiClient.post('/billing/checkout', {
        price_id: priceId,
        cycle,
      })
      window.location.href = data.checkout_url
    } catch {
      toast.error('Failed to start checkout. Please try again.')
    } finally {
      setCheckoutLoading(null)
    }
  }

  const currentRank = PLAN_RANK[currentPlan] ?? 0

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={onClose} />

      {/* Dialog */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <Card glow className="w-full max-w-3xl max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-bold text-white">Upgrade Your Plan</h2>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-white transition-colors text-lg leading-none"
            >
              &times;
            </button>
          </div>

          {/* Billing toggle */}
          <div className="flex justify-center mb-6">
            <div className="inline-flex items-center gap-1 p-1 rounded-full border border-border bg-surface/60">
              <button
                onClick={() => setCycle('monthly')}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                  cycle === 'monthly'
                    ? 'bg-accent text-background'
                    : 'text-text-muted hover:text-white'
                }`}
              >
                Monthly
              </button>
              <button
                onClick={() => setCycle('yearly')}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                  cycle === 'yearly'
                    ? 'bg-accent text-background'
                    : 'text-text-muted hover:text-white'
                }`}
              >
                Yearly
                <span className="ml-1.5 text-[10px] font-bold text-green-400">SAVE 20%+</span>
              </button>
            </div>
          </div>

          {/* Plan grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PLANS.map((plan) => {
              const planRank = PLAN_RANK[plan.id] ?? 0
              const isCurrent = plan.id === currentPlan
              const isDowngrade = planRank < currentRank

              return (
                <div
                  key={plan.id}
                  className={`relative flex flex-col rounded-xl border p-5 transition-all ${
                    plan.popular
                      ? 'border-accent/50 bg-accent/[0.05] shadow-[0_0_30px_rgba(0,229,255,0.06)]'
                      : 'border-white/[0.08] bg-white/[0.03]'
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[10px] font-bold bg-accent text-background uppercase tracking-wider">
                      Most Popular
                    </div>
                  )}

                  <div className="mb-4">
                    <h3 className="text-base font-bold text-white">{plan.name}</h3>
                    <p className="text-[11px] text-text-muted mt-0.5">{plan.tagline}</p>
                  </div>

                  {/* Price */}
                  <div className="mb-4">
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-black text-white">
                        ${cycle === 'yearly' ? plan.yearly : plan.monthly}
                      </span>
                      {plan.monthly > 0 && (
                        <span className="text-xs text-text-muted">/ mo</span>
                      )}
                    </div>
                    {plan.monthly > 0 && cycle === 'yearly' && (
                      <p className="text-[10px] text-text-muted mt-0.5">
                        Billed ${plan.yearly * 12}/yr &middot;{' '}
                        <span className="text-green-400">
                          Save ${(plan.monthly - plan.yearly) * 12}/yr
                        </span>
                      </p>
                    )}
                    {plan.monthly === 0 && (
                      <p className="text-[10px] text-text-muted mt-0.5">Free forever</p>
                    )}
                  </div>

                  {/* Features */}
                  <ul className="space-y-2 mb-5 flex-1 text-[13px]">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2">
                        <svg className="w-3.5 h-3.5 mt-0.5 text-accent shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                        <span className="text-white/90">{f}</span>
                      </li>
                    ))}
                    {plan.excluded?.map((f) => (
                      <li key={f} className="flex items-start gap-2">
                        <svg className="w-3.5 h-3.5 mt-0.5 text-white/20 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        <span className="text-white/30">{f}</span>
                      </li>
                    ))}
                  </ul>

                  {/* CTA */}
                  {isCurrent ? (
                    <Button size="sm" variant="secondary" disabled className="w-full">
                      Current Plan
                    </Button>
                  ) : isDowngrade ? (
                    <Button size="sm" variant="ghost" disabled className="w-full opacity-40">
                      {plan.name}
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant={plan.popular ? 'primary' : 'secondary'}
                      className="w-full"
                      disabled={checkoutLoading === plan.id}
                      onClick={() => handleCheckout(plan.id)}
                    >
                      {checkoutLoading === plan.id ? 'Redirecting...' : plan.cta}
                    </Button>
                  )}
                </div>
              )
            })}
          </div>
        </Card>
      </div>
    </>
  )
}
