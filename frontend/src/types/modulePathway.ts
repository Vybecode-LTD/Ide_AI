/** Types for the modular dynamic pathway system. */

export interface ModuleDefinition {
  id: string
  label: string
  group: string
  description: string
  estimated_time_lite: string
  estimated_time_deep: string
  default_mode: 'lite' | 'deep'
}

export interface ConceptCategory {
  id: string
  label: string
  examples: string[]
  default_modules: string[]
}

export interface PathwayModuleEntry {
  module_id: string
  label: string
  description: string
  group: string
  estimated_time: string
  mode: 'lite' | 'deep'
  reason: string
}

export interface PathwayAssembleResponse {
  modules: PathwayModuleEntry[]
  primary_category: string
  secondary_category: string | null
}

export interface PathwayState {
  id: string
  project_id: string
  modules: string[]
  lite_deep_settings: Record<string, string>
  status: 'pending' | 'active' | 'complete'
  created_at: string
  updated_at: string
}

export interface CategorizeResponse {
  primary_category: string
  secondary_category: string | null
  confidence: number
  reasoning: string
}

export interface ModuleStartResponse {
  module_id: string
  label: string
  question: string
  question_number: number
  total_questions: number
  mode: string
  existing_module?: boolean
  redirect?: string
  already_complete?: boolean
  message?: string
  resumed?: boolean
  messages?: Array<{ role: string; content: string }>
  extracted?: Record<string, unknown>
}

export interface ModuleResponseRecord {
  id: string
  project_id: string
  module_id: string
  responses: Record<string, unknown>
  status: 'pending' | 'active' | 'complete' | 'skipped'
  completed_at: string | null
  created_at: string
}
