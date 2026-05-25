/**
 * Landing — Public marketing page for Ide/AI.
 * Hero, features, how-it-works, pricing, FAQ, and footer.
 * @module pages/Landing
 */
import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import apiClient from '../lib/apiClient'
import { PLANS, type Cycle, type Plan } from '../lib/plans'

/* ── Feature cards ────────────────────────────────────────────── */
const FEATURES = [
  {
    icon: '🧠',
    title: 'Socratic AI Discovery',
    description:
      'Our AI doesn\'t just take orders — it asks the right questions. Through a guided conversation, it uncovers what you really need and builds a complete concept sheet.',
  },
  {
    icon: '🤝',
    title: 'AI Partner Styles',
    description:
      'Choose how your AI collaborates. Pick a Strategist for big-picture thinking, a Challenger to stress-test ideas, a Visionary for moonshots, or three other styles.',
  },
  {
    icon: '🧩',
    title: 'Modular Pathways',
    description:
      'Every project gets a custom module stack based on what you\'re building. A SaaS app gets sprint planners; a cookbook gets recipe templates. No two projects are the same.',
  },
  {
    icon: '📊',
    title: 'Market Analysis',
    description:
      'AI-powered competitive landscape, audience sizing, and positioning insights — built right into your project workflow.',
  },
  {
    icon: '🎯',
    title: 'From Idea to Action Plan',
    description:
      'Go from a vague thought to a structured design kit with concept sheets, design blocks, pipelines, sprint plans, and pitch decks — all AI-generated.',
  },
  {
    icon: '📤',
    title: 'Export Everything',
    description:
      'Take your work anywhere. Export to PDF, Markdown, JSON, or share a live link with collaborators and stakeholders.',
  },
]

/* ── How it works ─────────────────────────────────────────────── */
const STEPS = [
  {
    num: '01',
    title: 'Describe your idea',
    description: 'Type a sentence or pick a template. That\'s all we need to get started.',
  },
  {
    num: '02',
    title: 'AI discovers the details',
    description: 'Your AI partner asks smart questions to fill in the gaps and build a complete concept sheet.',
  },
  {
    num: '03',
    title: 'Custom modules assemble',
    description: 'Based on your concept, a tailored set of design and planning modules is built just for you.',
  },
  {
    num: '04',
    title: 'Execute and export',
    description: 'Work through each module, refine with AI, and export a complete design kit ready for action.',
  },
]

/* ── FAQ ──────────────────────────────────────────────────────── */
const FAQ = [
  {
    q: 'What makes Ide/AI different from other AI tools?',
    a: 'Most AI tools generate a one-shot response. Ide/AI is a structured concept development platform — it guides you through discovery, builds a tailored module pathway, and produces a complete design kit. It\'s not a chatbot; it\'s a co-architect.',
  },
  {
    q: 'Can I try it before paying?',
    a: 'Absolutely. The Free plan lets you create up to 3 projects with access to the core AI discovery engine and concept generation. No credit card required.',
  },
  {
    q: 'What are AI partner styles?',
    a: 'Partner styles change how the AI collaborates with you. A Strategist focuses on feasibility and market fit; a Visionary pushes bold ideas; a Challenger pokes holes in your assumptions. Available on the Pro plan.',
  },
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. Both Basic and Pro plans are billed monthly or yearly. You can cancel at any time from your account settings — no questions asked.',
  },
  {
    q: 'What types of projects can I build?',
    a: 'Anything — software products, mobile apps, creative projects, business plans, educational curricula, marketing campaigns, and more. The AI adapts its modules to whatever you\'re building.',
  },
  {
    q: 'Is my data safe?',
    a: 'Yes. Your projects are private by default, encrypted in transit and at rest. We never use your data to train AI models.',
  },
]

/* ── Animations ───────────────────────────────────────────────── */
const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: 'easeOut' as const },
  }),
}

/* ── Component ────────────────────────────────────────────────── */
export function Landing() {
  const location = useLocation()
  const [cycle, setCycle] = useState<Cycle>('yearly')
  const [openFaq, setOpenFaq] = useState<number | null>(null)
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null)

  // Auto-scroll to pricing when accessed via /pricing
  useEffect(() => {
    if (location.pathname === '/pricing') {
      setTimeout(() => {
        document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })
      }, 300)
    }
  }, [location.pathname])

  const handleCheckout = async (plan: Plan) => {
    if (plan.id === 'free') {
      window.location.href = '/sign-up'
      return
    }
    const priceId = cycle === 'yearly' ? plan.stripePriceYearly : plan.stripePriceMonthly
    if (!priceId) return
    setCheckoutLoading(plan.id)
    try {
      const { data } = await apiClient.post('/billing/checkout', {
        price_id: priceId,
        cycle,
      })
      window.location.href = data.checkout_url
    } catch {
      // Not authenticated — save plan choice and redirect to sign-up
      sessionStorage.setItem('pending_plan', JSON.stringify({ priceId, cycle }))
      window.location.href = '/sign-up'
    } finally {
      setCheckoutLoading(null)
    }
  }

  return (
    <div className="min-h-screen bg-background text-white overflow-x-hidden">
      {/* ─── Nav ─────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 bg-background/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-6xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/brandmark.png" alt="Ide/AI" className="h-9 md:h-11 w-9 md:w-11 object-contain" />
            <span className="ml-2 text-xl md:text-2xl font-black text-white tracking-tight">Ide<span className="text-accent">/AI</span></span>
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm text-text-muted">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/sign-in"
              className="text-sm text-text-muted hover:text-white transition-colors hidden sm:inline"
            >
              Sign In
            </Link>
            <Link
              to="/sign-up"
              className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-accent text-background hover:bg-accent/90 transition-colors shadow-[0_0_20px_rgba(0,229,255,0.15)]"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </nav>

      {/* ─── Hero ────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-20 md:pt-44 md:pb-32 px-4">
        {/* Glow effects */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-accent/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute top-40 left-1/4 w-[300px] h-[300px] bg-purple-500/8 rounded-full blur-[100px] pointer-events-none" />

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={0}
          >
            <img src="/brandmark.png" alt="Ide/AI" className="h-20 md:h-28 w-20 md:w-28 mx-auto mb-6 object-contain drop-shadow-[0_0_30px_rgba(0,229,255,0.25)]" />
          </motion.div>

          <motion.h1
            className="text-4xl md:text-6xl lg:text-7xl font-black leading-[1.1] mb-6"
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={1}
          >
            Turn a <span className="text-orange-400">spark</span> of an idea into a{' '}
            <span className="text-accent">complete design kit</span>
          </motion.h1>

          <motion.p
            className="text-lg md:text-xl text-text-muted max-w-2xl mx-auto mb-10"
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={2}
          >
            Ide/AI is the first AI platform that doesn't just answer — it discovers.
            Through guided conversation, it builds concept sheets, design blocks,
            market analysis, and action plans tailored to whatever you're creating.
          </motion.p>

          <motion.div
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={3}
          >
            <Link
              to="/sign-up"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-lg text-base font-semibold bg-accent text-background hover:bg-accent/90 transition-all shadow-[0_0_30px_rgba(0,229,255,0.2)] hover:shadow-[0_0_40px_rgba(0,229,255,0.3)]"
            >
              Start Building — It's Free
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-lg text-base font-medium text-white/70 hover:text-white border border-white/15 hover:border-white/30 transition-all"
            >
              See How It Works
            </a>
          </motion.div>

          {/* Social proof */}
          <motion.p
            className="mt-10 text-xs text-text-muted"
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            custom={4}
          >
            No credit card required &middot; 3 free projects &middot; Cancel anytime
          </motion.p>
        </div>
      </section>

      {/* ─── "Nothing else like it" banner ───────────────────────── */}
      <section className="py-12 border-y border-white/10 bg-white/[0.04]">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="text-sm md:text-base text-text-muted">
            Other tools give you a chatbot. <span className="text-white font-semibold">Ide/AI gives you a co-architect.</span>{' '}
            There's nothing else out there that dynamically assembles custom AI modules,
            adapts its collaboration style to your needs, and produces structured, actionable design kits
            — all from a single sentence.
          </p>
        </div>
      </section>

      {/* ─── Features ────────────────────────────────────────────── */}
      <section id="features" className="py-20 md:py-28 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            className="text-center mb-14"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-80px' }}
            variants={fadeUp}
          >
            <h2 className="text-3xl md:text-4xl font-black mb-4">
              Built different, by design
            </h2>
            <p className="text-text-muted max-w-xl mx-auto">
              Every feature exists to save you time, cut costs, and turn vague ideas into things you can actually build.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                className="group p-6 rounded-xl border border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] hover:border-white/15 transition-all"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-40px' }}
                variants={fadeUp}
                custom={i}
              >
                <span className="text-3xl mb-4 block">{f.icon}</span>
                <h3 className="text-base font-bold mb-2">{f.title}</h3>
                <p className="text-sm text-text-muted leading-relaxed">{f.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Cost & Time Savings ─────────────────────────────────── */}
      <section className="py-16 bg-white/[0.04] border-y border-white/10 px-4">
        <div className="max-w-5xl mx-auto">
          <motion.div
            className="text-center mb-12"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
          >
            <h2 className="text-3xl md:text-4xl font-black mb-4">
              Save <span className="text-accent">weeks</span> of work. Save <span className="text-accent">thousands</span> of dollars.
            </h2>
            <p className="text-text-muted max-w-2xl mx-auto">
              What used to require a team of consultants, designers, and researchers
              now happens in a single guided session.
            </p>
          </motion.div>

          <div className="grid sm:grid-cols-3 gap-6">
            {[
              { stat: '10x', label: 'Faster than manual concept development', sub: 'From weeks to minutes' },
              { stat: '$5K+', label: 'Saved vs hiring consultants', sub: 'Per project, on average' },
              { stat: '60+', label: 'Templates across 6 categories', sub: 'Ready to customize' },
            ].map((item, i) => (
              <motion.div
                key={item.stat}
                className="text-center p-6 rounded-xl border border-white/[0.08] bg-background/80"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                custom={i}
              >
                <div className="text-4xl md:text-5xl font-black text-accent mb-2">{item.stat}</div>
                <div className="text-sm font-semibold text-white mb-1">{item.label}</div>
                <div className="text-xs text-text-muted">{item.sub}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── How It Works ────────────────────────────────────────── */}
      <section id="how-it-works" className="py-20 md:py-28 px-4">
        <div className="max-w-4xl mx-auto">
          <motion.div
            className="text-center mb-14"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
          >
            <h2 className="text-3xl md:text-4xl font-black mb-4">
              How it works
            </h2>
            <p className="text-text-muted max-w-lg mx-auto">
              Four steps. One idea. A complete design kit.
            </p>
          </motion.div>

          <div className="space-y-6">
            {STEPS.map((step, i) => (
              <motion.div
                key={step.num}
                className="flex gap-5 md:gap-8 items-start p-5 md:p-6 rounded-xl border border-white/[0.08] bg-white/[0.03]"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-40px' }}
                variants={fadeUp}
                custom={i}
              >
                <div className="shrink-0 w-12 h-12 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent text-sm font-black">
                  {step.num}
                </div>
                <div>
                  <h3 className="text-base font-bold mb-1">{step.title}</h3>
                  <p className="text-sm text-text-muted leading-relaxed">{step.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Pricing ─────────────────────────────────────────────── */}
      <section id="pricing" className="py-20 md:py-28 px-4 bg-white/[0.02]">
        <div className="max-w-5xl mx-auto">
          <motion.div
            className="text-center mb-10"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
          >
            <h2 className="text-3xl md:text-4xl font-black mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-text-muted max-w-lg mx-auto mb-8">
              Start free. Upgrade when you're ready. No hidden fees.
            </p>

            {/* Billing toggle */}
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
          </motion.div>

          <div className="grid md:grid-cols-3 gap-5">
            {PLANS.map((plan, i) => (
              <motion.div
                key={plan.id}
                className={`relative flex flex-col rounded-xl border p-6 md:p-7 transition-all ${
                  plan.popular
                    ? 'border-accent/50 bg-accent/[0.05] shadow-[0_0_50px_rgba(0,229,255,0.08)]'
                    : 'border-white/[0.08] bg-white/[0.03]'
                }`}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                custom={i}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[10px] font-bold bg-accent text-background uppercase tracking-wider">
                    Most Popular
                  </div>
                )}

                <div className="mb-5">
                  <h3 className="text-lg font-bold">{plan.name}</h3>
                  <p className="text-xs text-text-muted mt-1">{plan.tagline}</p>
                </div>

                <div className="mb-6">
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-black">
                      ${cycle === 'yearly' ? plan.yearly : plan.monthly}
                    </span>
                    {plan.monthly > 0 && (
                      <span className="text-sm text-text-muted">/ month</span>
                    )}
                  </div>
                  {plan.monthly > 0 && cycle === 'yearly' && (
                    <p className="text-[11px] text-text-muted mt-1">
                      Billed ${plan.yearly * 12}/year &middot;{' '}
                      <span className="text-green-400">
                        Save ${(plan.monthly - plan.yearly) * 12}/yr
                      </span>
                    </p>
                  )}
                  {plan.monthly === 0 && (
                    <p className="text-[11px] text-text-muted mt-1">Free forever</p>
                  )}
                </div>

                {/* Included features */}
                <ul className="space-y-2.5 mb-6 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <svg className="w-4 h-4 mt-0.5 text-accent shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-white/90">{f}</span>
                    </li>
                  ))}
                  {plan.excluded?.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <svg className="w-4 h-4 mt-0.5 text-white/20 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span className="text-white/30">{f}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleCheckout(plan)}
                  disabled={checkoutLoading === plan.id}
                  className={`w-full py-3 rounded-lg text-sm font-semibold transition-all ${
                    plan.popular
                      ? 'bg-accent text-background hover:bg-accent/90 shadow-[0_0_20px_rgba(0,229,255,0.15)]'
                      : 'bg-white/[0.06] text-white border border-white/15 hover:bg-white/10'
                  } disabled:opacity-50`}
                >
                  {checkoutLoading === plan.id ? 'Redirecting...' : plan.cta}
                </button>
              </motion.div>
            ))}
          </div>

          <p className="text-center text-xs text-text-muted mt-8">
            All plans include SSL encryption &middot; 99.9% uptime &middot; Cancel anytime &middot; Payments secured by Stripe
          </p>
        </div>
      </section>

      {/* ─── FAQ ──────────────────────────────────────────────────── */}
      <section id="faq" className="py-20 md:py-28 px-4">
        <div className="max-w-3xl mx-auto">
          <motion.div
            className="text-center mb-12"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
          >
            <h2 className="text-3xl md:text-4xl font-black mb-4">
              Frequently asked questions
            </h2>
          </motion.div>

          <div className="space-y-3">
            {FAQ.map((item, i) => (
              <motion.div
                key={i}
                className="border border-white/[0.08] rounded-xl overflow-hidden"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                variants={fadeUp}
                custom={i * 0.5}
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-white/[0.02] transition-colors"
                >
                  <span className="text-sm font-semibold pr-4">{item.q}</span>
                  <svg
                    className={`w-4 h-4 shrink-0 text-text-muted transition-transform ${
                      openFaq === i ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {openFaq === i && (
                  <div className="px-5 pb-4">
                    <p className="text-sm text-text-muted leading-relaxed">{item.a}</p>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Final CTA ───────────────────────────────────────────── */}
      <section className="py-20 md:py-28 px-4 bg-white/[0.04] border-t border-white/10">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
          >
            <h2 className="text-3xl md:text-4xl font-black mb-4">
              Your next big idea deserves better than a blank page
            </h2>
            <p className="text-text-muted mb-8 max-w-xl mx-auto">
              Join creators, founders, and teams who are using AI to think bigger, move faster, and build smarter.
            </p>
            <Link
              to="/sign-up"
              className="inline-flex items-center gap-2 px-8 py-3.5 rounded-lg text-base font-semibold bg-accent text-background hover:bg-accent/90 transition-all shadow-[0_0_30px_rgba(0,229,255,0.2)]"
            >
              Start Building — It's Free
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ─── Footer ──────────────────────────────────────────────── */}
      <footer className="py-10 px-4 border-t border-white/10">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <img src="/brandmark.png" alt="Ide/AI" className="h-6 w-6 object-contain" />
            <span className="ml-1.5 text-sm font-bold text-white tracking-tight">Ide<span className="text-accent">/AI</span></span>
            <span className="text-xs text-text-muted">&copy; {new Date().getFullYear()} Ide/AI. All rights reserved.</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-text-muted">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
            <Link to="/sign-in" className="hover:text-white transition-colors">Sign In</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
