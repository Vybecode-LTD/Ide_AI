/**
 * TermsOfService — Public legal page.
 * @module pages/TermsOfService
 */
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'

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

export function TermsOfService() {
  return (
    <div className="min-h-screen bg-background text-white">
      <Helmet>
        <title>Terms of Service — Ide/AI</title>
        <meta name="description" content="Ide/AI terms of service — your rights and responsibilities when using the platform." />
        <link rel="canonical" href={`${SITE}/terms`} />
      </Helmet>

      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-lg border-b border-white/[0.08]">
        <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/brandmark.png" alt="Ide/AI" className="h-7 w-7 object-contain" />
            <span className="text-base font-black tracking-tight">
              Ide<span className="text-accent">/AI</span>
            </span>
          </Link>
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <Link to="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link
              to="/sign-up"
              className="px-3 py-1.5 rounded-lg bg-accent text-background text-xs font-semibold hover:bg-accent/90 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-3xl mx-auto px-4 py-12 pb-20">
        <div className="mb-8">
          <h1 className="text-3xl font-black mb-2">Terms of Service</h1>
          <p className="text-sm text-text-muted">
            Effective date: {EFFECTIVE_DATE} · {COMPANY}
          </p>
        </div>

        <P>
          These Terms of Service ("Terms") govern your access to and use of the Ide/AI platform
          operated by {COMPANY} ("Ide/AI", "we", "us", or "our") at{' '}
          <a href={SITE} className="text-accent hover:underline">{SITE}</a>. By creating an account
          or using the Service in any way, you agree to be bound by these Terms. If you do not
          agree, do not use the Service.
        </P>

        {/* ─── 1. The Service ───────────────────────────────────── */}
        <H2>1. The Service</H2>
        <P>
          Ide/AI is a cloud-based AI concept development platform. It helps individuals and teams
          transform rough ideas into structured design kits through AI-guided discovery
          conversations, modular planning workflows, market analysis, sprint planning, and
          exportable documentation.
        </P>
        <P>
          We reserve the right to modify, suspend, or discontinue any part of the Service at any
          time with reasonable notice. We will not be liable to you or any third party for any such
          modification, suspension, or discontinuation.
        </P>

        {/* ─── 2. Eligibility ───────────────────────────────────── */}
        <H2>2. Eligibility</H2>
        <P>
          You must be at least 16 years old to use the Service. By using the Service, you
          represent that you are at least 16 and that you have the legal capacity to enter into a
          binding agreement. If you are using the Service on behalf of an organisation, you
          represent that you are authorised to bind that organisation to these Terms.
        </P>

        {/* ─── 3. Accounts ──────────────────────────────────────── */}
        <H2>3. Account Registration and Security</H2>
        <P>
          You must create an account to access the Service. You agree to provide accurate, current,
          and complete information and to keep it updated. You are responsible for maintaining the
          confidentiality of your account credentials and for all activity that occurs under your
          account. Notify us immediately at{' '}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-accent hover:underline">
            {CONTACT_EMAIL}
          </a>{' '}
          if you suspect unauthorised access.
        </P>

        {/* ─── 4. Subscriptions and Billing ─────────────────────── */}
        <H2>4. Subscriptions and Billing</H2>

        <H3>4.1 Plans</H3>
        <P>
          Ide/AI offers a free tier and paid subscription plans (Basic and Pro). Feature availability
          varies by plan and is described on the pricing page.
        </P>

        <H3>4.2 Billing</H3>
        <P>
          Paid subscriptions are billed in advance on a monthly or annual basis through Stripe.
          By providing payment information, you authorise us to charge the applicable fees to your
          payment method on a recurring basis. All prices are in USD unless otherwise stated.
        </P>

        <H3>4.3 Cancellation</H3>
        <P>
          You may cancel your subscription at any time from your account settings. Cancellation
          takes effect at the end of your current billing period. You will retain access to paid
          features until the period ends. We do not provide refunds for partial billing periods
          except where required by applicable law.
        </P>

        <H3>4.4 Price Changes</H3>
        <P>
          We may change subscription prices with at least 30 days' notice. Continued use of the
          Service after the price change takes effect constitutes acceptance of the new price.
        </P>

        {/* ─── 5. Device Access and File Operations ─────────────── */}
        <H2>5. Device Access and File Operations</H2>

        <Callout>
          <p className="font-semibold text-accent mb-2">
            Ide/AI does not access your computer or local files — under any circumstances.
          </p>
          <p>
            Ide/AI operates entirely as a cloud-based service delivered through your web browser.
            We make no claim to and take no access of your local device, filesystem, installed
            applications, or any other local resource beyond what is explicitly described in
            Sections 5.1–5.3 below.
          </p>
        </Callout>

        <H3>5.1 File Export</H3>
        <P>
          The Service allows you to export your project data as an{' '}
          <code className="text-accent">.ideai</code> file — Ide/AI's proprietary project format.
          Export is initiated by you, performed through your browser's standard download mechanism,
          and delivered to a location of your choosing on your device. We do not retain a separate
          copy of the exported file beyond what is already stored as your project data in our
          systems.
        </P>

        <H3>5.2 File Import</H3>
        <P>
          The Service allows you to import a previously exported{' '}
          <code className="text-accent">.ideai</code> file to restore or migrate a project. Import
          is initiated by you through a browser file picker dialog. Only the specific file you
          select is transmitted to our servers. Your browser's security model enforces this: we
          have no technical means of accessing any other file, directory, or resource on your
          device. Any attempt to request broader filesystem access would be blocked by the browser
          and is not something we will ever do.
        </P>

        <H3>5.3 Third-Party Integration Actions</H3>
        <P>
          If you choose to connect a third-party service (such as Notion, Trello, or Linear) to
          your Ide/AI account, we will:
        </P>
        <Ul>
          <Li>Present a clear, plain-language description of exactly what data will be read from or written to that service.</Li>
          <Li>Require your explicit confirmation before performing any action.</Li>
          <Li>Perform only the specific actions you have authorised.</Li>
          <Li>Provide a straightforward mechanism to revoke access at any time from your account settings.</Li>
        </Ul>

        <H3>5.4 Absolute Prohibitions</H3>
        <P>
          Under no circumstances will we, and you have our commitment that we will never:
        </P>
        <Ul>
          <Li>Scan, read, index, or transmit files or directories from your device without your explicit, file-specific selection.</Li>
          <Li>Access your device's camera, microphone, contacts, location, clipboard, or any other browser-controlled permission without a clear, in-context request and your explicit grant.</Li>
          <Li>Install software, browser extensions, service workers intended for data collection, or background processes of any kind on your device.</Li>
          <Li>Perform actions on third-party services connected to your account without your explicit, per-action or per-session consent.</Li>
          <Li>Access any file format other than <code className="text-accent">.ideai</code> files that you have explicitly chosen to import through the file picker.</Li>
        </Ul>

        {/* ─── 6. User Content ──────────────────────────────────── */}
        <H2>6. User Content and Ownership</H2>

        <H3>6.1 Your Content is Yours</H3>
        <P>
          You retain full ownership of all content you create, upload, or generate using the
          Service — including project descriptions, concept sheets, design blocks, prompts, and
          exported files. We make no claim to ownership of your intellectual property.
        </P>

        <H3>6.2 Licence to Operate the Service</H3>
        <P>
          By using the Service, you grant us a limited, non-exclusive, royalty-free licence to
          store, process, and transmit your content solely as necessary to provide the Service to
          you. This licence does not permit us to use your content for any other purpose, including
          training AI models.
        </P>

        <H3>6.3 AI-Generated Content</H3>
        <P>
          Content generated by the AI on your behalf (concept sheets, design recommendations,
          market analysis, etc.) is provided to you and owned by you, subject to any applicable
          terms from Anthropic. We make no warranty that AI-generated content is accurate,
          complete, or fit for any particular purpose. You are responsible for reviewing and
          validating any AI output before acting on it.
        </P>

        {/* ─── 7. Acceptable Use ────────────────────────────────── */}
        <H2>7. Acceptable Use</H2>
        <P>You agree not to use the Service to:</P>
        <Ul>
          <Li>Violate any applicable law or regulation.</Li>
          <Li>Infringe the intellectual property, privacy, or other rights of any third party.</Li>
          <Li>Upload or generate content that is unlawful, harmful, threatening, abusive, harassing, defamatory, or otherwise objectionable.</Li>
          <Li>Attempt to probe, scan, or test the vulnerability of the Service or circumvent any security or access controls.</Li>
          <Li>Reverse-engineer, decompile, or otherwise attempt to derive the source code of the Service.</Li>
          <Li>Use automated tools (bots, scrapers, crawlers) to access the Service without our prior written permission.</Li>
          <Li>Resell or sublicense the Service without our prior written permission.</Li>
          <Li>Impersonate another person or entity or misrepresent your affiliation.</Li>
        </Ul>
        <P>
          We reserve the right to suspend or terminate accounts that violate these rules, with or
          without notice depending on the severity of the violation.
        </P>

        {/* ─── 8. Intellectual Property ─────────────────────────── */}
        <H2>8. Intellectual Property</H2>
        <P>
          The Ide/AI platform — including its software, design, user interface, trademarks, logos,
          and documentation — is the property of {COMPANY} and is protected by copyright,
          trademark, and other intellectual property laws. Nothing in these Terms grants you any
          right to use our trademarks, logos, or branding without our prior written consent.
        </P>

        {/* ─── 9. Privacy ───────────────────────────────────────── */}
        <H2>9. Privacy</H2>
        <P>
          Your use of the Service is also governed by our{' '}
          <Link to="/privacy" className="text-accent hover:underline">
            Privacy Policy
          </Link>
          , which is incorporated into these Terms by reference. Please read it carefully — it
          explains in detail what data we collect, how we use it, and your rights over it.
        </P>

        {/* ─── 10. Disclaimers ──────────────────────────────────── */}
        <H2>10. Disclaimer of Warranties</H2>
        <P>
          THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
          EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY,
          FITNESS FOR A PARTICULAR PURPOSE, TITLE, OR NON-INFRINGEMENT.
        </P>
        <P>
          We do not warrant that the Service will be uninterrupted, error-free, or entirely secure.
          We do not warrant the accuracy, completeness, or usefulness of any AI-generated content.
          You use the Service at your own risk.
        </P>

        {/* ─── 11. Limitation of Liability ──────────────────────── */}
        <H2>11. Limitation of Liability</H2>
        <P>
          TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, {COMPANY.toUpperCase()} AND ITS
          DIRECTORS, EMPLOYEES, AND AGENTS SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL,
          SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES — INCLUDING LOSS OF PROFITS, DATA, GOODWILL,
          OR BUSINESS OPPORTUNITIES — ARISING OUT OF OR RELATED TO YOUR USE OF THE SERVICE, EVEN
          IF WE HAVE BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
        </P>
        <P>
          OUR TOTAL AGGREGATE LIABILITY TO YOU FOR ANY CLAIMS ARISING UNDER THESE TERMS SHALL NOT
          EXCEED THE GREATER OF (A) THE AMOUNT YOU PAID TO US IN THE 12 MONTHS PRECEDING THE CLAIM
          OR (B) £100 GBP.
        </P>

        {/* ─── 12. Indemnification ──────────────────────────────── */}
        <H2>12. Indemnification</H2>
        <P>
          You agree to defend, indemnify, and hold harmless {COMPANY} and its officers, directors,
          employees, and agents from and against any claims, damages, losses, liabilities, costs,
          and expenses (including reasonable legal fees) arising out of or related to: (a) your
          use of the Service; (b) your User Content; (c) your violation of these Terms; or (d) your
          violation of any third-party rights.
        </P>

        {/* ─── 13. Termination ──────────────────────────────────── */}
        <H2>13. Termination</H2>
        <P>
          You may close your account at any time from your account settings. We may suspend or
          terminate your account at any time if you violate these Terms, or for any other reason
          with reasonable notice. Upon termination, your right to use the Service ceases immediately.
          We will handle your data in accordance with our Privacy Policy.
        </P>

        {/* ─── 14. Governing Law ────────────────────────────────── */}
        <H2>14. Governing Law and Dispute Resolution</H2>
        <P>
          These Terms are governed by and construed in accordance with the laws of England and
          Wales. Any disputes arising under or in connection with these Terms shall be subject to
          the exclusive jurisdiction of the courts of England and Wales, except where applicable
          consumer protection law grants you the right to bring a claim in your local jurisdiction.
        </P>

        {/* ─── 15. Changes ──────────────────────────────────────── */}
        <H2>15. Changes to These Terms</H2>
        <P>
          We may update these Terms from time to time. When we make material changes, we will
          update the effective date above and notify you by email or by a notice within the Service.
          Continued use of the Service after changes are posted constitutes acceptance of the
          revised Terms. If you do not agree to the changes, you must stop using the Service and
          may close your account.
        </P>

        {/* ─── 16. Entire Agreement ─────────────────────────────── */}
        <H2>16. Entire Agreement</H2>
        <P>
          These Terms, together with our{' '}
          <Link to="/privacy" className="text-accent hover:underline">Privacy Policy</Link>, constitute
          the entire agreement between you and {COMPANY} with respect to the Service and supersede
          all prior agreements and understandings.
        </P>

        {/* ─── 17. Contact ──────────────────────────────────────── */}
        <H2>17. Contact</H2>
        <P>Questions about these Terms? Contact us:</P>
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
            <Link to="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link to="/terms" className="text-accent">Terms of Service</Link>
            <Link to="/" className="hover:text-white transition-colors">Home</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
