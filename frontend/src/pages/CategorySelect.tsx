/**
 * CategorySelect — Full-page category picker shown before the main Home page.
 * Users select one of 16 concept categories, then proceed to idea input.
 * @module pages/CategorySelect
 */
import { motion } from 'framer-motion'
import { IdeaNebulaCanvas } from '../components/nebula/IdeaNebulaCanvas'
import { CONCEPT_CATEGORIES } from '../lib/categories'

interface Props {
  onSelect: (categoryId: string) => void
}

export function CategorySelect({ onSelect }: Props) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4 py-12 relative">
      <IdeaNebulaCanvas />

      <div className="relative z-10 w-full max-w-4xl">
        {/* Title */}
        <motion.div
          className="text-center mb-10"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-3xl md:text-5xl font-bold text-white mb-3">
            What are you <span className="text-accent">creating</span>?
          </h1>
          <p className="text-text-muted text-sm md:text-base">
            Pick the category that best fits your project
          </p>
        </motion.div>

        {/* Category grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {CONCEPT_CATEGORIES.map((cat, i) => (
            <motion.button
              key={cat.id}
              type="button"
              onClick={() => onSelect(cat.id)}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03, duration: 0.3 }}
              className="group relative bg-surface/60 backdrop-blur-md border border-border rounded-xl p-4 md:p-5 text-center transition-all duration-200 hover:border-accent/40 hover:bg-accent/5 hover:shadow-[0_0_20px_rgba(0,229,255,0.08)] hover:scale-[1.03] cursor-pointer"
            >
              <span className="text-3xl md:text-4xl block mb-2">{cat.icon}</span>
              <p className="text-sm font-semibold text-white group-hover:text-accent transition-colors">
                {cat.label}
              </p>
              <p className="text-[10px] text-text-muted mt-1 leading-tight">
                {cat.examples.join(' \u00B7 ')}
              </p>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  )
}
