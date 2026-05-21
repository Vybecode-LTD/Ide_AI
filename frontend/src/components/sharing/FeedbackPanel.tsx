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
  /** JWT for private share access (returned by /verify). Optional for public shares. */
  shareAccessToken?: string | null
}

export function FeedbackPanel({
  shareToken,
  allowFeedback,
  allowRatings,
  shareAccessToken,
}: FeedbackPanelProps) {
  const [averageScore, setAverageScore] = useState(0)
  const [totalRatings, setTotalRatings] = useState(0)

  const fetchRatings = useCallback(async () => {
    if (!allowRatings) return
    try {
      const headers: Record<string, string> = {}
      if (shareAccessToken) headers['Authorization'] = `Bearer ${shareAccessToken}`
      const resp = await fetch(
        `${API_BASE}/sharing/public/${shareToken}/ratings`,
        { headers },
      )
      if (resp.ok) {
        const data = await resp.json()
        setAverageScore(data.average_score ?? 0)
        setTotalRatings(data.total_ratings ?? 0)
      }
    } catch {
      // silently fail
    }
  }, [shareToken, allowRatings, shareAccessToken])

  // Fetch ratings on mount / when dependencies change.
  // The setState is inside an async callback (not synchronous in the effect body).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { fetchRatings() }, [fetchRatings])

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
            shareAccessToken={shareAccessToken}
          />
        </div>
      )}

      {allowFeedback && <CommentSection shareToken={shareToken} shareAccessToken={shareAccessToken} />}
    </section>
  )
}
