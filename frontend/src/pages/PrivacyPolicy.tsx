/**
 * PrivacyPolicy — Public legal page.
 * @module pages/PrivacyPolicy
 */
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { PublicHeader } from '../components/layout/PublicHeader'

const EFFECTIVE_DATE = 'May 26, 2026'
const COMPANY = 'VybeCode LTD'
const CONTACT_EMAIL = 'support@myide.ai'
const SITE = 'https://myide.ai'

function H2({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-lg font-bold text-white mt-10 mb-3 pb-2 border-b border-white/10">
      {children}
    </h2>
  )
}

function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-base font-semibold text-white/90 mt-6 mb-2">{children}</h3>
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-text-muted leading-relaxed mb-3">{children}</p>
}

function Li({ children }: { children: React.ReactNode }) {
  return (
    <li className="text-sm text-text-muted leading-relaxed flex gap-2">
      <span className="text-accent shrink-0 mt-0.5">–</span>
      <span>{children}</span>
    </li>
  )
}

function Ul({ children }: { children: React.ReactNode }) {
  return <ul className="space-y-1.5 mb-4">{children}</ul>
}

function Callout({ children }: { children: React.ReactNode }) {
  return (
    <div className="my-6 p-5 rounded-xl border border-accent/30 bg-accent/[0.05]">
      <div className="text-sm text-white/90 leading-relaxed space-y-2">{children}</div>
    </div>
  )
}

export function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-background text-white">
      <Helmet>
        <title>Privacy Policy — Ide/AI</title>
        <meta name="description" content="Ide/AI privacy policy — how we collect, use, and protect your data." />
        <link rel="canonical" href={`${SITE}/privacy`} />
      </Helmet>

      {/* Unified public header */}
      <PublicHeader />

      {/* Content */}
      <main className="max-w-3xl mx-auto px-4 py-12 pb-20">
        <div className="mb-8">
          <h1 className="text-3xl font-black mb-2">Privacy Policy</h1>
          <p className="text-sm text-text-muted">
            Effective date: {EFFECTIVE_DATE} · {COMPANY}
          </p>
        </div>

        <P>
          This Privacy Policy describes how {COMPANY} ("<strong className="text-white">Ide/AI</strong>", "we",
          "us", or "our") collects, uses, and protects your information when you use the Ide/AI
          platform at <a href={SITE} className="text-accent hover:underline">{SITE}</a>. By using our
          Service you agree to the practices described here.
        </P>
        <P>
          We take privacy seriously. This document is written to be read, not buried. If you have
          questions, contact us at{' '}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-accent hover:underline">
            {CONTACT_EMAIL}
          </a>.
        </P>

        {/* ─── 1. Information We Collect ─────────────────────────── */}
        <H2>1. Information We Collect</H2>

        <H3>1.1 Account Information</H3>
        <P>
          When you create an account, we collect your name, email address, and (if you use social
          login) limited profile information from your chosen OAuth provider (Google, Microsoft, or
          GitHub). Authentication is handled by Clerk, Inc. — we never see or store your password.
        </P>

        <H3>1.2 Project and Content Data</H3>
        <P>
          We store the content you create inside Ide/AI — project descriptions, concept sheets,
          design blocks, pipeline configurations, sprint plans, module responses, and related
          materials. This is your data. You own it.
        </P>

        <H3>1.3 Billing Information</H3>
        <P>
          If you subscribe to a paid plan, payments are processed by Stripe, Inc. We never see,
          store, or have access to your full card number, CVV, or banking details. Stripe provides
          us only with a customer ID and subscription status.
        </P>

        <H3>1.4 Usage and Technical Data</H3>
        <P>
          We collect standard usage data including pages visited, features used, session duration,
          browser type, operating system, and IP address. This data is used to operate the Service,
          diagnose issues, and understand how the product is used. Google Analytics 4 is used for
          aggregate analytics (see Section 9).
        </P>

        <H3>1.5 Communications</H3>
        <P>
          If you contact us by email or use the Idea Inbox feature, we retain those communications
          to respond to you and improve the Service.
        </P>

        {/* ─── 2. How We Use Your Information ───────────────────── */}
        <H2>2. How We Use Your Information</H2>
        <Ul>
          <Li>To create and manage your account and authenticate you securely.</Li>
          <Li>To provide the core Service — AI-guided discovery, module sessions, and design kit generation.</Li>
          <Li>To process subscription payments and manage billing through Stripe.</Li>
          <Li>To send transactional emails (account verification, password reset, receipts) via Resend.</Li>
          <Li>To monitor for bugs, errors, and abuse, and to improve reliability.</Li>
          <Li>To analyse aggregate, anonymised usage patterns and improve the product.</Li>
          <Li>To comply with legal obligations.</Li>
        </Ul>
        <P>We do not use your data for advertising. We do not build advertising profiles.</P>

        {/* ─── 3. Your Computer and Files ───────────────────────── */}
        <H2>3. Your Computer, Files, and Local Device</H2>

        <Callout>
          <p className="font-semibold text-accent mb-2">
            Ide/AI never accesses your computer, filesystem, or local data — period.
          </p>
          <p>
            Ide/AI is a cloud-based web application that runs entirely inside your browser. We have
            no ability to scan, read, index, or interact with any file, directory, application, or
            system resource on your device except in the strictly limited circumstances described
            below. No software, extension, or background process is ever installed on your device.
          </p>
        </Callout>

        <H3>3.1 File Export</H3>
        <P>
          When you choose to export a project, your browser generates an <code className="text-accent">.ideai</code>{' '}
          file and initiates a standard browser download dialog. The file is transferred to a
          location of your choosing on your device through your browser's normal download mechanism.
          We do not retain a separate copy of the exported file beyond what is already stored as
          your project data in our systems.
        </P>

        <H3>3.2 File Import</H3>
        <P>
          When you choose to import a project file, your browser presents a file picker dialog. You
          select a specific <code className="text-accent">.ideai</code> file — only that file is
          transmitted to our servers. We have no visibility into any other file or directory on your
          device. Your browser's sandboxing enforces this: it is technically impossible for us to
          access anything beyond what you explicitly select.
        </P>

        <H3>3.3 Third-Party Integration Actions</H3>
        <P>
          If you choose to connect an external integration (such as Notion, Trello, or Linear), you
          will be shown a clear description of exactly what data will be read or written before any
          action is performed. Integration actions require your explicit, informed consent. You may
          revoke any integration at any time from your account settings.
        </P>

        <H3>3.4 What We Will Never Do</H3>
        <Ul>
          <Li>Scan, read, or index files or directories on your device.</Li>
          <Li>Access your device's camera, microphone, contacts, location, or any other browser permission not explicitly granted by you.</Li>
          <Li>Install software, browser extensions, service workers for data exfiltration, or background processes.</Li>
          <Li>Access any file format other than <code className="text-accent">.ideai</code> files that you explicitly choose to import.</Li>
          <Li>Perform any action on a connected third-party service without your explicit consent and awareness.</Li>
        </Ul>

        {/* ─── 4. AI Processing ─────────────────────────────────── */}
        <H2>4. AI Processing and Anthropic</H2>
        <P>
          The AI features in Ide/AI are powered by Anthropic, Inc.'s Claude API. When you interact
          with the AI — during discovery sessions, module sessions, or any AI-generated output —
          relevant portions of your project data and conversation are transmitted to Anthropic's
          servers to generate responses.
        </P>
        <P>
          <strong className="text-white">We never use your data to train AI models.</strong> Anthropic
          processes your inputs under their API terms solely to generate the requested outputs.
          Project content sent to the Anthropic API is not used to train, fine-tune, or improve
          Anthropic's models.
        </P>

        {/* ─── 5. Third-Party Services ──────────────────────────── */}
        <H2>5. Third-Party Services (Subprocessors)</H2>
        <P>We use the following sub-processors to operate the Service:</P>
        <Ul>
          <Li><strong className="text-white">Clerk, Inc.</strong> — Authentication and identity management (email, Google, Microsoft, GitHub login).</Li>
          <Li><strong className="text-white">Stripe, Inc.</strong> — Payment processing and subscription management.</Li>
          <Li><strong className="text-white">Anthropic, Inc.</strong> — AI language model processing for discovery and generation features.</Li>
          <Li><strong className="text-white">Resend, Inc.</strong> — Transactional email delivery (verification, receipts, inbox).</Li>
          <Li><strong className="text-white">Railway Corporation</strong> — Cloud infrastructure hosting (servers and database).</Li>
          <Li><strong className="text-white">Google LLC</strong> — Analytics (Google Analytics 4, aggregate and anonymised).</Li>
        </Ul>
        <P>
          Each of these providers operates under their own privacy policies and data processing
          agreements. We select subprocessors that meet high standards for data security and privacy.
        </P>

        {/* ─── 6. Data Sharing ──────────────────────────────────── */}
        <H2>6. Data Sharing</H2>
        <P>
          <strong className="text-white">We do not sell your personal data.</strong> We do not share
          your personal data with third parties for marketing, advertising, or commercial purposes.
          We share data only:
        </P>
        <Ul>
          <Li>With the subprocessors listed in Section 5, as necessary to operate the Service.</Li>
          <Li>With other users if you explicitly enable project sharing (only the content and settings you choose to share).</Li>
          <Li>When required by applicable law, court order, or governmental authority — in which case we will notify you where legally permitted to do so.</Li>
          <Li>In connection with a business transfer (merger, acquisition, or sale of assets), in which case we will provide notice and your data will remain subject to this Policy.</Li>
        </Ul>

        {/* ─── 7. Data Security ─────────────────────────────────── */}
        <H2>7. Data Security</H2>
        <P>
          All data is encrypted in transit using TLS. Your project data is stored in a PostgreSQL
          database hosted on Railway with access restricted to the application and authorised
          personnel only. OAuth tokens for third-party integrations are encrypted at rest.
        </P>
        <P>
          No system is perfectly secure. We implement industry-standard controls and will notify
          affected users promptly in the event of a confirmed data breach.
        </P>

        {/* ─── 8. Data Retention ────────────────────────────────── */}
        <H2>8. Data Retention</H2>
        <P>
          We retain your account and project data for as long as your account is active. If you
          delete your account, we will delete your personal data and project content within 30 days,
          except where we are required to retain it for legal, tax, or fraud-prevention purposes
          (for example, billing records may be retained for up to 7 years as required by law).
        </P>

        {/* ─── 9. Cookies and Analytics ─────────────────────────── */}
        <H2>9. Cookies and Analytics</H2>
        <P>
          We use strictly necessary session cookies (set by Clerk) to keep you logged in. We use
          Google Analytics 4 to collect anonymised, aggregated data about how visitors use the
          site. GA4 may set cookies on your device. You can opt out of Google Analytics tracking by
          using the{' '}
          <a
            href="https://tools.google.com/dlpage/gaoptout"
            className="text-accent hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Google Analytics Opt-out Browser Add-on
          </a>
          .
        </P>

        {/* ─── 10. Your Rights ──────────────────────────────────── */}
        <H2>10. Your Rights</H2>
        <P>
          Depending on where you are located, you may have the following rights regarding your
          personal data:
        </P>
        <Ul>
          <Li><strong className="text-white">Access</strong> — Request a copy of the personal data we hold about you.</Li>
          <Li><strong className="text-white">Rectification</strong> — Ask us to correct inaccurate data.</Li>
          <Li><strong className="text-white">Erasure</strong> — Request deletion of your personal data ("right to be forgotten").</Li>
          <Li><strong className="text-white">Portability</strong> — Receive your data in a structured, machine-readable format.</Li>
          <Li><strong className="text-white">Restriction</strong> — Ask us to restrict processing of your data in certain circumstances.</Li>
          <Li><strong className="text-white">Objection</strong> — Object to processing based on legitimate interests.</Li>
          <Li><strong className="text-white">Withdraw Consent</strong> — Where processing is based on consent, withdraw it at any time.</Li>
        </Ul>
        <P>
          To exercise any of these rights, email us at{' '}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-accent hover:underline">
            {CONTACT_EMAIL}
          </a>
          . We will respond within 30 days. EU and UK residents may also lodge a complaint with
          their national data protection authority (UK: the{' '}
          <a
            href="https://ico.org.uk"
            className="text-accent hover:underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            Information Commissioner's Office
          </a>
          ).
        </P>

        {/* ─── 11. Children ─────────────────────────────────────── */}
        <H2>11. Children's Privacy</H2>
        <P>
          Ide/AI is not directed at children under the age of 16. We do not knowingly collect
          personal data from anyone under 16. If we become aware that we have collected data from a
          child under 16 without verified parental consent, we will delete it promptly.
        </P>

        {/* ─── 12. Changes ──────────────────────────────────────── */}
        <H2>12. Changes to This Policy</H2>
        <P>
          We may update this Privacy Policy from time to time. When we make material changes, we
          will update the effective date at the top of this page and, where appropriate, notify you
          by email. Continued use of the Service after changes are posted constitutes acceptance of
          the updated Policy.
        </P>

        {/* ─── 13. Contact ──────────────────────────────────────── */}
        <H2>13. Contact</H2>
        <P>
          For privacy questions, data requests, or concerns, contact us at:
        </P>
        <div className="mt-2 p-4 rounded-xl bg-white/[0.04] border border-white/[0.08] text-sm text-text-muted space-y-1">
          <p className="text-white font-semibold">{COMPANY}</p>
          <p>
            Email:{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-accent hover:underline">
              {CONTACT_EMAIL}
            </a>
          </p>
          <p>Website: <a href={SITE} className="text-accent hover:underline">{SITE}</a></p>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-white/10">
        <div className="max-w-3xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-xs text-text-muted">
            &copy; {new Date().getFullYear()} {COMPANY}. All rights reserved.
          </span>
          <div className="flex items-center gap-5 text-xs text-text-muted">
            <Link to="/privacy" className="text-accent">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
            <Link to="/" className="hover:text-white transition-colors">Home</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
