/**
 * ChannelMix — Marketing Campaign module page.
 * Channel cards with budget allocation across marketing channels.
 * @module pages/modules/ChannelMix
 */
import { useParams } from 'react-router-dom'
import { Sidebar } from '../../components/layout/Sidebar'

export function ChannelMix() {
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <div className="flex min-h-screen bg-background text-white">
      <Sidebar projectId={projectId} />
      <main className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1">
        <div className="max-w-5xl mx-auto px-4 py-8">
          <h1 className="text-2xl font-bold mb-2">Channel Mix</h1>
          <p className="text-text-muted text-sm mb-8">
            Plan and allocate budget across marketing channels. Coming soon.
          </p>
          <div className="rounded-xl border border-border bg-surface p-8 text-center text-text-muted">
            Channel allocation cards will appear here.
          </div>
        </div>
      </main>
    </div>
  )
}
