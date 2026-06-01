/**
 * BlogChrome — shared public nav, conversion CTA, and footer for the blog
 * pages. Mirrors the standalone public-page shell used by PrivacyPolicy.
 * @module components/blog/BlogChrome
 */
import { Link } from 'react-router-dom'

/** Conversion call-to-action — the whole point of the blog as a funnel. */
export function BlogCTA() {
  return (
    <section className="my-12 p-8 rounded-2xl border border-accent/30 bg-accent/[0.05] text-center">
      <h2 className="text-xl font-black text-white mb-2">Ready to turn your idea into a plan?</h2>
      <p className="text-sm text-text-muted mb-5 max-w-md mx-auto leading-relaxed">
        Ide/AI takes you from a rough idea to an export-ready design kit in one session — a
        prioritized feature breakdown, a tech-stack recommendation, and platform-ready prompts.
      </p>
      <Link
        to="/sign-up"
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-accent text-background text-sm font-semibold hover:bg-accent/90 transition-colors"
      >
        Try Ide/AI free →
      </Link>
    </section>
  )
}

export function BlogFooter() {
  return (
    <footer className="py-8 px-4 border-t border-white/10">
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        <span className="text-xs text-text-muted">
          &copy; {new Date().getFullYear()}{' '}
          <a href="https://vybeco.de" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">VybeCode LTD</a>. All rights reserved.
        </span>
        <div className="flex items-center gap-5 text-xs text-text-muted">
          <Link to="/blog" className="hover:text-white transition-colors">Blog</Link>
          <Link to="/privacy" className="hover:text-white transition-colors">Privacy</Link>
          <Link to="/terms" className="hover:text-white transition-colors">Terms</Link>
          <Link to="/" className="hover:text-white transition-colors">Home</Link>
        </div>
      </div>
    </footer>
  )
}
