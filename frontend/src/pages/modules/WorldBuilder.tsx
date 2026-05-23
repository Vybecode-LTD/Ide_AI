/**
 * WorldBuilder — Creative Writing module page.
 * Setting, characters, and plot structure for narrative projects.
 * @module pages/modules/WorldBuilder
 */
import { useParams } from 'react-router-dom'
import { Sidebar } from '../../components/layout/Sidebar'

export function WorldBuilder() {
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <div className="flex min-h-screen bg-background text-white">
      <Sidebar projectId={projectId} />
      <main className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1">
        <div className="max-w-5xl mx-auto px-4 py-8">
          <h1 className="text-2xl font-bold mb-2">World Builder</h1>
          <p className="text-text-muted text-sm mb-8">
            Define settings, characters, and plot structure. Coming soon.
          </p>
          <div className="rounded-xl border border-border bg-surface p-8 text-center text-text-muted">
            World-building tools will appear here.
          </div>
        </div>
      </main>
    </div>
  )
}
