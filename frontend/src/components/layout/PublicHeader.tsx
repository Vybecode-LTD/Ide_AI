/**
 * PublicHeader — unified top nav for every logged-out page (landing, legal,
 * blog, auth, shared views). One source of truth so all public pages share the
 * same brand bar, links, and CTAs.
 *
 * - `fixed` overlays content (Landing uses this so its hero scrolls under the
 *   bar); the default is `sticky` (sits above content and takes layout space).
 * - `links` overrides the middle nav (defaults to Blog + Pricing). Pages can
 *   pass same-page anchors (`href`) and/or routes (`to`) — Landing passes its
 *   section anchors.
 * @module components/layout/PublicHeader
 */
import { Link } from 'react-router-dom'

export interface PublicNavLink {
  label: string
  /** Internal route (react-router Link). */
  to?: string
  /** Same-page anchor (plain <a>), e.g. "#pricing". */
  href?: string
}

const DEFAULT_LINKS: PublicNavLink[] = [
  { label: 'Features', to: '/#features' },
  { label: 'How It Works', to: '/#how-it-works' },
  { label: 'Pricing', to: '/#pricing' },
  { label: 'Blog', to: '/blog' },
  { label: 'FAQ', to: '/#faq' },
]

interface PublicHeaderProps {
  /** Use fixed positioning (overlays content) instead of sticky. */
  fixed?: boolean
  /** Override the middle nav links (defaults to Blog + Pricing). */
  links?: PublicNavLink[]
}

export function PublicHeader({ fixed = false, links = DEFAULT_LINKS }: PublicHeaderProps) {
  return (
    <header
      className={`${fixed ? 'fixed inset-x-0' : 'sticky'} top-0 z-50 border-b border-border bg-background/80 backdrop-blur-lg`}
    >
      <div className="max-w-6xl mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <img src="/brandmark.png" alt="Ide/AI" className="h-8 w-8 object-contain" />
          <span className="text-xl font-black tracking-tight text-white">
            Ide<span className="text-accent">/AI</span>
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm text-text-muted">
          {links.map((link) =>
            link.to ? (
              <Link key={link.label} to={link.to} className="hover:text-white transition-colors">
                {link.label}
              </Link>
            ) : (
              <a key={link.label} href={link.href} className="hover:text-white transition-colors">
                {link.label}
              </a>
            ),
          )}
        </nav>

        <div className="flex items-center gap-3">
          <Link
            to="/sign-in"
            className="hidden sm:inline text-sm text-text-muted hover:text-white transition-colors"
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
    </header>
  )
}
