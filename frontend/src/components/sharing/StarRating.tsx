/**
 * StarRating — Interactive star rating widget for shared project blocks.
 * Uses the public sharing API (no auth required).
 */
import { useState } from 'react'
import toast from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

interface StarRatingProps {
  shareToken: string
  /** Summary fetched from the API — averageScore and totalRatings. */
  averageScore: number
  totalRatings: number
  onRated?: () => void
  /** JWT for private share access (returned by /verify). Optional for public shares. */
  shareAccessToken?: string | null
}

export function StarRating({
  shareToken,
  averageScore,
  totalRatings,
  onRated,
  shareAccessToken,
}: StarRatingProps) {
  const [hovered, setHovered] = useState(0)
  const [selected, setSelected] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleRate = async (score: number) => {
    if (submitted || submitting) return
    setSelected(score)
    setSubmitting(true)
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (shareAccessToken) headers['Authorization'] = `Bearer ${shareAccessToken}`
      const resp = await fetch(
        `${API_BASE}/sharing/public/${shareToken}/ratings`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ score }),
        },
      )
      if (resp.ok) {
        setSubmitted(true)
        onRated?.()
      } else {
        const data = await resp.json()
        toast.error(data.detail || 'Rating failed.')
        setSelected(0)
      }
    } catch {
      toast.error('Failed to submit rating.')
      setSelected(0)
    } finally {
      setSubmitting(false)
    }
  }

  const displayScore = submitted ? selected : averageScore

  return (
    <div>
      <div className="flex items-center gap-3 mb-1">
        {/* Stars */}
        <div className="flex gap-0.5">
          {[1, 2, 3, 4, 5].map((star) => {
            const filled = hovered ? star <= hovered : star <= Math.round(displayScore)
            return (
              <button
                key={star}
                type="button"
                disabled={submitted || submitting}
                onMouseEnter={() => !submitted && setHovered(star)}
                onMouseLeave={() => setHovered(0)}
                onClick={() => handleRate(star)}
                className={`text-lg transition-colors ${
                  filled
                    ? 'text-yellow-400'
                    : 'text-white/15 hover:text-yellow-400/50'
                } ${submitted ? 'cursor-default' : 'cursor-pointer'}`}
              >
                {filled ? '★' : '☆'}
              </button>
            )
          })}
        </div>
        {/* Score text */}
        <span className="text-xs text-white/50">
          {displayScore > 0 ? displayScore.toFixed(1) : '---'}
          {totalRatings > 0 && (
            <span className="ml-1">
              ({totalRatings} rating{totalRatings !== 1 ? 's' : ''})
            </span>
          )}
        </span>
      </div>
      {submitted && (
        <p className="text-xs text-green-400">Thanks for rating!</p>
      )}
    </div>
  )
}
