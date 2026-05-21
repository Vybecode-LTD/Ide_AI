/**
 * modulePathwayStore.ts — Zustand store for the modular dynamic pathway system.
 * Manages pathway state, module ordering, execution progress, and responses.
 */
import { create } from 'zustand'
import apiClient from '../lib/apiClient'
import type {
  CategorizeResponse,
  ModuleResponseRecord,
  PathwayAssembleResponse,
  PathwayModuleEntry,
  PathwayState,
} from '../types/modulePathway'

interface ModulePathwayStoreState {
  /** Assembled pathway with full module metadata */
  assembledModules: PathwayModuleEntry[]
  /** Persisted pathway state from backend */
  pathway: PathwayState | null
  /** Module response records (completion status per module) */
  moduleResponses: ModuleResponseRecord[]
  /** Currently active module being executed */
  activeModuleId: string | null
  /** Whether all modules are complete */
  pathwayComplete: boolean
  /** Loading state */
  loading: boolean
  /** Error message */
  error: string | null

  /** Categorize the project and get primary/secondary categories */
  categorize: (projectId: string) => Promise<CategorizeResponse>
  /** Assemble the pathway (base stack + enrichment) */
  assemble: (projectId: string) => Promise<PathwayAssembleResponse>
  /** Fetch current pathway state */
  fetchPathway: (projectId: string) => Promise<void>
  /** Update module order and settings */
  updatePathway: (projectId: string, modules: string[], settings: Record<string, string>) => Promise<void>
  /** Lock the pathway and start execution */
  lockPathway: (projectId: string) => Promise<void>
  /** Fetch all module responses for the project */
  fetchResponses: (projectId: string) => Promise<void>
  /** Set the active module */
  setActiveModule: (moduleId: string | null) => void
  /** Check if all modules are complete */
  checkCompletion: () => void
}

export const useModulePathwayStore = create<ModulePathwayStoreState>()((set, get) => ({
  assembledModules: [],
  pathway: null,
  moduleResponses: [],
  activeModuleId: null,
  pathwayComplete: false,
  loading: false,
  error: null,

  categorize: async (projectId: string) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post<CategorizeResponse>(
        `/projects/${projectId}/categorize`
      )
      set({ loading: false })
      return data
    } catch (err) {
      const msg = (err as Error).message || 'Categorization failed'
      set({ loading: false, error: msg })
      throw err
    }
  },

  assemble: async (projectId: string) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.post<PathwayAssembleResponse>(
        `/projects/${projectId}/pathway/assemble`
      )
      set({ assembledModules: data.modules, loading: false })
      return data
    } catch (err) {
      const msg = (err as Error).message || 'Assembly failed'
      set({ loading: false, error: msg })
      throw err
    }
  },

  fetchPathway: async (projectId: string) => {
    set({ loading: true, error: null })
    try {
      const { data } = await apiClient.get<PathwayState>(
        `/projects/${projectId}/pathway`
      )
      set({ pathway: data, loading: false })
      get().checkCompletion()
    } catch (err) {
      set({ loading: false, error: (err as Error).message })
    }
  },

  updatePathway: async (projectId, modules, settings) => {
    try {
      const { data } = await apiClient.patch<PathwayState>(
        `/projects/${projectId}/pathway`,
        { modules, lite_deep_settings: settings }
      )
      set({ pathway: data })
    } catch (err) {
      set({ error: (err as Error).message })
    }
  },

  lockPathway: async (projectId: string) => {
    set({ loading: true })
    try {
      const { data } = await apiClient.post<PathwayState>(
        `/projects/${projectId}/pathway/lock`
      )
      set({ pathway: data, loading: false })
      get().checkCompletion()
    } catch (err) {
      set({ loading: false, error: (err as Error).message })
    }
  },

  fetchResponses: async (projectId: string) => {
    try {
      const { data } = await apiClient.get<ModuleResponseRecord[]>(
        `/modules/${projectId}/responses`
      )
      set({ moduleResponses: data })
      get().checkCompletion()
    } catch { /* ignore */ }
  },

  setActiveModule: (moduleId) => set({ activeModuleId: moduleId }),

  checkCompletion: () => {
    const { pathway, moduleResponses } = get()
    if (!pathway) return
    const allDone = pathway.modules.every(mid =>
      moduleResponses.some(r => r.module_id === mid && (r.status === 'complete' || r.status === 'skipped'))
    )
    set({ pathwayComplete: allDone })
  },
}))
