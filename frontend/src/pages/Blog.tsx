/**
 * Blog — Public blog index (tutorials, tips, conversion content).
 * Standalone public page (no auth, no app shell). Client-rendered with
 * react-helmet-async meta + JSON-LD for crawlers and AI answer engines.
 * @module pages/Blog
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import { BlogFooter, BlogCTA } from '../components/blog/BlogChrome'
import { PublicHeader } from '../components/layout/PublicHeader'
import { formatBlogDate } from '../lib/blogFormat'
import { listPublishedPosts } from '../lib/blogApi'
import type { BlogPostSummary } from '../types/blog'

const SITE = 'https://myide.ai'
const BLOG_URL = `${SITE}/blog`
const DESCRIPTION =
  'Tutorials, tips, and ideas to help you go from a rough concept to a build-ready plan with Ide/AI.'

export function Blog() {
  const [posts, setPosts] = useState<BlogPostSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    listPublishedPosts()
      .then((data) => active && setPosts(data))
      .catch(() => active && setError(true))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [])

  const blogSchema = {
    '@context': 'https://schema.org',
    '@type': 'Blog',
    name: 'Ide/AI Blog',
    url: BLOG_URL,
    description: DESCRIPTION,
    blogPost: posts.map((p) => ({
      '@type': 'BlogPosting',
      headline: p.title,
      url: `${BLOG_URL}/${p.slug}`,
      datePublished: p.published_at || p.created_at,
    })),
  }

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${SITE}/` },
      { '@type': 'ListItem', position: 2, name: 'Blog', item: BLOG_URL },
    ],
  }

  return (
    <div className="min-h-screen bg-background text-white">
      <Helmet>
        <title>Blog — Ide/AI | Tutorials & Tips for Going From Idea to Build</title>
        <meta name="description" content={DESCRIPTION} />
        <link rel="canonical" href={BLOG_URL} />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={BLOG_URL} />
        <meta property="og:title" content="The Ide/AI Blog" />
        <meta property="og:description" content={DESCRIPTION} />
        <meta property="og:image" content={`${SITE}/og-image.png`} />
        <meta property="og:site_name" content="Ide/AI" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="The Ide/AI Blog" />
        <meta name="twitter:description" content={DESCRIPTION} />
        <meta name="twitter:image" content={`${SITE}/og-image.png`} />
        <script type="application/ld+json">{JSON.stringify(blogSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumbSchema)}</script>
      </Helmet>

      <PublicHeader />

      <main className="max-w-4xl mx-auto px-4 py-12 pb-20">
        <header className="mb-10">
          <h1 className="text-3xl md:text-4xl font-black mb-2">The Ide/AI Blog</h1>
          <p className="text-sm text-text-muted max-w-2xl leading-relaxed">{DESCRIPTION}</p>
        </header>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <p className="text-sm text-text-muted py-16 text-center">
            Couldn't load posts right now. Please try again later.
          </p>
        ) : posts.length === 0 ? (
          <p className="text-sm text-text-muted py-16 text-center">
            No posts yet — check back soon for tutorials and tips.
          </p>
        ) : (
          <div className="grid sm:grid-cols-2 gap-5">
            {posts.map((post) => (
              <Link
                key={post.id}
                to={`/blog/${post.slug}`}
                className="group rounded-[var(--radius-card)] border border-border bg-surface/60 backdrop-blur-md overflow-hidden hover:border-white/15 transition-all hover:-translate-y-0.5"
              >
                {post.cover_image_url && (
                  <img
                    src={post.cover_image_url}
                    alt=""
                    className="w-full h-40 object-cover"
                    loading="lazy"
                  />
                )}
                <div className="p-5">
                  {post.tags && post.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-2">
                      {post.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-accent/10 text-accent"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <h2 className="text-base font-bold text-white mb-1.5 group-hover:text-accent transition-colors">
                    {post.title}
                  </h2>
                  {post.excerpt && (
                    <p className="text-sm text-text-muted leading-relaxed line-clamp-3">
                      {post.excerpt}
                    </p>
                  )}
                  <p className="text-xs text-text-muted/70 mt-3">
                    {formatBlogDate(post.published_at || post.created_at)}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        )}

        <BlogCTA />
      </main>

      <BlogFooter />
    </div>
  )
}
