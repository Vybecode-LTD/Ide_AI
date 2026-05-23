/**
 * Library — Project library with Explorer-style detail view, .ideai export/import,
 * snapshot version management, and project sharing.
 * @module pages/Library
 */
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Sidebar } from '../components/layout/Sidebar'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ShareDialog } from '../components/sharing/ShareDialog'
import apiClient from '../lib/apiClient'
import { downloadBlob } from '../lib/exportUtils'

interface LibraryProject {
  id: string
  name: string
  description: string | null
  platform: string
  audience: string
  complexity: string
  tone: string
  accent_color: string
  created_at: string
  updated_at: string
  snapshot_count: number
  // Progress metadata
  discovery_stage: string | null
  discovery_message_count: number
  design_confidence: number
  block_count: number
  pathway_status: string | null
  pathway_locked: boolean
  recommended_resume_path: string
}

interface Snapshot {
  id: string
  project_id: string
  name: string
  description: string | null
  version: number
  created_at: string
}

type SortKey = 'name' | 'platform' | 'updated_at' | 'created_at'
type SortDir = 'asc' | 'desc'
type ViewMode = 'list' | 'grid'

export function Library() {
  const [projects, setProjects] = useState<LibraryProject[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [snapshotsLoading, setSnapshotsLoading] = useState(false)
  const [exporting, setExporting] = useState<string | null>(null)
  const [importing, setImporting] = useState(false)
  const [restoring, setRestoring] = useState<string | null>(null)

  // View controls
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [sortKey, setSortKey] = useState<SortKey>('updated_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [search, setSearch] = useState('')

  // Snapshot creation form
  const [showSnapshotForm, setShowSnapshotForm] = useState(false)
  const [snapshotName, setSnapshotName] = useState('')
  const [snapshotDesc, setSnapshotDesc] = useState('')
  const [creatingSnapshot, setCreatingSnapshot] = useState(false)

  // Share dialog
  const [shareOpen, setShareOpen] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchProjects()
  }, [])

  useEffect(() => {
    if (selectedProjectId) {
      fetchSnapshots(selectedProjectId)
    } else {
      setSnapshots([])
    }
  }, [selectedProjectId])

  const fetchProjects = async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get('/library/projects')
      setProjects(data)
    } catch (err) {
      console.error('Failed to fetch library projects:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchSnapshots = async (projectId: string) => {
    setSnapshotsLoading(true)
    try {
      const { data } = await apiClient.get(`/library/${projectId}/snapshots`)
      setSnapshots(data)
    } catch (err) {
      console.error('Failed to fetch snapshots:', err)
    } finally {
      setSnapshotsLoading(false)
    }
  }

  const handleExport = async (projectId: string, projectName: string) => {
    setExporting(projectId)
    try {
      const response = await apiClient.post(`/library/${projectId}/export`, null, {
        responseType: 'blob',
      })
      const slug = projectName.toLowerCase().replace(/\s+/g, '-').slice(0, 30)
      downloadBlob(response.data, `${slug}.ideai`)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExporting(null)
    }
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      await apiClient.post('/library/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await fetchProjects()
    } catch (err) {
      console.error('Import failed:', err)
    } finally {
      setImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleCreateSnapshot = async () => {
    if (!selectedProjectId || !snapshotName.trim()) return
    setCreatingSnapshot(true)
    try {
      await apiClient.post(`/library/${selectedProjectId}/snapshots`, {
        name: snapshotName.trim(),
        description: snapshotDesc.trim() || null,
      })
      setSnapshotName('')
      setSnapshotDesc('')
      setShowSnapshotForm(false)
      await fetchSnapshots(selectedProjectId)
      await fetchProjects()
    } catch (err) {
      console.error('Snapshot creation failed:', err)
    } finally {
      setCreatingSnapshot(false)
    }
  }

  const handleRestore = async (snapshotId: string) => {
    setRestoring(snapshotId)
    try {
      await apiClient.post(`/library/snapshots/${snapshotId}/restore`)
      await fetchProjects()
    } catch (err) {
      console.error('Restore failed:', err)
    } finally {
      setRestoring(null)
    }
  }

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir(key === 'name' ? 'asc' : 'desc')
    }
  }

  // Filtered + sorted projects
  const filteredProjects = projects
    .filter((p) => {
      if (!search) return true
      const q = search.toLowerCase()
      return (
        p.name.toLowerCase().includes(q) ||
        p.platform.toLowerCase().includes(q) ||
        (p.description || '').toLowerCase().includes(q)
      )
    })
    .sort((a, b) => {
      let cmp = 0
      if (sortKey === 'name') cmp = a.name.localeCompare(b.name)
      else if (sortKey === 'platform') cmp = a.platform.localeCompare(b.platform)
      else if (sortKey === 'updated_at') cmp = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
      else if (sortKey === 'created_at') cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      return sortDir === 'asc' ? cmp : -cmp
    })

  const selectedProject = projects.find((p) => p.id === selectedProjectId)

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  const formatDateTime = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <span className="text-text-muted/30 ml-1">{'\u2195'}</span>
    return <span className="text-accent ml-1">{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>
  }

  /** Human-readable progress label for a project. */
  const progressLabel = (p: LibraryProject) => {
    if (!p.discovery_stage) return 'Not started'
    if (p.discovery_stage !== 'confirm' && p.discovery_stage !== 'complete')
      return `Discovery (${p.discovery_stage})`
    if (!p.pathway_status || p.pathway_status === 'pending') return 'Pathway review'
    if (p.pathway_status === 'active') return 'Modules in progress'
    if (p.block_count === 0) return 'Ready for blocks'
    return 'Complete'
  }

  /** Color class for the progress badge. */
  const progressColor = (p: LibraryProject) => {
    if (!p.discovery_stage) return 'text-text-muted'
    if (p.pathway_status === 'complete' && p.block_count > 0) return 'text-green-400'
    return 'text-yellow-400'
  }

  /** Resume button label based on where the user left off. */
  const resumeLabel = (p: LibraryProject) => {
    if (!p.discovery_stage) return 'Start'
    if (p.pathway_status === 'complete' && p.block_count > 0) return 'View'
    return 'Resume'
  }

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="ml-0 md:ml-[232px] pb-mobile-nav md:pb-0 flex-1 flex flex-col h-dvh">
        <TopBar title="Projects" subtitle="Manage projects, snapshots, and exports">
          <input
            ref={fileInputRef}
            type="file"
            accept=".ideai"
            onChange={handleImport}
            className="hidden"
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
          >
            {importing ? 'Importing...' : 'Import .ideai'}
          </Button>
        </TopBar>

        <div className="flex-1 p-4 md:p-6 overflow-y-auto pb-20 md:pb-6">
          <div className="max-w-6xl mx-auto">
            {/* ── Toolbar: search + view toggle ── */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search projects..."
                className="w-full md:w-72 bg-white/5 border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
              />
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setViewMode('list')}
                  className={`px-2.5 py-1.5 rounded text-xs border transition-colors ${
                    viewMode === 'list'
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border bg-white/5 text-text-muted hover:text-white'
                  }`}
                  title="List view"
                >
                  ☰
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  className={`px-2.5 py-1.5 rounded text-xs border transition-colors ${
                    viewMode === 'grid'
                      ? 'border-accent bg-accent/10 text-accent'
                      : 'border-border bg-white/5 text-text-muted hover:text-white'
                  }`}
                  title="Grid view"
                >
                  ⊞
                </button>
                <span className="text-[10px] text-text-muted ml-2">
                  {filteredProjects.length} project{filteredProjects.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-12 text-text-muted text-sm">Loading projects...</div>
            ) : projects.length === 0 ? (
              <Card className="text-center py-12">
                <p className="text-4xl mb-3 opacity-30">📁</p>
                <p className="text-text-muted text-sm mb-3">No projects yet. Create one from the Home page.</p>
                <p className="text-text-muted text-xs">Or import a .ideai file using the button above.</p>
              </Card>
            ) : viewMode === 'list' ? (
              /* ── Explorer-style list view ── */
              <div className="rounded-lg border border-border overflow-hidden mb-6">
                {/* Header row */}
                <div className="hidden md:grid grid-cols-[1fr_120px_140px_120px_100px_56px] gap-2 px-4 py-2 bg-white/3 border-b border-border text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  <button onClick={() => handleSort('name')} className="text-left flex items-center hover:text-white transition-colors">
                    Name <SortIcon col="name" />
                  </button>
                  <button onClick={() => handleSort('platform')} className="text-left flex items-center hover:text-white transition-colors">
                    Platform <SortIcon col="platform" />
                  </button>
                  <span>Progress</span>
                  <button onClick={() => handleSort('updated_at')} className="text-left flex items-center hover:text-white transition-colors">
                    Modified <SortIcon col="updated_at" />
                  </button>
                  <span>Snapshots</span>
                  <span />
                </div>

                {/* Rows */}
                {filteredProjects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() =>
                      setSelectedProjectId(
                        selectedProjectId === project.id ? null : project.id
                      )
                    }
                    className={`w-full grid grid-cols-1 md:grid-cols-[1fr_120px_140px_120px_100px_56px] gap-1 md:gap-2 px-4 py-3 text-left border-b border-border last:border-b-0 transition-colors ${
                      selectedProjectId === project.id
                        ? 'bg-accent/5 border-l-2 border-l-accent'
                        : 'hover:bg-white/3'
                    }`}
                  >
                    {/* Name */}
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className="shrink-0 w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: project.accent_color }}
                      />
                      <span className="text-sm text-white font-medium truncate">{project.name}</span>
                      {project.description && (
                        <span className="hidden lg:inline text-xs text-text-muted truncate">
                          — {project.description}
                        </span>
                      )}
                    </div>
                    {/* Platform */}
                    <span className="text-xs text-text-muted">
                      <span className="md:hidden text-[10px] text-text-muted/50 mr-1">Platform:</span>
                      {project.platform}
                    </span>
                    {/* Progress */}
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium ${progressColor(project)}`}>
                        {progressLabel(project)}
                      </span>
                      {project.design_confidence > 0 && (
                        <span className="text-[10px] text-text-muted bg-white/5 px-1.5 py-0.5 rounded">
                          {project.design_confidence}%
                        </span>
                      )}
                    </div>
                    {/* Modified */}
                    <span className="text-xs text-text-muted">
                      <span className="md:hidden text-[10px] text-text-muted/50 mr-1">Modified:</span>
                      {formatDate(project.updated_at)}
                    </span>
                    {/* Snapshots */}
                    <span className="text-xs text-text-muted">
                      {project.snapshot_count} ver{project.snapshot_count !== 1 ? 's' : ''}
                    </span>
                    {/* Actions — smart resume routing */}
                    <Link
                      to={project.recommended_resume_path || `/discovery/${project.id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-accent text-xs hover:underline"
                      title="Open project"
                    >
                      {resumeLabel(project)}
                    </Link>
                  </button>
                ))}

                {filteredProjects.length === 0 && (
                  <div className="px-4 py-8 text-center text-text-muted text-sm">
                    No projects match your search.
                  </div>
                )}
              </div>
            ) : (
              /* ── Grid view ── */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4 mb-6">
                {filteredProjects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() =>
                      setSelectedProjectId(
                        selectedProjectId === project.id ? null : project.id
                      )
                    }
                    className="text-left"
                  >
                    <Card
                      className={`transition-all cursor-pointer h-full ${
                        selectedProjectId === project.id
                          ? 'border-accent shadow-[0_0_20px_rgba(0,229,255,0.1)]'
                          : 'hover:border-white/15'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <h3 className="text-sm font-semibold text-white truncate flex-1">
                          {project.name}
                        </h3>
                        <span
                          className="shrink-0 w-3 h-3 rounded-full mt-0.5"
                          style={{ backgroundColor: project.accent_color }}
                        />
                      </div>
                      {project.description && (
                        <p className="text-xs text-text-muted mb-3 line-clamp-2">
                          {project.description}
                        </p>
                      )}
                      <div className="flex items-center gap-2 text-[10px] text-text-muted mb-2">
                        <span className="bg-white/5 px-2 py-0.5 rounded">{project.platform}</span>
                        <span className={`font-medium ${progressColor(project)}`}>
                          {progressLabel(project)}
                        </span>
                        {project.design_confidence > 0 && (
                          <span className="bg-white/5 px-1.5 py-0.5 rounded">
                            {project.design_confidence}%
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-[10px] text-text-muted">
                        <span>{project.snapshot_count} snapshot{project.snapshot_count !== 1 ? 's' : ''}</span>
                        {project.block_count > 0 && (
                          <span>{project.block_count} block{project.block_count !== 1 ? 's' : ''}</span>
                        )}
                        <span className="ml-auto">{formatDate(project.updated_at)}</span>
                      </div>
                    </Card>
                  </button>
                ))}

                {filteredProjects.length === 0 && (
                  <div className="col-span-full text-center py-8 text-text-muted text-sm">
                    No projects match your search.
                  </div>
                )}
              </div>
            )}

            {/* ── Selected Project Detail Panel ── */}
            {selectedProject && (
              <>
                <div className="border-t border-border mb-6" />

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-5">
                  <div>
                    <h2 className="text-lg font-semibold text-white mb-1">
                      {selectedProject.name}
                    </h2>
                    <p className="text-sm text-text-muted">
                      Manage snapshots, exports, and sharing.
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShareOpen(true)}
                    >
                      Share
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleExport(selectedProject.id, selectedProject.name)}
                      disabled={exporting === selectedProject.id}
                    >
                      {exporting === selectedProject.id ? 'Exporting...' : 'Export .ideai'}
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => setShowSnapshotForm(!showSnapshotForm)}
                    >
                      Create Snapshot
                    </Button>
                  </div>
                </div>

                {/* Create Snapshot Form */}
                {showSnapshotForm && (
                  <Card className="mb-6">
                    <h3 className="text-sm font-semibold text-white mb-3">New Snapshot</h3>
                    <div className="space-y-3">
                      <div>
                        <label className="block text-xs font-medium text-text-muted mb-1">Name *</label>
                        <input
                          type="text"
                          value={snapshotName}
                          onChange={(e) => setSnapshotName(e.target.value)}
                          placeholder="e.g., v1.0 - MVP scope finalized"
                          className="w-full bg-white/5 border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
                          maxLength={200}
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-text-muted mb-1">Description (optional)</label>
                        <textarea
                          value={snapshotDesc}
                          onChange={(e) => setSnapshotDesc(e.target.value)}
                          placeholder="Brief notes about what changed..."
                          className="w-full bg-white/5 border border-border rounded-lg px-3 py-2 text-sm text-white placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors resize-none h-20"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={handleCreateSnapshot}
                          disabled={!snapshotName.trim() || creatingSnapshot}
                        >
                          {creatingSnapshot ? 'Saving...' : 'Save Snapshot'}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setShowSnapshotForm(false)
                            setSnapshotName('')
                            setSnapshotDesc('')
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </Card>
                )}

                {/* Snapshots List */}
                <h3 className="text-sm font-semibold text-white mb-3">Version History</h3>

                {snapshotsLoading ? (
                  <div className="text-center py-8 text-text-muted text-sm">Loading snapshots...</div>
                ) : snapshots.length === 0 ? (
                  <Card className="text-center py-8">
                    <p className="text-text-muted text-sm">
                      No snapshots yet. Create one to save the current project state.
                    </p>
                  </Card>
                ) : (
                  <div className="space-y-2">
                    {snapshots.map((snap) => (
                      <Card key={snap.id} className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono text-accent bg-accent/10 px-1.5 py-0.5 rounded">
                              v{snap.version}
                            </span>
                            <h4 className="text-sm font-medium text-white truncate">{snap.name}</h4>
                          </div>
                          {snap.description && (
                            <p className="text-xs text-text-muted truncate">{snap.description}</p>
                          )}
                          <p className="text-[10px] text-text-muted mt-1">{formatDateTime(snap.created_at)}</p>
                        </div>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleRestore(snap.id)}
                          disabled={restoring === snap.id}
                        >
                          {restoring === snap.id ? 'Restoring...' : 'Restore'}
                        </Button>
                      </Card>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Share Dialog */}
      {selectedProject && (
        <ShareDialog
          projectId={selectedProject.id}
          projectName={selectedProject.name}
          open={shareOpen}
          onClose={() => setShareOpen(false)}
        />
      )}
    </div>
  )
}
