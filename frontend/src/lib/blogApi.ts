/**
 * blogApi — Blog API calls. Public reads need no auth (apiClient simply omits
 * the token when signed out); admin writes ride the Clerk session token.
 * @module lib/blogApi
 */
import apiClient from './apiClient'
import type {
  BlogListResponse,
  BlogPost,
  BlogPostCreate,
  BlogPostSummary,
  BlogPostUpdate,
} from '../types/blog'

/** Lowercase, hyphenate, strip to a URL-safe slug (mirrors the backend). */
export function slugify(value: string): string {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'post'
  )
}

// ── Public ──────────────────────────────────────────────────────────

export async function listPublishedPosts(): Promise<BlogPostSummary[]> {
  const { data } = await apiClient.get<BlogPostSummary[]>('/blog/posts')
  return data
}

export async function getPublishedPost(slug: string): Promise<BlogPost> {
  const { data } = await apiClient.get<BlogPost>(`/blog/posts/${encodeURIComponent(slug)}`)
  return data
}

// ── Admin ───────────────────────────────────────────────────────────

export async function adminListPosts(status?: 'published' | 'draft'): Promise<BlogListResponse> {
  const { data } = await apiClient.get<BlogListResponse>('/blog/admin/posts', {
    params: status ? { status } : undefined,
  })
  return data
}

export async function adminGetPost(id: string): Promise<BlogPost> {
  const { data } = await apiClient.get<BlogPost>(`/blog/admin/posts/${id}`)
  return data
}

export async function adminCreatePost(payload: BlogPostCreate): Promise<BlogPost> {
  const { data } = await apiClient.post<BlogPost>('/blog/admin/posts', payload)
  return data
}

export async function adminUpdatePost(id: string, payload: BlogPostUpdate): Promise<BlogPost> {
  const { data } = await apiClient.patch<BlogPost>(`/blog/admin/posts/${id}`, payload)
  return data
}

export async function adminDeletePost(id: string): Promise<void> {
  await apiClient.delete(`/blog/admin/posts/${id}`)
}
