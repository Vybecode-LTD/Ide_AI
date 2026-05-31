/**
 * blogFormat — small formatting helpers for blog UI (kept separate from
 * component files so Fast Refresh / react-refresh stays happy).
 * @module lib/blogFormat
 */

/** Format an ISO timestamp as e.g. "May 31, 2026". Empty string if invalid. */
export function formatBlogDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
}
