/**
 * project.ts — Project-related type definitions.
 * @module types/project
 */

export interface Project {
  id: string
  user_id: string
  name: string
  description?: string
  platform: string
  audience: string
  complexity: string
  tone: string
  accent_color: string
  pathway_id: string
  ai_partner_style: string
  primary_category?: string | null
  secondary_category?: string | null
  pathway_locked?: boolean
  /**
   * Discovery flow version.
   * - 'v1': legacy state-machine Discovery + per-module sessions (pre-2026-05-23 projects + template-created projects)
   * - 'v2': unified Discovery prompt targeting all assembled module fields, terminating at the Design Kit
   * Backend default is 'v2'; existing rows backfilled to 'v1' in migration 029.
   */
  flow_version?: 'v1' | 'v2'
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  platform: string
  audience: string
  complexity: string
  tone: string
  description?: string
  accent_color?: string
  pathway_id?: string
  ai_partner_style?: string
}

/** AI Partner metadata returned by GET /meta/partner-styles */
export interface PartnerStyleMeta {
  id: string
  name: string
  icon: string
  color: string
  description: string
  best_for: string[]
  traits: string[]
}
