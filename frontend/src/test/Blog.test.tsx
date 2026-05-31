import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import { Blog } from '../pages/Blog'
import { BlogPost } from '../pages/BlogPost'
import * as blogApi from '../lib/blogApi'
import type { BlogPostSummary } from '../types/blog'

vi.mock('../lib/blogApi')
const mockedApi = vi.mocked(blogApi)

const SAMPLE: BlogPostSummary = {
  id: '1',
  title: 'First Post',
  slug: 'first-post',
  excerpt: 'An intro to the thing',
  cover_image_url: null,
  tags: ['tutorial'],
  author_name: 'Ide/AI',
  published: true,
  published_at: '2026-05-31T00:00:00Z',
  view_count: 5,
  created_at: '2026-05-31T00:00:00Z',
}

function renderBlog() {
  return render(
    <HelmetProvider>
      <MemoryRouter>
        <Blog />
      </MemoryRouter>
    </HelmetProvider>,
  )
}

function renderPost(slug: string) {
  return render(
    <HelmetProvider>
      <MemoryRouter initialEntries={[`/blog/${slug}`]}>
        <Routes>
          <Route path="/blog/:slug" element={<BlogPost />} />
        </Routes>
      </MemoryRouter>
    </HelmetProvider>,
  )
}

describe('Blog listing', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders published posts from the API', async () => {
    mockedApi.listPublishedPosts.mockResolvedValue([SAMPLE])
    renderBlog()
    expect(await screen.findByText('First Post')).toBeInTheDocument()
    expect(screen.getByText('An intro to the thing')).toBeInTheDocument()
  })

  it('shows an empty state when there are no posts', async () => {
    mockedApi.listPublishedPosts.mockResolvedValue([])
    renderBlog()
    expect(await screen.findByText(/no posts yet/i)).toBeInTheDocument()
  })
})

describe('BlogPost', () => {
  beforeEach(() => vi.resetAllMocks())

  it('renders the post title and rendered Markdown body', async () => {
    mockedApi.getPublishedPost.mockResolvedValue({
      ...SAMPLE,
      body: '## Hello\n\nWorld of **markdown**.',
      updated_at: '2026-05-31T00:00:00Z',
    })
    renderPost('first-post')
    expect(await screen.findByRole('heading', { name: 'First Post', level: 1 })).toBeInTheDocument()
    expect(await screen.findByText('Hello')).toBeInTheDocument() // markdown rendered
    expect(screen.getByText('markdown')).toBeInTheDocument() // **bold** rendered
  })

  it('shows a not-found state when the post is missing', async () => {
    mockedApi.getPublishedPost.mockRejectedValue(new Error('404'))
    renderPost('missing')
    expect(await screen.findByText(/post not found/i)).toBeInTheDocument()
  })
})
