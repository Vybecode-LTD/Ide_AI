/**
 * blog.ts — TypeScript types for the blog feature (mirrors backend schemas).
 */

export interface BlogPostSummary {
  id: string
  title: string
  slug: string
  excerpt: string | null
  cover_image_url: string | null
  tags: string[] | null
  author_name: string | null
  published: boolean
  published_at: string | null
  view_count: number
  created_at: string
}

export interface BlogPost extends BlogPostSummary {
  body: string
  updated_at: string
}

export interface BlogPostCreate {
  title: string
  slug?: string
  excerpt?: string | null
  body: string
  cover_image_url?: string | null
  tags?: string[] | null
  author_name?: string | null
  published?: boolean
}

export type BlogPostUpdate = Partial<BlogPostCreate>

export interface BlogListResponse {
  items: BlogPostSummary[]
  total: number
  page: number
  per_page: number
}
