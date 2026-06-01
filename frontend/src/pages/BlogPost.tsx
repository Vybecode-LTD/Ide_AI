/**
 * BlogPost — Public single blog post. Standalone public page (no auth, no app
 * shell). Renders Markdown via react-markdown (raw HTML disabled = XSS-safe),
 * with per-post Helmet meta + BlogPosting/Breadcrumb JSON-LD for SEO/GEO.
 * @module pages/BlogPost
 */
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Helmet } from 'react-helmet-async'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BlogFooter, BlogCTA } from '../components/blog/BlogChrome'
import { PublicHeader } from '../components/layout/PublicHeader'
import { formatBlogDate } from '../lib/blogFormat'
import { getPublishedPost } from '../lib/blogApi'
import type { BlogPost as BlogPostType } from '../types/blog'

const SITE = 'https://myide.ai'

/** Strip basic Markdown to a plain-text meta description fallback. */
function deriveDescription(body: string): string {
  const text = body
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/[#>*_`[\]()!-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return text.slice(0, 155)
}

export function BlogPost() {
  const { slug } = useParams<{ slug: string }>()
  const [post, setPost] = useState<BlogPostType | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!slug) return
    // The page mounts fresh per post view (list → post remounts), so initial
    // state already covers loading=true / notFound=false; no synchronous reset.
    let active = true
    getPublishedPost(slug)
      .then((data) => active && setPost(data))
      .catch(() => active && setNotFound(true))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [slug])

  if (loading) {
    return (
      <div className="min-h-screen bg-background text-white">
        <PublicHeader />
        <div className="flex justify-center py-24">
          <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  if (notFound || !post) {
    return (
      <div className="min-h-screen bg-background text-white">
        <Helmet>
          <title>Post not found — Ide/AI Blog</title>
          <meta name="robots" content="noindex" />
        </Helmet>
        <PublicHeader />
        <main className="max-w-3xl mx-auto px-4 py-24 text-center">
          <h1 className="text-2xl font-black mb-2">Post not found</h1>
          <p className="text-sm text-text-muted mb-6">
            This post may have been moved or unpublished.
          </p>
          <Link to="/blog" className="text-accent text-sm hover:underline">
            ← Back to the blog
          </Link>
        </main>
        <BlogFooter />
      </div>
    )
  }

  const url = `${SITE}/blog/${post.slug}`
  const description = post.excerpt || deriveDescription(post.body)
  const ogImage = post.cover_image_url || `${SITE}/og-image.png`
  const author = post.author_name || 'Ide/AI'

  const articleSchema = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: post.title,
    description,
    image: ogImage,
    datePublished: post.published_at || post.created_at,
    dateModified: post.updated_at,
    author: { '@type': 'Organization', name: author },
    publisher: {
      '@type': 'Organization',
      name: 'Ide/AI',
      logo: { '@type': 'ImageObject', url: `${SITE}/brandmark.png` },
    },
    mainEntityOfPage: { '@type': 'WebPage', '@id': url },
  }

  const breadcrumbSchema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: `${SITE}/` },
      { '@type': 'ListItem', position: 2, name: 'Blog', item: `${SITE}/blog` },
      { '@type': 'ListItem', position: 3, name: post.title, item: url },
    ],
  }

  return (
    <div className="min-h-screen bg-background text-white">
      <Helmet>
        <title>{post.title} — Ide/AI Blog</title>
        <meta name="description" content={description} />
        <link rel="canonical" href={url} />
        <meta property="og:type" content="article" />
        <meta property="og:url" content={url} />
        <meta property="og:title" content={post.title} />
        <meta property="og:description" content={description} />
        <meta property="og:image" content={ogImage} />
        <meta property="og:site_name" content="Ide/AI" />
        {post.published_at && (
          <meta property="article:published_time" content={post.published_at} />
        )}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={post.title} />
        <meta name="twitter:description" content={description} />
        <meta name="twitter:image" content={ogImage} />
        <script type="application/ld+json">{JSON.stringify(articleSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(breadcrumbSchema)}</script>
      </Helmet>

      <PublicHeader />

      <main className="max-w-3xl mx-auto px-4 py-12 pb-20">
        <Link to="/blog" className="text-xs text-text-muted hover:text-white transition-colors">
          ← Back to the blog
        </Link>

        <header className="mt-6 mb-8">
          {post.tags && post.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-accent/10 text-accent"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
          <h1 className="text-3xl md:text-4xl font-black mb-3 leading-tight">{post.title}</h1>
          <p className="text-xs text-text-muted">
            {formatBlogDate(post.published_at || post.created_at)} · {author}
          </p>
        </header>

        {post.cover_image_url && (
          <img
            src={post.cover_image_url}
            alt=""
            className="w-full rounded-[var(--radius-card)] border border-border mb-8"
          />
        )}

        <article className="blog-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{post.body}</ReactMarkdown>
        </article>

        <BlogCTA />
      </main>

      <BlogFooter />
    </div>
  )
}
