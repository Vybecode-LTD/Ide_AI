/**
 * TemplateGrid — Displays system project templates filtered by the selected category.
 * @module components/home/TemplateGrid
 */
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Card } from '../ui/Card'
import apiClient from '../../lib/apiClient'
import toast from 'react-hot-toast'

export interface Template {
  id: string
  name: string
  description: string
  icon: string
  category: string
}

interface Props {
  onSelect: (template: Template) => void
  selectedId?: string | null
  /** Pre-set category from CategorySelect — hides the dropdown when provided */
  category?: string
}

const DEFAULT_CATEGORY = 'software_tech'

/** Maps legacy template category slugs to concept category IDs */
const LEGACY_MAP: Record<string, string> = {
  saas: 'software_tech',
  mobile: 'software_tech',
  ai_ml: 'software_tech',
  social: 'software_tech',
  developer: 'software_tech',
  general: 'software_tech',
  software: 'software_tech',
  ecommerce: 'business_startup',
  marketplace: 'business_startup',
  business: 'business_startup',
  marketing: 'business_startup',
  content: 'creative_writing',
  personal: 'creative_writing',
  creative: 'art_visual',
  education: 'education_training',
}

/** Module-level cache so templates survive component remounts */
let _templateCache: Template[] | null = null

export function TemplateGrid({ onSelect, selectedId, category }: Props) {
  const [templates, setTemplates] = useState<Template[]>(() => _templateCache ?? [])
  const [loading, setLoading] = useState(() => !_templateCache)

  // Derive active category directly from props — no mirroring into state.
  const activeCategory = category || DEFAULT_CATEGORY

  useEffect(() => {
    if (_templateCache) return
    apiClient.get('/templates').then(({ data }) => {
      _templateCache = data
      setTemplates(data)
    }).catch((err) => {
      console.error('[TemplateGrid] Failed to fetch templates:', err)
      toast.error("Couldn't load project templates.")
    }).finally(() => setLoading(false))
  }, [])

  if (loading || templates.length === 0) return null
  const filtered = templates.filter(t => {
    const normalized = LEGACY_MAP[t.category] || t.category
    return normalized === activeCategory
  })
  if (filtered.length === 0) return null

  return (
    <div className="w-full max-w-2xl mx-auto mt-6 pb-[50px] md:pb-24">
      {/* Header */}
      <p className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">
        Or start from a template
      </p>

      {/* Template cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
        {filtered.map((t, i) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
          >
            <button
              type="button"
              onClick={() => onSelect(t)}
              className={`w-full text-left group rounded-xl transition-all ${
                selectedId === t.id
                  ? 'ring-1 ring-accent/40'
                  : ''
              }`}
            >
              <Card>
                <div className={`text-center py-1 transition-all ${
                  selectedId === t.id ? 'bg-accent/5' : ''
                }`}>
                  <span className="text-2xl block mb-1">{t.icon}</span>
                  <p className={`text-xs font-medium transition-colors truncate ${
                    selectedId === t.id ? 'text-accent' : 'text-white group-hover:text-accent'
                  }`}>
                    {t.name}
                  </p>
                  <p className="text-[10px] text-text-muted mt-0.5 line-clamp-2 leading-tight">
                    {t.description}
                  </p>
                </div>
              </Card>
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
