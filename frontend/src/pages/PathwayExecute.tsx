/**
 * PathwayExecute — Pathway execution hub. Shows all modules with their status.
 * Users click modules to start/resume them.
 */
import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { ModuleCard } from '../components/pathway/ModuleCard'
import { PathwayProgress } from '../components/pathway/PathwayProgress'
import { Button } from '../components/ui/Button'
import { StageInterlude, PulseBeacon } from '../components/tutorial'
import { useModulePathwayStore } from '../stores/modulePathwayStore'
import apiClient from '../lib/apiClient'
import toast from 'react-hot-toast'
import type { PathwayModuleEntry } from '../types/modulePathway'

function getModuleStatus(
  moduleId: string,
  responses: { module_id: string; status: string }[],
): 'pending' | 'active' | 'complete' | 'skipped' {
  const resp = responses.find(r => r.module_id === moduleId)
  if (!resp) return 'pending'
  return resp.status as 'pending' | 'active' | 'complete' | 'skipped'
}

export function PathwayExecute() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const {
    assembledModules,
    pathway,
    moduleResponses,
    pathwayComplete,
    fetchPathway,
    fetchResponses,
    assemble,
  } = useModulePathwayStore()

  useEffect(() => {
    if (!projectId) return
    let cancelled = false

    const init = async () => {
      // v2 projects don't use PathwayExecute — they go straight from
      // creation → Discovery → Design Kit (Phase 5). Redirect any v2
      // project that lands here back to Discovery. Audit H2: defense-
      // in-depth — Library + PathwayReview already redirect v2 away,
      // but a manual URL (/pathway-execute/{v2-pid}) would otherwise
      // open a legacy per-module session that clobbers the v2-populated
      // module_responses.
      try {
        const { data: proj } = await apiClient.get(`/projects/${projectId}`)
        if (proj?.flow_version === 'v2') {
          navigate(`/discovery/${projectId}`, { replace: true })
          return
        }
      } catch {
        // If project fetch fails, fall through to the legacy path —
        // recoverable; user can re-navigate.
      }
      if (cancelled) return

      try {
        await fetchPathway(projectId)
      } catch (err) {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status !== 404) toast.error('Failed to load pathway')
      }
      await fetchResponses(projectId)
      // If we don't have assembled modules with full metadata, re-fetch.
      // Read the store directly — the `assembledModules` closure may be stale.
      if (!cancelled && useModulePathwayStore.getState().assembledModules.length === 0) {
        await assemble(projectId).catch(() => {})
      }
    }

    void init()
    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const handleStartModule = (moduleId: string) => {
    if (!projectId) return
    navigate(`/module-session/${projectId}/${moduleId}`)
  }

  // Build module entries with status
  const moduleEntries: (PathwayModuleEntry & { status: string })[] =
    (pathway?.modules ?? []).map(mid => {
      const assembled = assembledModules.find(m => m.module_id === mid)
      return {
        module_id: mid,
        label: assembled?.label ?? mid,
        description: assembled?.description ?? '',
        group: assembled?.group ?? '',
        estimated_time: assembled?.estimated_time ?? '',
        mode: (pathway?.lite_deep_settings?.[mid] as 'lite' | 'deep') ?? 'lite',
        reason: assembled?.reason ?? '',
        status: getModuleStatus(mid, moduleResponses),
      }
    })

  // Find first incomplete module
  const firstIncomplete = moduleEntries.find(m => m.status === 'pending')

  return (
    <div className="h-dvh bg-background flex overflow-hidden">
      <StageInterlude
        phase="pathway-execute"
        message="Work through each module to build your design kit. Click any module to start."
        stepIndex={2}
        totalSteps={5}
      />
      <Sidebar />
      <div className="flex-1 flex min-w-0">
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar />
          <main className="flex-1 overflow-y-auto p-4 md:p-8">
            <div className="max-w-2xl mx-auto">
              <div className="mb-6">
                <h1 className="text-xl font-bold text-white mb-1">Design Kit Pathway</h1>
                <p className="text-sm text-text-muted">
                  {pathwayComplete
                    ? 'All modules complete! Your design kit is ready for export.'
                    : 'Work through each module to build your design kit.'}
                </p>
              </div>

              {pathwayComplete && (
                <div className="mb-6 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-center">
                  <p className="text-green-400 font-medium text-sm mb-3">Pathway Complete</p>
                  <Button
                    onClick={() => navigate(`/exports/${projectId}`)}
                    className="px-6"
                  >
                    Export Design Kit
                  </Button>
                </div>
              )}

              {/* Continue button */}
              {!pathwayComplete && firstIncomplete && (
                <div className="mb-6">
                  <PulseBeacon id="execute:continue">
                    <Button
                      onClick={() => handleStartModule(firstIncomplete.module_id)}
                      className="w-full py-3"
                    >
                      Continue: {firstIncomplete.label}
                    </Button>
                  </PulseBeacon>
                </div>
              )}

              {/* Module list */}
              <div className="space-y-3 pb-mobile-nav md:pb-0">
                {moduleEntries.map((mod, i) => (
                  <ModuleCard
                    key={mod.module_id}
                    module={mod}
                    index={i}
                    status={mod.status as 'pending' | 'active' | 'complete' | 'skipped'}
                    onStart={handleStartModule}
                  />
                ))}
              </div>
            </div>
          </main>
        </div>

        {/* Desktop sidebar progress */}
        <div className="hidden lg:block w-64 border-l border-white/5 p-4 overflow-y-auto">
          <h3 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">Progress</h3>
          <PathwayProgress
            modules={assembledModules}
            responses={moduleResponses}
            activeModuleId={null}
            onModuleClick={handleStartModule}
          />
        </div>
      </div>
    </div>
  )
}
