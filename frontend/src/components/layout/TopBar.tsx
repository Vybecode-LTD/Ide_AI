/**
 * TopBar — Horizontal header with page title, optional controls,
 * and a mobile-only Clerk UserButton (top-right).
 * @module components/layout/TopBar
 */
import { UserButton } from '@clerk/clerk-react'

interface TopBarProps {
  title?: string
  subtitle?: string
  children?: React.ReactNode
}

export function TopBar({ title, subtitle, children }: TopBarProps) {
  return (
    <header className="h-14 border-b border-border bg-surface/80 backdrop-blur-sm flex items-center justify-between px-3 md:px-6 gap-2 md:gap-3 shrink-0">
      {/* Title — caps width so action chips always get space */}
      <div className="min-w-0 max-w-[40%] md:max-w-none md:flex-1">
        {title && <h1 className="text-sm font-semibold text-white truncate">{title}</h1>}
        {subtitle && <p className="text-xs text-text-muted truncate">{subtitle}</p>}
      </div>
      {/* Actions — horizontally scrollable on mobile so they never overflow */}
      <div className="flex items-center gap-2 md:gap-3 shrink min-w-0 overflow-x-auto md:overflow-visible scrollbar-hidden -mx-1 px-1">
        {children}
        {/* Mobile-only profile badge — always visible at the right */}
        <div className="md:hidden shrink-0">
          <UserButton afterSignOutUrl="/" />
        </div>
      </div>
    </header>
  )
}
