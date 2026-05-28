/**
 * Shared meaningful-value checker for design kit field completion.
 *
 * Used by both DesignKit.tsx (client-side field counting) and Discovery.tsx
 * (proceed gate). Mirrors the backend's `_has_value()` in
 * `backend/app/services/discovery_service.py`.
 */
export function hasMeaningfulValue(value: unknown): boolean {
  if (value === undefined || value === null) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
  return true
}
