/**
 * PathwayReview — Full-screen module card stack review page.
 * Users can reorder, add/remove modules, toggle lite/deep, and confirm pathway.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { ModuleCard } from '../components/pathway/ModuleCard'
import { Button } from '../components/ui/Button'
import { useModulePathwayStore } from '../stores/modulePathwayStore'
import apiClient from '../lib/apiClient'
import { extractError } from '../lib/extractError'
import { StageInterlude, PulseBeacon, Whisper } from '../components/tutorial'
import type { ModuleDefinition, PathwayModuleEntry } from '../types/modulePathway'

export function PathwayReview() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const {
    assembledModules,
    loading,
    error,
    categorize,
    assemble,
    fetchPathway,
    updatePathway,
    lockPathway,
  } = useModulePathwayStore()

  const [modules, setModules] = useState<PathwayModuleEntry[]>([])
  const [allModules, setAllModules] = useState<ModuleDefinition[]>([])
  const [showAddPanel, setShowAddPanel] = useState(false)
  const [step, setStep] = useState<'categorizing' | 'assembling' | 'review' | 'locking'>('categorizing')

  // Initialize: categorize → assemble → show review
  useEffect(() => {
    if (!projectId) return

    const init = async () => {
      try {
        // Check if pathway already exists (404 is expected for fresh projects)
        try {
          await fetchPathway(projectId)
          const { pathway: pw } = useModulePathwayStore.getState()
          if (pw && pw.status !== 'pending') {
            // Pathway already locked, redirect to execution
            navigate(`/pathway-execute/${projectId}`)
            return
          }
        } catch (err) {
          // 404 = no pathway yet, proceed with assembly. EVERYTHING ELSE surfaces
          // (including network errors where status is undefined).
          const status = (err as { response?: { status?: number } })?.response?.status
          if (status !== 404) {
            throw err
          }
          // Clear any stale error the store may have set during the 404 path
          useModulePathwayStore.setState({ error: null })
        }

        setStep('categorizing')
        await categorize(projectId)

        setStep('assembling')
        const result = await assemble(projectId)
        setModules(result.modules)

        setStep('review')
      } catch (err) {
        console.error('[PathwayReview] init failed:', err)
        const msg = extractError(err, 'Failed to build your pathway. Please try again.')
        // Surface to user via toast AND store error banner
        toast.error(msg)
        useModulePathwayStore.setState({ error: msg })
        // Advance to review step so the error banner renders + user can retry
        setStep('review')
      }
    }

    init()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  // Fetch full module library for add panel
  useEffect(() => {
    apiClient.get<ModuleDefinition[]>('/meta/modules').then(res => {
      setAllModules(res.data)
    }).catch(() => {})
  }, [])

  // Use assembled modules when they arrive — sync from store to local state.
  // Only runs when store data changes (not on every render).
  const prevAssembledRef = useRef(assembledModules)
  if (assembledModules !== prevAssembledRef.current) {
    prevAssembledRef.current = assembledModules
    if (assembledModules.length > 0 && modules.length === 0) {
      setModules(assembledModules)
    }
  }

  const handleToggleMode = useCallback((moduleId: string, mode: 'lite' | 'deep') => {
    setModules(prev =>
      prev.map(m => m.module_id === moduleId ? { ...m, mode } : m)
    )
  }, [])

  const handleRemove = useCallback((moduleId: string) => {
    setModules(prev => prev.filter(m => m.module_id !== moduleId))
  }, [])

  const handleAddModule = useCallback((moduleDef: ModuleDefinition) => {
    // Don't add duplicates
    if (modules.some(m => m.module_id === moduleDef.id)) return
    const entry: PathwayModuleEntry = {
      module_id: moduleDef.id,
      label: moduleDef.label,
      description: moduleDef.description,
      group: moduleDef.group,
      estimated_time: moduleDef.estimated_time_lite,
      mode: moduleDef.default_mode as 'lite' | 'deep',
      reason: 'Added by user.',
    }
    setModules(prev => [...prev, entry])
    setShowAddPanel(false)
  }, [modules])

  const handleMoveUp = useCallback((index: number) => {
    if (index === 0) return
    setModules(prev => {
      const next = [...prev]
      ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
      return next
    })
  }, [])

  const handleMoveDown = useCallback((index: number) => {
    setModules(prev => {
      if (index >= prev.length - 1) return prev
      const next = [...prev]
      ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
      return next
    })
  }, [])

  const handleConfirm = async () => {
    if (!projectId) return
    setStep('locking')

    const moduleIds = modules.map(m => m.module_id)
    const settings: Record<string, string> = {}
    for (const m of modules) {
      settings[m.module_id] = m.mode
    }

    try {
      await updatePathway(projectId, moduleIds, settings)
      await lockPathway(projectId)
      // Verify the lock actually succeeded — store sets `error` on failure
      const { error: lockErr, pathway } = useModulePathwayStore.getState()
      if (lockErr || !pathway || pathway.status === 'pending') {
        throw new Error(lockErr || 'Pathway did not lock — please try again.')
      }
      navigate(`/pathway-execute/${projectId}`)
    } catch (err) {
      console.error('[PathwayReview] lock failed:', err)
      const msg = extractError(err, 'Could not lock the pathway. Please try again.')
      toast.error(msg)
      useModulePathwayStore.setState({ error: msg })
      setStep('review')
    }
  }

  // Available modules not yet in pathway
  const availableToAdd = allModules.filter(
    m => !modules.some(pm => pm.module_id === m.id)
  )

  // Group available modules
  const groupedAvailable = availableToAdd.reduce<Record<string, ModuleDefinition[]>>((acc, m) => {
    if (!acc[m.group]) acc[m.group] = []
    acc[m.group].push(m)
    return acc
  }, {})

  return (
    <div className="h-dvh bg-background flex overflow-hidden">
      <StageInterlude
        phase="pathway-review"
        message="Your custom module pathway is ready. Reorder, toggle depth, or add modules before locking in."
        stepIndex={1}
        totalSteps={5}
      />
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          {/* Status banner */}
          {step !== 'review' && (
            <div className="max-w-2xl mx-auto text-center py-20">
              <div className="w-10 h-10 mx-auto mb-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <p className="text-text-muted text-sm">
                {step === 'categorizing' && 'Analyzing your concept...'}
                {step === 'assembling' && 'Building your custom pathway...'}
                {step === 'locking' && 'Locking pathway...'}
              </p>
            </div>
          )}

          {step === 'review' && (
            <div className="max-w-2xl mx-auto">
              <div className="mb-6">
                <h1 className="text-xl font-bold text-white mb-1">Your Design Kit Pathway</h1>
                <p className="text-sm text-text-muted">
                  Review, reorder, and customize the modules AI selected for your project.
                  Toggle between Lite (quick) and Deep (thorough) mode per module.
                </p>
              </div>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}

              {/* Module cards */}
              <div className="space-y-3 mb-6">
                {modules.map((mod, i) => (
                  <div key={mod.module_id} className="flex items-start gap-2">
                    {/* Reorder buttons */}
                    <div className="flex flex-col gap-0.5 pt-4">
                      <button
                        type="button"
                        onClick={() => handleMoveUp(i)}
                        disabled={i === 0}
                        className="text-text-muted hover:text-white disabled:opacity-20 text-xs p-1"
                        aria-label="Move up"
                      >
                        {'▲'}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleMoveDown(i)}
                        disabled={i === modules.length - 1}
                        className="text-text-muted hover:text-white disabled:opacity-20 text-xs p-1"
                        aria-label="Move down"
                      >
                        {'▼'}
                      </button>
                    </div>
                    <div className="flex-1">
                      {i === 0 ? (
                        <Whisper id="pathway:first-card" text="Lite asks 2-3 questions, Deep goes to 6-10">
                          <ModuleCard
                            module={mod}
                            index={i}
                            isEditable
                            onToggleMode={handleToggleMode}
                            onRemove={handleRemove}
                          />
                        </Whisper>
                      ) : (
                        <ModuleCard
                          module={mod}
                          index={i}
                          isEditable
                          onToggleMode={handleToggleMode}
                          onRemove={handleRemove}
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Add module */}
              <div className="mb-8">
                <PulseBeacon id="pathway:add-module">
                  <button
                    type="button"
                    onClick={() => setShowAddPanel(!showAddPanel)}
                    className="w-full py-3 border border-dashed border-white/20 rounded-xl text-sm text-text-muted hover:text-accent hover:border-accent/40 transition-colors"
                  >
                    + Add a module
                  </button>
                </PulseBeacon>

                {showAddPanel && (
                  <div className="mt-3 p-4 rounded-xl border border-white/10 bg-white/[0.02] max-h-80 overflow-y-auto">
                    {Object.entries(groupedAvailable).map(([group, mods]) => (
                      <div key={group} className="mb-4 last:mb-0">
                        <h3 className="text-xs font-medium text-accent/70 mb-2 uppercase tracking-wider">{group}</h3>
                        <div className="space-y-1">
                          {mods.map(m => (
                            <button
                              key={m.id}
                              type="button"
                              onClick={() => handleAddModule(m)}
                              className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-white/[0.05] transition-colors text-left"
                            >
                              <div className="min-w-0">
                                <p className="text-sm text-white truncate">{m.label}</p>
                                <p className="text-[11px] text-text-muted truncate">{m.description}</p>
                              </div>
                              <span className="text-xs text-accent ml-2 flex-shrink-0">Add</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                    {availableToAdd.length === 0 && (
                      <p className="text-xs text-text-muted text-center py-4">All modules are in your pathway.</p>
                    )}
                  </div>
                )}
              </div>

              {/* Confirm button */}
              <div className="sticky bottom-4 flex justify-center">
                <Button
                  onClick={handleConfirm}
                  disabled={loading || modules.length === 0}
                  className="px-8 py-3 text-sm font-semibold"
                >
                  {loading ? 'Locking...' : `Confirm Pathway (${modules.length} modules)`}
                </Button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
