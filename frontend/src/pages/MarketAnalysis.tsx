/**
 * MarketAnalysis — AI-powered market research with live generation streaming.
 * Displays target market, competitors, TAM/SAM/SOM, revenue projections, and marketing strategy.
 * @module pages/MarketAnalysis
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import apiClient, { getAuthToken } from '../lib/apiClient'
import { downloadBlob } from '../lib/exportUtils'
import type { EntitlementDetail } from '../lib/extractError'
import { EntitlementLimitModal } from '../components/ui/EntitlementLimitModal'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MarketAnalysisData {
  id: string
  project_id: string
  target_market: TargetMarket | null
  competitive_landscape: CompetitiveLandscape | null
  market_metrics: MarketMetrics | null
  revenue_projections: RevenueProjections | null
  marketing_strategies: MarketingStrategies | null
  status: string
  error_message: string | null
}

interface TargetMarket {
  summary: string
  demographics: Record<string, string>
  psychographics: {
    values: string[]
    pain_points: string[]
    buying_behavior: string
    tech_savviness: string
    brand_affinity: string
  }
  market_segments: Array<{
    name: string
    size_pct: number
    description: string
    priority: string
  }>
  user_personas: Array<{
    name: string
    role: string
    goal: string
    frustration: string
  }>
}

interface CompetitiveLandscape {
  summary: string
  direct_competitors: Array<{
    name: string
    description: string
    strengths: string[]
    weaknesses: string[]
    pricing: string
    market_share_pct: number
    threat_level: string
  }>
  indirect_competitors: Array<{
    name: string
    description: string
    overlap: string
  }>
  competitive_advantages: string[]
  barriers_to_entry: string[]
  market_gaps: string[]
}

interface MarketMetrics {
  tam: { value_usd: number; description: string; methodology: string }
  sam: { value_usd: number; description: string; methodology: string }
  som: { value_usd: number; description: string; methodology: string }
  growth_rate_pct: number
  growth_trend: string
  market_maturity: string
  key_stats: Array<{ label: string; value: string; source: string }>
  industry_trends: Array<{ trend: string; impact: string; direction: string }>
}

interface RevenueProjections {
  pricing_model: string
  pricing_tiers: Array<{
    name: string
    price_monthly: number
    features: string[]
    target_segment: string
  }>
  scenarios: {
    best_case: RevenueScenario
    likely_case: RevenueScenario
    worst_case: RevenueScenario
  }
  break_even_months: number
  key_revenue_drivers: string[]
  revenue_risks: string[]
}

interface RevenueScenario {
  year_1: { revenue: number; users: number; paying_users: number; mrr: number }
  year_2: { revenue: number; users: number; paying_users: number; mrr: number }
  year_3: { revenue: number; users: number; paying_users: number; mrr: number }
  assumptions: string[]
}

interface MarketingStrategies {
  summary: string
  channels: Array<{
    name: string
    priority: string
    budget_monthly_usd: number
    expected_cac: number
    tactics: string[]
    timeline: string
    kpis: string[]
  }>
  launch_strategy: {
    pre_launch: string[]
    launch_week: string[]
    post_launch: string[]
  }
  content_ideas: Array<{
    type: string
    title: string
    goal: string
  }>
  partnerships: Array<{
    type: string
    description: string
  }>
  budget_summary: {
    monthly_min_usd: number
    monthly_max_usd: number
    allocation: Array<{ category: string; pct: number }>
  }
}

type TabKey = 'target_market' | 'competitive_landscape' | 'market_metrics' | 'revenue_projections' | 'marketing_strategies'

const TABS: Array<{ key: TabKey; label: string; icon: string }> = [
  { key: 'target_market', label: 'Target Market', icon: '\u{1F3AF}' },
  { key: 'competitive_landscape', label: 'Competitors', icon: '\u{2694}\u{FE0F}' },
  { key: 'market_metrics', label: 'Metrics', icon: '\u{1F4CA}' },
  { key: 'revenue_projections', label: 'Revenue', icon: '\u{1F4B0}' },
  { key: 'marketing_strategies', label: 'Strategy', icon: '\u{1F680}' },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Safe array helper — returns [] if input is not an array. */
function safeArr<T>(v: unknown): T[] {
  return Array.isArray(v) ? v : []
}

function formatUSD(n: number): string {
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n}`
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return `${n}`
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-white/10 text-text-muted',
    generating: 'bg-accent/20 text-accent animate-pulse',
    complete: 'bg-emerald-500/20 text-emerald-400',
    error: 'bg-red-500/20 text-red-400',
  }
  return (
    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${colors[status] || colors.pending}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

/** Simple horizontal bar chart using Tailwind. */
function BarChart({ items, maxValue }: { items: Array<{ label: string; value: number; color?: string }>; maxValue?: number }) {
  const max = maxValue || Math.max(...items.map(i => i.value), 1)
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i}>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-text-muted">{item.label}</span>
            <span className="text-white font-medium">{typeof item.value === 'number' && item.value > 999 ? formatUSD(item.value) : `${item.value}%`}</span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${Math.min((item.value / max) * 100, 100)}%`,
                backgroundColor: item.color || 'var(--color-accent)',
              }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

/** Donut chart built with CSS conic-gradient. */
function DonutChart({ segments }: { segments: Array<{ label: string; pct: number; color: string }> }) {
  const gradientStops = useMemo(() => {
    return segments.reduce<{ stops: string[]; running: number }>(
      (acc, seg) => {
        const start = acc.running
        const end = start + seg.pct
        acc.stops.push(`${seg.color} ${start}% ${end}%`)
        acc.running = end
        return acc
      },
      { stops: [], running: 0 },
    ).stops
  }, [segments])
  const conicGradient = `conic-gradient(${gradientStops.join(', ')})`

  return (
    <div className="flex items-center gap-6">
      <div
        className="w-28 h-28 rounded-full shrink-0"
        style={{
          background: conicGradient,
          mask: 'radial-gradient(farthest-side, transparent 60%, #000 60.5%)',
          WebkitMask: 'radial-gradient(farthest-side, transparent 60%, #000 60.5%)',
        }}
      />
      <div className="space-y-1.5">
        {segments.map((seg, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: seg.color }} />
            <span className="text-text-muted">{seg.label}</span>
            <span className="text-white font-medium ml-auto">{seg.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section renderers
// ---------------------------------------------------------------------------

function TargetMarketSection({ data }: { data: TargetMarket }) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-text-muted leading-relaxed">{data.summary}</p>

      {/* Demographics */}
      <Card>
        <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Demographics</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {Object.entries(data.demographics || {}).map(([key, value]) => (
            <div key={key} className="bg-white/5 rounded-lg px-3 py-2">
              <div className="text-[10px] text-text-muted uppercase mb-0.5">{key.replace(/_/g, ' ')}</div>
              <div className="text-sm text-white">{value}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Market Segments */}
      {data.market_segments?.length > 0 && (
        <Card>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Market Segments</h4>
          <BarChart
            items={data.market_segments.map(s => ({ label: s.name, value: s.size_pct }))}
            maxValue={100}
          />
          <div className="mt-4 space-y-2">
            {data.market_segments.map((seg, i) => (
              <div key={i} className="text-xs text-text-muted">
                <span className="text-white font-medium">{seg.name}</span>
                <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] ${
                  seg.priority === 'primary' ? 'bg-accent/20 text-accent' :
                  seg.priority === 'secondary' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-white/10 text-text-muted'
                }`}>{seg.priority}</span>
                {' — '}{seg.description}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* User Personas */}
      {data.user_personas?.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.user_personas.map((persona, i) => (
            <Card key={i} glow>
              <div className="text-sm font-semibold text-white mb-1">{persona.name}</div>
              <div className="text-xs text-accent mb-2">{persona.role}</div>
              <div className="text-xs text-text-muted space-y-1">
                <div><span className="text-white/70">Goal:</span> {persona.goal}</div>
                <div><span className="text-white/70">Frustration:</span> {persona.frustration}</div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Psychographics */}
      {data.psychographics && (
        <Card>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Psychographics</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <div className="text-white/70 mb-1.5">Pain Points</div>
              <ul className="space-y-1">
                {safeArr<string>(data.psychographics.pain_points).map((p, i) => (
                  <li key={i} className="text-text-muted flex gap-2"><span className="text-red-400 shrink-0">*</span> {p}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-white/70 mb-1.5">Values</div>
              <ul className="space-y-1">
                {safeArr<string>(data.psychographics.values).map((v, i) => (
                  <li key={i} className="text-text-muted flex gap-2"><span className="text-emerald-400 shrink-0">*</span> {v}</li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

function CompetitiveSection({ data }: { data: CompetitiveLandscape }) {
  return (
    <div className="space-y-6">
      <p className="text-sm text-text-muted leading-relaxed">{data.summary}</p>

      {/* Direct Competitors */}
      {data.direct_competitors?.length > 0 && (
        <>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Direct Competitors</h4>
          <div className="space-y-3">
            {data.direct_competitors.map((comp, i) => (
              <Card key={i}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="text-sm font-semibold text-white">{comp.name}</span>
                    <span className={`ml-2 text-[10px] px-1.5 py-0.5 rounded ${
                      comp.threat_level === 'high' ? 'bg-red-500/20 text-red-400' :
                      comp.threat_level === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                      'bg-emerald-500/20 text-emerald-400'
                    }`}>{comp.threat_level} threat</span>
                  </div>
                  {comp.market_share_pct != null && (
                    <span className="text-xs text-accent font-medium">{comp.market_share_pct}% share</span>
                  )}
                </div>
                <p className="text-xs text-text-muted mb-3">{comp.description}</p>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <div className="text-emerald-400 mb-1">Strengths</div>
                    <ul className="space-y-0.5">{safeArr<string>(comp.strengths).map((s, j) => <li key={j} className="text-text-muted">+ {s}</li>)}</ul>
                  </div>
                  <div>
                    <div className="text-red-400 mb-1">Weaknesses</div>
                    <ul className="space-y-0.5">{safeArr<string>(comp.weaknesses).map((w, j) => <li key={j} className="text-text-muted">- {w}</li>)}</ul>
                  </div>
                </div>
                {comp.pricing && <div className="mt-2 text-xs text-text-muted">Pricing: <span className="text-white">{comp.pricing}</span></div>}
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Competitive Advantages & Gaps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.competitive_advantages?.length > 0 && (
          <Card glow>
            <h4 className="text-xs font-semibold text-accent uppercase tracking-wider mb-2">Your Advantages</h4>
            <ul className="space-y-1.5">{data.competitive_advantages.map((a, i) => <li key={i} className="text-xs text-text-muted flex gap-2"><span className="text-accent shrink-0">+</span> {a}</li>)}</ul>
          </Card>
        )}
        {data.market_gaps?.length > 0 && (
          <Card>
            <h4 className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2">Market Gaps</h4>
            <ul className="space-y-1.5">{data.market_gaps.map((g, i) => <li key={i} className="text-xs text-text-muted flex gap-2"><span className="text-amber-400 shrink-0">*</span> {g}</li>)}</ul>
          </Card>
        )}
      </div>
    </div>
  )
}

function MetricsSection({ data }: { data: MarketMetrics }) {
  const tamSamSom = [
    { label: 'TAM', value: data.tam?.value_usd || 0, color: 'rgba(0, 229, 255, 0.3)' },
    { label: 'SAM', value: data.sam?.value_usd || 0, color: 'rgba(0, 229, 255, 0.6)' },
    { label: 'SOM', value: data.som?.value_usd || 0, color: '#00E5FF' },
  ]

  return (
    <div className="space-y-6">
      {/* TAM/SAM/SOM Cards */}
      <div className="grid grid-cols-3 gap-4">
        {tamSamSom.map((item) => (
          <Card key={item.label} glow={item.label === 'SOM'}>
            <div className="text-xs text-text-muted uppercase mb-1">{item.label}</div>
            <div className="text-xl font-bold text-white">{formatUSD(item.value)}</div>
          </Card>
        ))}
      </div>

      {/* TAM > SAM > SOM funnel bar */}
      <Card>
        <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Market Funnel</h4>
        <BarChart items={tamSamSom.map(t => ({ label: t.label, value: t.value, color: t.color }))} />
        <div className="mt-4 space-y-2 text-xs text-text-muted">
          {data.tam?.description && <div><span className="text-white/70">TAM:</span> {data.tam.description}</div>}
          {data.sam?.description && <div><span className="text-white/70">SAM:</span> {data.sam.description}</div>}
          {data.som?.description && <div><span className="text-white/70">SOM:</span> {data.som.description}</div>}
        </div>
      </Card>

      {/* Growth & Maturity */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <div className="text-xs text-text-muted uppercase mb-1">Growth Rate</div>
          <div className="text-2xl font-bold text-accent">{data.growth_rate_pct}%</div>
          <div className="text-xs text-text-muted mt-0.5">{data.growth_trend}</div>
        </Card>
        <Card>
          <div className="text-xs text-text-muted uppercase mb-1">Maturity</div>
          <div className="text-lg font-bold text-white capitalize">{data.market_maturity}</div>
        </Card>
      </div>

      {/* Industry Trends */}
      {data.industry_trends?.length > 0 && (
        <Card>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Industry Trends</h4>
          <div className="space-y-2">
            {data.industry_trends.map((t, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`shrink-0 mt-0.5 w-2 h-2 rounded-full ${
                  t.direction === 'positive' ? 'bg-emerald-400' :
                  t.direction === 'negative' ? 'bg-red-400' : 'bg-amber-400'
                }`} />
                <div>
                  <span className="text-white font-medium">{t.trend}</span>
                  <span className="text-text-muted"> — {t.impact}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Key Stats */}
      {data.key_stats?.length > 0 && (
        <Card>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Key Statistics</h4>
          <div className="grid grid-cols-2 gap-3">
            {data.key_stats.map((stat, i) => (
              <div key={i} className="bg-white/5 rounded-lg px-3 py-2">
                <div className="text-sm font-semibold text-white">{stat.value}</div>
                <div className="text-[10px] text-text-muted">{stat.label}</div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function RevenueSection({ data }: { data: RevenueProjections }) {
  const scenarios = data.scenarios
  const scenarioColors = {
    best_case: '#10B981',
    likely_case: '#00E5FF',
    worst_case: '#EF4444',
  }

  const years = ['year_1', 'year_2', 'year_3'] as const

  // Build comparison bars for revenue by year
  const revenueByYear = years.map((yr, idx) => ({
    year: `Year ${idx + 1}`,
    best: scenarios?.best_case?.[yr]?.revenue || 0,
    likely: scenarios?.likely_case?.[yr]?.revenue || 0,
    worst: scenarios?.worst_case?.[yr]?.revenue || 0,
  }))

  const maxRevenue = Math.max(...revenueByYear.map(r => r.best), 1)

  return (
    <div className="space-y-6">
      {/* Pricing Model */}
      <Card glow>
        <div className="text-xs text-text-muted uppercase mb-1">Recommended Pricing Model</div>
        <div className="text-lg font-bold text-accent capitalize">{data.pricing_model}</div>
        {data.break_even_months && (
          <div className="text-xs text-text-muted mt-1">Break-even estimate: <span className="text-white">{data.break_even_months} months</span></div>
        )}
      </Card>

      {/* Pricing Tiers */}
      {data.pricing_tiers?.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {data.pricing_tiers.map((tier, i) => (
            <Card key={i}>
              <div className="text-sm font-semibold text-white mb-1">{tier.name}</div>
              <div className="text-2xl font-bold text-accent mb-2">
                {tier.price_monthly === 0 ? 'Free' : `$${tier.price_monthly}/mo`}
              </div>
              <div className="text-[10px] text-text-muted uppercase mb-2">{tier.target_segment}</div>
              <ul className="space-y-1">
                {safeArr<string>(tier.features).map((f, j) => <li key={j} className="text-xs text-text-muted">* {f}</li>)}
              </ul>
            </Card>
          ))}
        </div>
      )}

      {/* Revenue Comparison Chart */}
      <Card>
        <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-4">3-Year Revenue Projections</h4>
        <div className="space-y-4">
          {revenueByYear.map((yr) => (
            <div key={yr.year}>
              <div className="text-xs text-white font-medium mb-2">{yr.year}</div>
              <div className="space-y-1.5">
                {(['best', 'likely', 'worst'] as const).map(scenario => (
                  <div key={scenario} className="flex items-center gap-3">
                    <span className="text-[10px] text-text-muted w-12 shrink-0 capitalize">{scenario === 'best' ? 'Best' : scenario === 'likely' ? 'Likely' : 'Worst'}</span>
                    <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                          width: `${(yr[scenario] / maxRevenue) * 100}%`,
                          backgroundColor: scenarioColors[`${scenario}_case` as keyof typeof scenarioColors],
                        }}
                      />
                    </div>
                    <span className="text-xs text-white font-medium w-16 text-right shrink-0">{formatUSD(yr[scenario])}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Scenario Details */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {(['best_case', 'likely_case', 'worst_case'] as const).map(key => {
          const scenario = scenarios?.[key]
          if (!scenario) return null
          const label = key === 'best_case' ? 'Best Case' : key === 'likely_case' ? 'Likely Case' : 'Worst Case'
          const color = scenarioColors[key]
          return (
            <Card key={key}>
              <div className="text-sm font-semibold mb-2" style={{ color }}>{label}</div>
              <div className="space-y-2 text-xs">
                {years.map((yr, idx) => {
                  const d = scenario[yr]
                  return d ? (
                    <div key={yr} className="bg-white/5 rounded-lg px-3 py-2">
                      <div className="text-text-muted mb-1">Year {idx + 1}</div>
                      <div className="grid grid-cols-2 gap-1">
                        <div>Revenue: <span className="text-white">{formatUSD(d.revenue)}</span></div>
                        <div>MRR: <span className="text-white">{formatUSD(d.mrr)}</span></div>
                        <div>Users: <span className="text-white">{formatNumber(d.users)}</span></div>
                        <div>Paying: <span className="text-white">{formatNumber(d.paying_users)}</span></div>
                      </div>
                    </div>
                  ) : null
                })}
              </div>
              {safeArr<string>(scenario.assumptions).length > 0 && (
                <div className="mt-2 text-[10px] text-text-muted">
                  {safeArr<string>(scenario.assumptions).map((a, i) => <div key={i}>* {a}</div>)}
                </div>
              )}
            </Card>
          )
        })}
      </div>

      {/* Drivers & Risks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.key_revenue_drivers?.length > 0 && (
          <Card>
            <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">Revenue Drivers</h4>
            <ul className="space-y-1">{data.key_revenue_drivers.map((d, i) => <li key={i} className="text-xs text-text-muted flex gap-2"><span className="text-emerald-400 shrink-0">+</span> {d}</li>)}</ul>
          </Card>
        )}
        {data.revenue_risks?.length > 0 && (
          <Card>
            <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">Revenue Risks</h4>
            <ul className="space-y-1">{data.revenue_risks.map((r, i) => <li key={i} className="text-xs text-text-muted flex gap-2"><span className="text-red-400 shrink-0">!</span> {r}</li>)}</ul>
          </Card>
        )}
      </div>
    </div>
  )
}

function StrategySection({ data }: { data: MarketingStrategies }) {
  const donutColors = ['#00E5FF', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

  return (
    <div className="space-y-6">
      <p className="text-sm text-text-muted leading-relaxed">{data.summary}</p>

      {/* Budget Overview */}
      {data.budget_summary && (
        <Card glow>
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="text-xs text-text-muted uppercase mb-1">Monthly Budget Range</div>
              <div className="text-xl font-bold text-white">
                {formatUSD(data.budget_summary.monthly_min_usd)} &mdash; {formatUSD(data.budget_summary.monthly_max_usd)}
              </div>
            </div>
          </div>
          {data.budget_summary.allocation?.length > 0 && (
            <DonutChart
              segments={data.budget_summary.allocation.map((a, i) => ({
                label: a.category,
                pct: a.pct,
                color: donutColors[i % donutColors.length],
              }))}
            />
          )}
        </Card>
      )}

      {/* Marketing Channels */}
      {data.channels?.length > 0 && (
        <>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Channels</h4>
          <div className="space-y-3">
            {data.channels.map((ch, i) => (
              <Card key={i}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">{ch.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                      ch.priority === 'primary' ? 'bg-accent/20 text-accent' :
                      ch.priority === 'secondary' ? 'bg-amber-500/20 text-amber-400' :
                      'bg-white/10 text-text-muted'
                    }`}>{ch.priority}</span>
                  </div>
                  <div className="text-xs text-text-muted">
                    {formatUSD(ch.budget_monthly_usd)}/mo | CAC: ${ch.expected_cac}
                  </div>
                </div>
                <div className="text-xs text-text-muted mb-2">{ch.timeline}</div>
                <div className="flex flex-wrap gap-1.5">
                  {safeArr<string>(ch.tactics).map((t, j) => (
                    <span key={j} className="text-[10px] bg-white/5 border border-border rounded px-2 py-0.5 text-text-muted">{t}</span>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Launch Strategy */}
      {data.launch_strategy && (
        <Card>
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Launch Playbook</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(['pre_launch', 'launch_week', 'post_launch'] as const).map(phase => {
              const items = data.launch_strategy[phase]
              if (!items?.length) return null
              const labels = { pre_launch: 'Pre-Launch', launch_week: 'Launch Week', post_launch: 'Post-Launch (30-90d)' }
              return (
                <div key={phase}>
                  <div className="text-xs font-medium text-accent mb-2">{labels[phase]}</div>
                  <ul className="space-y-1">
                    {items.map((item, i) => <li key={i} className="text-xs text-text-muted">* {item}</li>)}
                  </ul>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Content Ideas & Partnerships */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.content_ideas?.length > 0 && (
          <Card>
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Content Ideas</h4>
            <div className="space-y-2">
              {data.content_ideas.map((idea, i) => (
                <div key={i} className="text-xs">
                  <span className="text-[10px] bg-white/10 rounded px-1.5 py-0.5 mr-2 text-text-muted">{idea.type}</span>
                  <span className="text-white">{idea.title}</span>
                  <span className="text-text-muted"> — {idea.goal}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
        {data.partnerships?.length > 0 && (
          <Card>
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Partnership Opportunities</h4>
            <div className="space-y-2">
              {data.partnerships.map((p, i) => (
                <div key={i} className="text-xs">
                  <span className="text-[10px] bg-accent/15 rounded px-1.5 py-0.5 mr-2 text-accent">{p.type}</span>
                  <span className="text-text-muted">{p.description}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Streaming progress display
// ---------------------------------------------------------------------------

function GenerationProgress({ progress, currentSection, streamText }: {
  progress: number
  currentSection: string
  streamText: string
}) {
  const sectionLabel = TABS.find(t => t.key === currentSection)?.label || currentSection

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-lg space-y-6">
        {/* Progress bar */}
        <div>
          <div className="flex justify-between text-xs mb-2">
            <span className="text-text-muted">Generating Market Analysis</span>
            <span className="text-accent font-medium">{Math.round(progress * 100)}%</span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        </div>

        {/* Current section */}
        <div className="text-center">
          <div className="text-sm text-white font-medium mb-1">
            Analyzing: {sectionLabel}
          </div>
          <div className="text-xs text-text-muted animate-pulse">
            Claude is researching and generating insights...
          </div>
        </div>

        {/* Live preview of streaming text */}
        {streamText && (
          <Card className="max-h-48 overflow-y-auto">
            <pre className="text-[10px] text-text-muted font-mono whitespace-pre-wrap break-all leading-relaxed">
              {streamText.slice(-600)}
            </pre>
          </Card>
        )}

        {/* Section progress steps */}
        <div className="flex justify-center gap-2">
          {TABS.map((tab) => {
            const sectionIdx = TABS.findIndex(t => t.key === tab.key)
            const currentIdx = TABS.findIndex(t => t.key === currentSection)
            const isDone = sectionIdx < currentIdx
            const isCurrent = tab.key === currentSection
            return (
              <div
                key={tab.key}
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs transition-all ${
                  isDone ? 'bg-emerald-500/20 text-emerald-400' :
                  isCurrent ? 'bg-accent/20 text-accent animate-pulse' :
                  'bg-white/5 text-text-muted'
                }`}
                title={tab.label}
              >
                {isDone ? '\u2713' : tab.icon}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export function MarketAnalysis() {
  const { projectId } = useParams<{ projectId: string }>()
  const [analysis, setAnalysis] = useState<MarketAnalysisData | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('target_market')
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentSection, setCurrentSection] = useState('')
  const [streamText, setStreamText] = useState('')
  const [upgradeDetail, setUpgradeDetail] = useState<EntitlementDetail | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Fetch existing analysis on mount
  useEffect(() => {
    if (!projectId) return
    const fetchAnalysis = async () => {
      setLoading(true)
      try {
        const { data } = await apiClient.get(`/market/${projectId}`)
        setAnalysis(data)
      } catch {
        // 404 = no analysis yet, which is fine
        setAnalysis(null)
      } finally {
        setLoading(false)
      }
    }
    fetchAnalysis()
  }, [projectId])

  // Generate analysis via SSE
  const generate = useCallback(async (forceRegenerate = false) => {
    if (!projectId || generating) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setGenerating(true)
    setProgress(0)
    setCurrentSection('')
    setStreamText('')

    try {
      const token = await getAuthToken()
      const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
      const response = await fetch(`${baseUrl}/market/${projectId}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ force_regenerate: forceRegenerate }),
        signal: controller.signal,
      })

      if (!response.ok) {
        if (response.status === 403) {
          try {
            const body = await response.json()
            const d = body?.detail
            if (d && (d.code === 'project_limit_reached' || d.code === 'feature_limit_reached')) {
              setUpgradeDetail(d as EntitlementDetail)
              return
            }
          } catch { /* not JSON */ }
        }
        throw new Error(`HTTP ${response.status}`)
      }
      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          buffer += decoder.decode() // flush remaining bytes
        } else {
          buffer += decoder.decode(value, { stream: true })
        }
        const lines = buffer.split('\n')
        buffer = done ? '' : (lines.pop() || '')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'section_start') {
              setCurrentSection(data.section)
              setStreamText('')
              if (data.progress != null) setProgress(data.progress)
            } else if (data.type === 'section_token') {
              setStreamText(prev => prev + (data.content || ''))
            } else if (data.type === 'section_complete') {
              if (data.progress != null) setProgress(data.progress)
              // Update the analysis data incrementally
              setAnalysis(prev => {
                const updated = prev ? { ...prev } : {
                  id: '',
                  project_id: projectId,
                  target_market: null,
                  competitive_landscape: null,
                  market_metrics: null,
                  revenue_projections: null,
                  marketing_strategies: null,
                  status: 'generating',
                  error_message: null,
                } as MarketAnalysisData
                ;(updated as unknown as Record<string, unknown>)[data.section] = data.data
                return updated
              })
              setStreamText('')
            } else if (data.type === 'complete') {
              setProgress(1)
              setAnalysis(prev => prev ? { ...prev, status: 'complete' } : prev)
            } else if (data.type === 'error') {
              console.error('Generation error:', data.message)
              setAnalysis(prev => prev ? { ...prev, status: 'error', error_message: data.message } : prev)
            }
          } catch { /* skip malformed lines */ }
        }
        if (done) break
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        console.error('SSE error:', err)
      }
    } finally {
      setGenerating(false)
    }
  }, [projectId, generating])

  const isComplete = analysis?.status === 'complete'
  const hasAnalysis = analysis && (isComplete || analysis.target_market)

  // Export report in selected format
  const [exportOpen, setExportOpen] = useState(false)
  const [exporting, setExporting] = useState(false)
  const exportRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false)
      }
    }
    if (exportOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [exportOpen])

  const exportReport = async (format: string) => {
    if (!projectId) return
    setExporting(true)
    setExportOpen(false)
    try {
      const response = await apiClient.get(`/market/${projectId}/export`, {
        params: { format },
        responseType: 'blob',
      })
      const ext = format === 'docx' ? 'docx' : format === 'txt' ? 'txt' : 'pdf'
      const slug = `market-analysis-${new Date().toISOString().split('T')[0]}`
      downloadBlob(response.data, `${slug}.${ext}`)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar projectId={projectId} />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col h-dvh">
        <TopBar title="Market Analysis" subtitle="AI-powered market research and projections">
          {isComplete && (
            <div className="relative" ref={exportRef}>
              <Button variant="ghost" onClick={() => setExportOpen(!exportOpen)} disabled={exporting}>
                {exporting ? 'Exporting...' : 'Export'}
                <svg className="w-3 h-3 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
              </Button>
              {exportOpen && (
                <div className="absolute right-0 top-full mt-1 w-44 bg-surface border border-border rounded-lg shadow-xl z-50 py-1">
                  {[
                    { id: 'pdf', label: 'PDF Document', icon: '\u{1F4D5}' },
                    { id: 'docx', label: 'Word Document', icon: '\u{1F4D8}' },
                    { id: 'txt', label: 'Plain Text', icon: '\u{1F4C4}' },
                  ].map(fmt => (
                    <button
                      key={fmt.id}
                      onClick={() => exportReport(fmt.id)}
                      className="w-full text-left px-3 py-2 text-xs text-text-muted hover:text-white hover:bg-white/5 flex items-center gap-2 transition-colors"
                    >
                      <span>{fmt.icon}</span>
                      <span>{fmt.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          {isComplete && (
            <Button variant="secondary" onClick={() => generate(true)} disabled={generating}>
              Regenerate
            </Button>
          )}
          {!isComplete && !generating && (
            <Button onClick={() => generate(false)} disabled={generating}>
              Generate Analysis
            </Button>
          )}
        </TopBar>

        {/* Loading state */}
        {loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-sm text-text-muted">Loading...</div>
          </div>
        )}

        {/* Generating state */}
        {!loading && generating && (
          <GenerationProgress
            progress={progress}
            currentSection={currentSection}
            streamText={streamText}
          />
        )}

        {/* Empty state */}
        {!loading && !generating && !hasAnalysis && (
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="text-6xl mb-4">{'\u{1F4CA}'}</div>
            <h2 className="text-lg font-semibold text-white mb-2">No Market Analysis Yet</h2>
            <p className="text-sm text-text-muted mb-6 max-w-md text-center">
              Generate a comprehensive market analysis from your Discovery data. This includes target market profiling,
              competitive analysis, TAM/SAM/SOM metrics, revenue projections, and marketing strategy.
            </p>
            {analysis?.status === 'error' && analysis.error_message && (
              <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2 mb-4 max-w-md">
                {analysis.error_message}
              </div>
            )}
            <Button size="lg" onClick={() => generate(false)}>
              Generate Market Analysis
            </Button>
          </div>
        )}

        {/* Analysis display */}
        {!loading && !generating && hasAnalysis && (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Tab Bar */}
            <div className="border-b border-border bg-surface/30 shrink-0">
              <div className="flex gap-1 px-6 py-2">
                {TABS.map(tab => {
                  const hasData = analysis?.[tab.key]
                  return (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key)}
                      className={`flex items-center gap-2 px-4 py-2 text-xs rounded-lg transition-colors ${
                        activeTab === tab.key
                          ? 'bg-accent/15 text-accent font-medium'
                          : hasData
                          ? 'text-text-muted hover:text-white hover:bg-white/5'
                          : 'text-text-muted/50 hover:text-text-muted hover:bg-white/5'
                      }`}
                    >
                      <span>{tab.icon}</span>
                      <span>{tab.label}</span>
                      {hasData && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
                    </button>
                  )
                })}
                <div className="ml-auto flex items-center">
                  <StatusBadge status={analysis?.status || 'pending'} />
                </div>
              </div>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 pb-20 md:pb-6">
              {activeTab === 'target_market' && analysis?.target_market && (
                <TargetMarketSection data={analysis.target_market as TargetMarket} />
              )}
              {activeTab === 'competitive_landscape' && analysis?.competitive_landscape && (
                <CompetitiveSection data={analysis.competitive_landscape as CompetitiveLandscape} />
              )}
              {activeTab === 'market_metrics' && analysis?.market_metrics && (
                <MetricsSection data={analysis.market_metrics as MarketMetrics} />
              )}
              {activeTab === 'revenue_projections' && analysis?.revenue_projections && (
                <RevenueSection data={analysis.revenue_projections as RevenueProjections} />
              )}
              {activeTab === 'marketing_strategies' && analysis?.marketing_strategies && (
                <StrategySection data={analysis.marketing_strategies as MarketingStrategies} />
              )}

              {/* Empty state for tabs without data */}
              {analysis && !analysis[activeTab] && !generating && (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="text-4xl mb-4 opacity-40">
                    {TABS.find(t => t.key === activeTab)?.icon || '?'}
                  </div>
                  <h3 className="text-lg font-medium text-white mb-2">
                    {TABS.find(t => t.key === activeTab)?.label || 'Section'} Not Available
                  </h3>
                  <p className="text-sm text-text-muted mb-6 max-w-md">
                    {analysis.status === 'error'
                      ? 'This section failed to generate. Try regenerating the full analysis.'
                      : analysis.status === 'complete'
                      ? 'This section was not generated. Regenerate to include it.'
                      : 'This section will be generated when the analysis runs.'}
                  </p>
                  {(analysis.status === 'error' || analysis.status === 'complete') && (
                    <Button variant="secondary" onClick={() => generate(true)} disabled={generating}>
                      Regenerate Analysis
                    </Button>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <EntitlementLimitModal detail={upgradeDetail} onClose={() => setUpgradeDetail(null)} />
    </div>
  )
}
