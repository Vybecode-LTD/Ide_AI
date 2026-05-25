import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import apiClient from '../lib/apiClient'
import { extractError } from '../lib/extractError'
import { Sidebar } from '../components/layout/Sidebar'

interface ModuleLibraryItem {
  id: string
  label: string
  group: string
  description: string
}

interface FieldSchema {
  key: string
  label: string
  type: 'text' | 'longtext' | 'list' | 'dict'
  required: boolean
  extraction_hint?: string
}

interface DesignKitModule {
  module_id: string
  label: string
  description: string
  group: string
  has_output: boolean
  fields: FieldSchema[]
  responses: Record<string, unknown>
  status: string
}

interface DesignKitData {
  project_id: string
  project_name: string
  modules: DesignKitModule[]
}

function titleize(s: string): string {
  return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

interface GeneratedOutput {
  title: string
  content: string
  generated_at: string
}

function ModuleCard({
  mod,
  onSave,
  onRefreshOutput,
}: {
  mod: DesignKitModule
  onSave: (moduleId: string, fields: Record<string, unknown>) => Promise<void>
  onRefreshOutput?: (moduleId: string) => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Record<string, unknown>>({})
  const [saving, setSaving] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const generatedOutput = (mod.responses.__generated_output as GeneratedOutput | undefined) || null

  const handleRefresh = async () => {
    if (!onRefreshOutput) return
    setRefreshing(true)
    try {
      await onRefreshOutput(mod.module_id)
    } finally {
      setRefreshing(false)
    }
  }

  const filledCount = mod.fields.filter((f) => f.key in mod.responses).length
  const totalCount = mod.fields.length
  const pct = totalCount > 0 ? Math.round((filledCount / totalCount) * 100) : 0

  const startEdit = () => {
    setDraft({ ...mod.responses })
    setEditing(true)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(mod.module_id, draft)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const updateField = (key: string, value: unknown) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <motion.div
      layout
      className="rounded-xl border border-border bg-white/[0.03] backdrop-blur-sm overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-[10px] uppercase tracking-wider text-text-muted font-semibold shrink-0">
            {mod.group}
          </span>
          <h3 className="text-sm font-semibold text-white truncate">{mod.label}</h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span
            className={`text-xs font-medium tabular-nums ${pct >= 80 ? 'text-accent' : pct > 0 ? 'text-white/70' : 'text-text-muted'}`}
          >
            {filledCount}/{totalCount}
          </span>
          {!editing && (
            <button
              onClick={startEdit}
              className="text-xs text-accent hover:text-accent/80 font-medium px-2 py-1 rounded hover:bg-accent/10 transition-colors"
            >
              Edit
            </button>
          )}
        </div>
      </div>

      {/* Fields */}
      <div className="px-4 py-3 space-y-3">
        {mod.fields.map((field) => {
          const value = editing ? draft[field.key] : mod.responses[field.key]
          const isEmpty = value === undefined || value === null || value === ''

          if (editing) {
            return (
              <FieldEditor
                key={field.key}
                field={field}
                value={value}
                onChange={(v) => updateField(field.key, v)}
              />
            )
          }

          return (
            <div key={field.key} className="flex flex-col gap-0.5">
              <span className="text-[11px] text-text-muted font-medium">
                {field.label}
                {field.required && <span className="text-amber-300 ml-0.5">*</span>}
              </span>
              {isEmpty ? (
                <span className="text-xs text-text-muted/50 italic">Not filled</span>
              ) : (
                <FieldDisplay type={field.type} value={value} />
              )}
            </div>
          )
        })}
      </div>

      {/* Edit actions */}
      <AnimatePresence>
        {editing && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-border px-4 py-2.5 flex items-center gap-2 justify-end"
          >
            <button
              onClick={() => setEditing(false)}
              className="text-xs text-text-muted hover:text-white px-3 py-1.5 rounded transition-colors"
              disabled={saving}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="text-xs font-medium text-white bg-accent/20 hover:bg-accent/30 border border-accent/40 px-3 py-1.5 rounded transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Generated output section for has_output modules */}
      {mod.has_output && (
        <div className="border-t border-border px-4 py-3">
          {generatedOutput ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-wider text-accent/80 font-semibold">
                  Generated Output
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-text-muted">
                    {new Date(generatedOutput.generated_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="text-[10px] text-accent hover:text-accent/80 font-medium px-1.5 py-0.5 rounded hover:bg-accent/10 transition-colors disabled:opacity-50"
                  >
                    {refreshing ? 'Generating...' : 'Regenerate'}
                  </button>
                </div>
              </div>
              <div className="text-xs text-white/80 whitespace-pre-wrap bg-white/[0.02] rounded-lg p-3 border border-border max-h-64 overflow-y-auto">
                {generatedOutput.content}
              </div>
            </div>
          ) : (
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="w-full text-xs font-medium text-accent border border-accent/30 hover:bg-accent/10 rounded-lg px-3 py-2.5 transition-colors disabled:opacity-50"
            >
              {refreshing ? 'Generating output...' : 'Generate Output'}
            </button>
          )}
        </div>
      )}
    </motion.div>
  )
}

function FieldEditor({
  field,
  value,
  onChange,
}: {
  field: FieldSchema
  value: unknown
  onChange: (v: unknown) => void
}) {
  if (field.type === 'longtext') {
    return (
      <div className="flex flex-col gap-1">
        <label className="text-[11px] text-text-muted font-medium">
          {field.label}
          {field.required && <span className="text-amber-300 ml-0.5">*</span>}
        </label>
        <textarea
          value={typeof value === 'string' ? value : ''}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          className="bg-white/[0.04] border border-border rounded-lg px-3 py-2 text-xs text-white resize-y focus:outline-none focus:ring-1 focus:ring-accent/40"
          placeholder={field.extraction_hint || `Enter ${field.label.toLowerCase()}...`}
        />
      </div>
    )
  }

  if (field.type === 'list') {
    const items = Array.isArray(value) ? value : []
    const [inputVal, setInputVal] = useState('')

    const addItem = () => {
      const trimmed = inputVal.trim()
      if (trimmed) {
        onChange([...items, trimmed])
        setInputVal('')
      }
    }

    return (
      <div className="flex flex-col gap-1">
        <label className="text-[11px] text-text-muted font-medium">
          {field.label}
          {field.required && <span className="text-amber-300 ml-0.5">*</span>}
        </label>
        <div className="flex flex-wrap gap-1.5 mb-1">
          {items.map((item, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 text-[11px] bg-accent/10 border border-accent/20 text-accent/90 rounded px-2 py-0.5"
            >
              {String(item)}
              <button
                type="button"
                onClick={() => onChange(items.filter((_, idx) => idx !== i))}
                className="text-accent/50 hover:text-accent"
              >
                x
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-1.5">
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addItem() } }}
            placeholder={`Add ${field.label.toLowerCase()}...`}
            className="flex-1 bg-white/[0.04] border border-border rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-accent/40"
          />
          <button
            type="button"
            onClick={addItem}
            className="text-xs text-accent hover:bg-accent/10 px-2 py-1.5 rounded border border-accent/30"
          >
            +
          </button>
        </div>
      </div>
    )
  }

  if (field.type === 'dict') {
    const dict = (typeof value === 'object' && value && !Array.isArray(value))
      ? value as Record<string, unknown>
      : {}
    const entries = Object.entries(dict)
    const [newKey, setNewKey] = useState('')
    const [newVal, setNewVal] = useState('')

    const addEntry = () => {
      const k = newKey.trim()
      const v = newVal.trim()
      if (k && v) {
        onChange({ ...dict, [k]: v })
        setNewKey('')
        setNewVal('')
      }
    }

    return (
      <div className="flex flex-col gap-1">
        <label className="text-[11px] text-text-muted font-medium">
          {field.label}
          {field.required && <span className="text-amber-300 ml-0.5">*</span>}
        </label>
        <div className="space-y-1 mb-1">
          {entries.map(([k, v]) => (
            <div key={k} className="flex items-center gap-1.5 text-[11px]">
              <span className="text-accent/80 font-medium">{k}:</span>
              <span className="text-white/80 flex-1 truncate">{String(v)}</span>
              <button
                type="button"
                onClick={() => {
                  const next = { ...dict }
                  delete next[k]
                  onChange(next)
                }}
                className="text-red-400/60 hover:text-red-400 text-[10px]"
              >
                x
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-1.5">
          <input
            type="text"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="Key"
            className="w-24 bg-white/[0.04] border border-border rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-accent/40"
          />
          <input
            type="text"
            value={newVal}
            onChange={(e) => setNewVal(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addEntry() } }}
            placeholder="Value"
            className="flex-1 bg-white/[0.04] border border-border rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-accent/40"
          />
          <button
            type="button"
            onClick={addEntry}
            className="text-xs text-accent hover:bg-accent/10 px-2 py-1.5 rounded border border-accent/30"
          >
            +
          </button>
        </div>
      </div>
    )
  }

  // Default: text
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] text-text-muted font-medium">
        {field.label}
        {field.required && <span className="text-amber-300 ml-0.5">*</span>}
      </label>
      <input
        type="text"
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.extraction_hint || `Enter ${field.label.toLowerCase()}...`}
        className="bg-white/[0.04] border border-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-accent/40"
      />
    </div>
  )
}

function FieldDisplay({ type, value }: { type: string; value: unknown }) {
  if (type === 'list' && Array.isArray(value)) {
    return (
      <div className="flex flex-wrap gap-1">
        {value.map((item, i) => (
          <span
            key={i}
            className="text-[11px] bg-accent/10 border border-accent/20 text-accent/90 rounded px-1.5 py-0.5"
          >
            {String(item)}
          </span>
        ))}
      </div>
    )
  }

  if (type === 'dict' && typeof value === 'object' && value) {
    return (
      <div className="space-y-0.5">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k} className="text-[11px]">
            <span className="text-accent/70 font-medium">{titleize(k)}:</span>{' '}
            <span className="text-white/80">{String(v)}</span>
          </div>
        ))}
      </div>
    )
  }

  return <span className="text-xs text-white/80">{String(value)}</span>
}

function AddModulesModal({
  existingIds,
  onAdd,
  onClose,
}: {
  existingIds: Set<string>
  onAdd: (ids: string[]) => void
  onClose: () => void
}) {
  const [modules, setModules] = useState<ModuleLibraryItem[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState('')

  useEffect(() => {
    apiClient.get<ModuleLibraryItem[]>('/meta/modules').then(({ data }) => {
      setModules(data.filter((m) => !existingIds.has(m.id)))
    })
  }, [existingIds])

  const filtered = modules.filter(
    (m) =>
      m.label.toLowerCase().includes(filter.toLowerCase()) ||
      m.group.toLowerCase().includes(filter.toLowerCase()),
  )

  const groups = filtered.reduce<Record<string, ModuleLibraryItem[]>>((acc, m) => {
    ;(acc[m.group] ??= []).push(m)
    return acc
  }, {})

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-[#1a1a22] border border-border rounded-xl w-full max-w-lg max-h-[80vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Add Modules</h3>
          <button onClick={onClose} className="text-text-muted hover:text-white text-lg leading-none">&times;</button>
        </div>
        <div className="px-4 py-2 border-b border-border">
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search modules..."
            className="w-full bg-white/[0.04] border border-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-accent/40"
          />
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          {Object.entries(groups).map(([group, items]) => (
            <div key={group}>
              <h4 className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1.5">{group}</h4>
              <div className="space-y-1">
                {items.map((m) => (
                  <label
                    key={m.id}
                    className={`flex items-start gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors ${
                      selected.has(m.id) ? 'bg-accent/10 border border-accent/30' : 'hover:bg-white/[0.03] border border-transparent'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(m.id)}
                      onChange={() => toggle(m.id)}
                      className="mt-0.5 accent-[#00E5FF]"
                    />
                    <div>
                      <span className="text-xs text-white font-medium">{m.label}</span>
                      <p className="text-[10px] text-text-muted">{m.description}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="text-xs text-text-muted text-center py-4">No modules available to add.</p>
          )}
        </div>
        <div className="px-4 py-3 border-t border-border flex items-center justify-between">
          <span className="text-[10px] text-text-muted">{selected.size} selected</span>
          <div className="flex gap-2">
            <button onClick={onClose} className="text-xs text-text-muted hover:text-white px-3 py-1.5 rounded">
              Cancel
            </button>
            <button
              onClick={() => { onAdd(Array.from(selected)); onClose() }}
              disabled={selected.size === 0}
              className="text-xs font-medium text-white bg-accent/20 hover:bg-accent/30 border border-accent/40 px-3 py-1.5 rounded transition-colors disabled:opacity-50"
            >
              Add {selected.size > 0 ? `(${selected.size})` : ''}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function DesignKit() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [data, setData] = useState<DesignKitData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return
    const load = async () => {
      try {
        const { data: kit } = await apiClient.get<DesignKitData>(
          `/projects/${projectId}/design-kit`,
        )
        setData(kit)
      } catch (err) {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 409) {
          navigate(`/exports/${projectId}`, { replace: true })
          return
        }
        toast.error(extractError(err, 'Failed to load design kit'))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [projectId, navigate])

  const handleSave = useCallback(
    async (moduleId: string, fields: Record<string, unknown>) => {
      if (!projectId) return
      try {
        const { data: updated } = await apiClient.patch(
          `/modules/${projectId}/${moduleId}/responses`,
          fields,
        )
        setData((prev) => {
          if (!prev) return prev
          return {
            ...prev,
            modules: prev.modules.map((m) =>
              m.module_id === moduleId
                ? { ...m, responses: updated.responses, status: updated.status }
                : m,
            ),
          }
        })
        toast.success('Saved')
      } catch (err) {
        toast.error(extractError(err, 'Failed to save'))
        throw err
      }
    },
    [projectId],
  )

  const handleRefreshOutput = useCallback(
    async (moduleId: string) => {
      if (!projectId) return
      try {
        const { data: output } = await apiClient.post(
          `/modules/${projectId}/${moduleId}/refresh-output`,
        )
        setData((prev) => {
          if (!prev) return prev
          return {
            ...prev,
            modules: prev.modules.map((m) =>
              m.module_id === moduleId
                ? { ...m, responses: { ...m.responses, __generated_output: output } }
                : m,
            ),
          }
        })
        toast.success('Output generated')
      } catch (err) {
        toast.error(extractError(err, 'Failed to generate output'))
      }
    },
    [projectId],
  )

  const [showAddModules, setShowAddModules] = useState(false)

  const handleAddModules = useCallback(
    async (moduleIds: string[]) => {
      if (!projectId || moduleIds.length === 0) return
      try {
        await apiClient.post(`/projects/${projectId}/pathway/modules`, { module_ids: moduleIds })
        const { data: kit } = await apiClient.get<DesignKitData>(`/projects/${projectId}/design-kit`)
        setData(kit)
        toast.success(`Added ${moduleIds.length} module${moduleIds.length > 1 ? 's' : ''}`)
      } catch (err) {
        toast.error(extractError(err, 'Failed to add modules'))
      }
    },
    [projectId],
  )

  if (loading) {
    return (
      <div className="flex h-dvh">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="animate-pulse text-text-muted text-sm">Loading design kit...</div>
        </main>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex h-dvh">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-text-muted text-sm">Design kit not available.</div>
        </main>
      </div>
    )
  }

  // Group modules by group
  const groups = data.modules.reduce<Record<string, DesignKitModule[]>>((acc, mod) => {
    const g = mod.group || 'Other'
    ;(acc[g] ??= []).push(mod)
    return acc
  }, {})

  const totalFilled = data.modules.reduce(
    (sum, m) => sum + m.fields.filter((f) => f.key in m.responses).length,
    0,
  )
  const totalFields = data.modules.reduce((sum, m) => sum + m.fields.length, 0)
  const overallPct = totalFields > 0 ? Math.round((totalFilled / totalFields) * 100) : 0

  return (
    <div className="flex h-dvh">
      <Sidebar />
      <main className="flex-1 overflow-y-auto pb-mobile-nav">
        <div className="max-w-4xl mx-auto px-4 md:px-6 py-6 space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white">{data.project_name}</h1>
              <p className="text-xs text-text-muted mt-0.5">Design Kit</p>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-lg font-bold text-accent">{overallPct}%</div>
                <div className="text-[10px] text-text-muted">
                  {totalFilled}/{totalFields} fields
                </div>
              </div>
              <button
                onClick={() => setShowAddModules(true)}
                className="text-xs font-medium text-text-muted hover:text-white border border-border hover:border-accent/40 px-3 py-2 rounded-lg transition-colors"
              >
                + Add Modules
              </button>
              <button
                onClick={() => navigate(`/exports/${projectId}`)}
                className="text-xs font-medium text-white bg-accent/20 hover:bg-accent/30 border border-accent/40 px-3 py-2 rounded-lg transition-colors"
              >
                Export
              </button>
            </div>
          </div>

          {/* Progress bar */}
          <div
            className="h-1.5 bg-white/5 rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={overallPct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full bg-accent rounded-full transition-all duration-500"
              style={{ width: `${overallPct}%` }}
            />
          </div>

          {/* Module cards by group */}
          {Object.entries(groups).map(([group, modules]) => (
            <section key={group} className="space-y-3">
              <h2 className="text-xs uppercase tracking-wider text-text-muted font-semibold">
                {group}
              </h2>
              <div className="space-y-3">
                {modules.map((mod) => (
                  <ModuleCard key={mod.module_id} mod={mod} onSave={handleSave} onRefreshOutput={handleRefreshOutput} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </main>

      {showAddModules && (
        <AddModulesModal
          existingIds={new Set(data.modules.map((m) => m.module_id))}
          onAdd={handleAddModules}
          onClose={() => setShowAddModules(false)}
        />
      )}
    </div>
  )
}
