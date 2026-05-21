/**
 * FeedbackPanel — Combines CommentSection + StarRating for a shared project.
 * Conditionally renders each based on the share's allow_feedback / allow_ratings flags.
 */
import { useCallback, useEffect, useState } from 'react'
import { CommentSection } from './CommentSection'
import { StarRating } from './StarRating'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

interface FeedbackPanelProps {
  shareToken: string
  allowFeedback: boolean
  allowRatings: boolean
}

export function FeedbackPanel({
  shareToken,
  allowFeedback,
  allowRatings,
}: FeedbackPanelProps) {
  const [averageScore, setAverageScore] = useState(0)
  const [totalRatings, setTotalRatings] = useState(0)

  const fetchRatings = useCallback(async () => {
    if (!allowRatings) return
    try {
      const resp = await fetch(
        `${API_BASE}/sharing/public/${shareToken}/ratings`,
      )
      if (resp.ok) {
        const data = await resp.json()
        setAverageScore(data.average_score ?? 0)
        setTotalRatings(data.total_ratings ?? 0)
      }
    } catch {
      // silently fail
    }
  }, [shareToken, allowRatings])

  useEffect(() => {
    fetchRatings()
  }, [fetchRatings])

  if (!allowFeedback && !allowRatings) return null

  return (
    <section className="space-y-6">
      <h2 className="text-lg font-semibold text-white">Feedback</h2>

      {allowRatings && (
        <div>
          <h3 className="text-sm font-semibold text-white mb-2">
            Rate this project
          </h3>
          <StarRating
            shareToken={shareToken}
            averageScore={averageScore}
            totalRatings={totalRatings}
            onRated={fetchRatings}
          />
        </div>
      )}

      {allowFeedback && <CommentSection shareToken={shareToken} />}
    </section>
  )
}
